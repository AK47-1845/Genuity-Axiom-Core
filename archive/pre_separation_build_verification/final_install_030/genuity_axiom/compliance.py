"""Compliance and privacy gates for engineering data."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable

import pandas as pd


PII_KEYWORDS = {
    "name",
    "first_name",
    "last_name",
    "fullname",
    "email",
    "email_address",
    "phone",
    "mobile",
    "address",
    "zip",
    "postal",
    "ssn",
    "passport",
    "driver_license",
    "aadhaar",
    "pan",
    "dob",
    "birth_date",
    "password",
    "secret",
    "credential",
    "account_number",
    "card_number",
}

IDENTIFIER_KEYWORDS = {
    "id",
    "uuid",
    "serial",
    "vin",
    "imei",
    "asset_tag",
    "project_code",
}

CELL_PATTERNS = {
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    "phone": re.compile(r"^\+?[\d\s().-]{7,}$"),
    "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "uuid": re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    ),
}


@dataclass(frozen=True)
class PrivacyPolicy:
    """Controls how strict the pre-generation privacy gate should be."""

    level: str = "standard"
    max_identifier_ratio: float = 0.9
    min_rows_for_release: int = 25
    quasi_identifier_cardinality_ratio: float = 0.8
    allow_exact_duplicates: bool = False
    epsilon: float | None = None

    def normalized_level(self) -> str:
        value = self.level.lower().strip()
        if value not in {"standard", "strict", "dp-ready"}:
            raise ValueError("privacy level must be standard, strict, or dp-ready")
        return value


@dataclass
class ComplianceReport:
    original_columns: list[str]
    retained_columns: list[str]
    removed_columns: list[str] = field(default_factory=list)
    masked_columns: list[str] = field(default_factory=list)
    pii_columns: list[str] = field(default_factory=list)
    identifier_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    privacy_level: str = "standard"

    @property
    def passed(self) -> bool:
        return not any(w.startswith("BLOCKER:") for w in self.warnings)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "privacy_level": self.privacy_level,
            "original_columns": self.original_columns,
            "retained_columns": self.retained_columns,
            "removed_columns": self.removed_columns,
            "masked_columns": self.masked_columns,
            "pii_columns": self.pii_columns,
            "identifier_columns": self.identifier_columns,
            "warnings": self.warnings,
        }


class ComplianceGate:
    """Detects and removes or masks PII before any generator sees the data."""

    def __init__(
        self,
        policy: PrivacyPolicy | None = None,
        strategy: str = "drop",
        allowlist: Iterable[str] | None = None,
    ) -> None:
        self.policy = policy or PrivacyPolicy()
        self.strategy = strategy
        self.allowlist = {c.lower() for c in (allowlist or [])}
        if strategy not in {"drop", "mask", "flag"}:
            raise ValueError("strategy must be drop, mask, or flag")

    def detect(self, df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
        pii_cols: list[str] = []
        identifier_cols: list[str] = []
        warnings: list[str] = []

        for col in df.columns:
            norm = _normalize(col)
            if col.lower() in self.allowlist:
                continue

            if _looks_like_pii_column(norm):
                pii_cols.append(col)

            if _looks_like_identifier_column(norm):
                identifier_cols.append(col)

            series = df[col].dropna()
            if series.empty:
                continue

            # Pattern scans on numeric measurements create severe false positives
            # (for example a decimal sensor value can resemble a phone number).
            # Explicitly named numeric PII is already caught by the keyword rules.
            if not pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
                sample = series.astype(str).head(250)
                for label, pattern in CELL_PATTERNS.items():
                    hits = sample.map(lambda value: bool(pattern.fullmatch(value.strip()))).mean()
                    if hits >= 0.3:
                        if label in {"email", "phone", "ssn"} and col not in pii_cols:
                            pii_cols.append(col)
                        if label == "uuid" and col not in identifier_cols:
                            identifier_cols.append(col)

            unique_ratio = float(series.nunique(dropna=True)) / max(float(len(series)), 1.0)
            if unique_ratio >= self.policy.quasi_identifier_cardinality_ratio:
                if (
                    col not in identifier_cols
                    and not pd.api.types.is_numeric_dtype(series)
                    and not pd.api.types.is_bool_dtype(series)
                ):
                    identifier_cols.append(col)

        level = self.policy.normalized_level()
        risky_ratio = len(set(pii_cols + identifier_cols)) / max(len(df.columns), 1)
        if risky_ratio > self.policy.max_identifier_ratio:
            warnings.append("BLOCKER: detected identifiers or PII exceed the configured column-risk ratio")
        if len(df) < self.policy.min_rows_for_release:
            warnings.append(
                "BLOCKER: dataset has fewer rows than the minimum release threshold"
            )

        if level in {"strict", "dp-ready"}:
            risky = sorted(set(pii_cols + identifier_cols))
            if risky:
                warnings.append(
                    "High privacy mode removed or masked direct and quasi-identifiers: "
                    + ", ".join(risky)
                )

        if level == "dp-ready" and self.policy.epsilon is None:
            warnings.append("DP-ready mode requested without an epsilon budget")

        return sorted(set(pii_cols)), sorted(set(identifier_cols)), warnings

    def scrub(self, df: pd.DataFrame) -> tuple[pd.DataFrame, ComplianceReport]:
        pii_cols, identifier_cols, warnings = self.detect(df)
        risky_cols = sorted(set(pii_cols + identifier_cols))
        cleaned = df.copy()
        removed: list[str] = []
        masked: list[str] = []

        if self.strategy == "drop":
            cleaned = cleaned.drop(columns=risky_cols, errors="ignore")
            removed = risky_cols
        elif self.strategy == "mask":
            for col in risky_cols:
                if col in cleaned:
                    cleaned[col] = cleaned[col].map(
                        lambda value: None if pd.isna(value) else f"{col}_MASKED"
                    )
                    masked.append(col)
        else:
            warnings.append("PII/identifier columns flagged but not removed")

        report = ComplianceReport(
            original_columns=list(df.columns),
            retained_columns=list(cleaned.columns),
            removed_columns=removed,
            masked_columns=masked,
            pii_columns=pii_cols,
            identifier_columns=identifier_cols,
            warnings=warnings,
            privacy_level=self.policy.normalized_level(),
        )
        return cleaned, report


def _normalize(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", str(value)).strip("_").lower()
    value = re.sub(r"_+", "_", value)
    return value


def _looks_like_pii_column(norm: str) -> bool:
    if norm in PII_KEYWORDS:
        return True
    sensitive_suffixes = (
        "_email", "_phone", "_mobile", "_address", "_ssn", "_passport",
        "_aadhaar", "_dob", "_birth_date", "_password", "_secret", "_credential",
        "_account_number", "_account_no", "_card_number", "_card_no",
    )
    if norm.endswith(sensitive_suffixes):
        return True
    person_prefixes = ("customer_", "person_", "patient_", "employee_", "user_", "driver_")
    return norm.endswith("_name") and norm.startswith(person_prefixes)


def _looks_like_identifier_column(norm: str) -> bool:
    if norm in IDENTIFIER_KEYWORDS or norm in {"customer", "employee", "patient", "user"}:
        return True
    return norm.endswith(("_id", "_uuid", "_serial", "_vin", "_imei", "_asset_tag", "_project_code"))
