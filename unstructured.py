"""Unstructured text/document privacy transforms and leakage checks."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
import secrets
from typing import Any


_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "aadhaar": re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
}


@dataclass
class TextSafetyReport:
    replacements_by_type: dict[str, int]
    residual_matches: dict[str, int]
    exact_document_overlap: int = 0
    longest_shared_ngram: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(self.residual_matches.values()) and self.exact_document_overlap == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "replacements_by_type": self.replacements_by_type,
            "residual_matches": self.residual_matches,
            "exact_document_overlap": self.exact_document_overlap,
            "longest_shared_ngram": self.longest_shared_ngram,
            "warnings": self.warnings,
        }


class UnstructuredPrivacyProcessor:
    """Redacts or consistently replaces pattern-detectable sensitive values.

    This is a baseline control, not a substitute for domain NER, OCR, legal
    review, or expert de-identification.
    """

    def __init__(self, *, secret: str | None = None, strategy: str = "replace") -> None:
        if strategy not in {"replace", "redact"}:
            raise ValueError("strategy must be replace or redact")
        self.ephemeral_secret = secret is None
        self.secret = secret or secrets.token_hex(32)
        self.strategy = strategy
        self._mapping: dict[tuple[str, str], str] = {}

    def transform_text(self, text: str) -> tuple[str, TextSafetyReport]:
        output = str(text)
        counts: dict[str, int] = {}
        for label, pattern in _PATTERNS.items():
            matches = list(pattern.finditer(output))
            counts[label] = len(matches)
            output = pattern.sub(lambda m: self._replacement(label, m.group(0)), output)
        residual = {label: len(pattern.findall(output)) for label, pattern in _PATTERNS.items()}
        warnings = ["Pattern detection does not cover names, proprietary entities, contextual identifiers, faces, signatures, or domain-specific secrets."]
        if self.ephemeral_secret and self.strategy == "replace":
            warnings.append("An ephemeral pseudonymization secret was generated; provide a protected run-specific secret when repeatable linkage is required.")
        return output, TextSafetyReport(counts, residual, warnings=warnings)

    def transform(self, value: Any) -> tuple[Any, TextSafetyReport]:
        reports: list[TextSafetyReport] = []

        def visit(item: Any) -> Any:
            if isinstance(item, str):
                transformed, report = self.transform_text(item)
                reports.append(report)
                return transformed
            if isinstance(item, list):
                return [visit(v) for v in item]
            if isinstance(item, tuple):
                return tuple(visit(v) for v in item)
            if isinstance(item, set):
                return [visit(v) for v in sorted(item, key=str)]
            if isinstance(item, dict):
                return {k: visit(v) for k, v in item.items()}
            return item

        transformed = visit(value)
        combined = {label: sum(r.replacements_by_type.get(label, 0) for r in reports) for label in _PATTERNS}
        residual = {label: sum(r.residual_matches.get(label, 0) for r in reports) for label in _PATTERNS}
        warnings = sorted({w for r in reports for w in r.warnings})
        return transformed, TextSafetyReport(combined, residual, warnings=warnings)

    def audit_pair(self, source_texts: list[str], output_texts: list[str], *, max_ngram: int = 12) -> TextSafetyReport:
        source_set = {text.strip() for text in source_texts if text.strip()}
        exact = sum(1 for text in output_texts if text.strip() in source_set)
        longest = 0
        source_ngrams: dict[int, set[tuple[str, ...]]] = {}
        for n in range(3, max_ngram + 1):
            grams: set[tuple[str, ...]] = set()
            for text in source_texts:
                tokens = text.split()
                grams.update(tuple(tokens[i:i+n]) for i in range(max(0, len(tokens) - n + 1)))
            source_ngrams[n] = grams
        for text in output_texts:
            tokens = text.split()
            for n in range(3, max_ngram + 1):
                if any(tuple(tokens[i:i+n]) in source_ngrams[n] for i in range(max(0, len(tokens) - n + 1))):
                    longest = max(longest, n)
        residual = {label: sum(len(pattern.findall(text)) for text in output_texts) for label, pattern in _PATTERNS.items()}
        warnings = []
        if longest >= 8:
            warnings.append("Long verbatim span detected; review copyright, confidentiality, and memorization risk.")
        return TextSafetyReport({}, residual, exact_document_overlap=exact, longest_shared_ngram=longest, warnings=warnings)

    def _replacement(self, label: str, value: str) -> str:
        if self.strategy == "redact":
            return f"<{label.upper()}_REDACTED>"
        key = (label, value)
        if key not in self._mapping:
            token = hashlib.sha256(f"{self.secret}:{label}:{value}".encode("utf-8")).hexdigest()[:12]
            self._mapping[key] = f"<{label.upper()}_{token}>"
        return self._mapping[key]
