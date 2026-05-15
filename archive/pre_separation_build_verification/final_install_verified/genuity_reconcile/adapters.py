"""Adapters keep Genuity downstream of a client's existing OCR/VLM stack."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .economics import vision_token_usage
from .models import DocumentRecord, EvidenceRef, FieldDecision, RunMetrics


class ExistingOCRJsonAdapter:
    """Read a deliberately small, vendor-neutral existing-OCR JSON contract."""

    def __init__(self, domain_pack: dict[str, Any], metrics: RunMetrics):
        self.pack = domain_pack
        self.metrics = metrics
        self.cache: dict[str, DocumentRecord] = {}

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            {
                "page_count": payload.get("page_count"),
                "text": payload.get("text", ""),
                "fields": payload.get("fields", []),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def document_id(path: Path) -> str:
        return path.stem.upper().replace("-", "_")

    def _classify(self, text: str) -> str:
        upper = text.upper()
        scores: dict[str, int] = {}
        for doc_type, cues in self.pack["document_types"].items():
            score = sum(cue.upper() in upper for cue in cues)
            scores[doc_type] = score
            self.metrics.rule_evaluations += len(cues)
        best_score = max(scores.values(), default=0)
        winners = [doc_type for doc_type, score in scores.items() if score == best_score and score > 0]
        return winners[0] if len(winners) == 1 else "unknown"

    @staticmethod
    def _validate_payload(payload: Any, path: Path) -> None:
        def finite(value: Any) -> bool:
            if isinstance(value, float):
                return math.isfinite(value)
            if isinstance(value, list):
                return all(finite(item) for item in value)
            if isinstance(value, dict):
                return all(finite(item) for item in value.values())
            return True

        if not isinstance(payload, dict):
            raise ValueError(f"{path}: OCR payload must be a JSON object")
        if not isinstance(payload.get("page_count"), int) or payload["page_count"] < 1:
            raise ValueError(f"{path}: page_count must be a positive integer")
        if not isinstance(payload.get("text"), str):
            raise ValueError(f"{path}: text must be a string")
        if not isinstance(payload.get("fields"), list):
            raise ValueError(f"{path}: fields must be an array")
        names: set[str] = set()
        for index, raw in enumerate(payload["fields"], start=1):
            prefix = f"{path}: field {index}"
            if not isinstance(raw, dict):
                raise ValueError(f"{prefix} must be an object")
            for key in ["name", "value", "confidence", "page", "region"]:
                if key not in raw:
                    raise ValueError(f"{prefix} is missing required key {key}")
            if not isinstance(raw["name"], str) or not raw["name"]:
                raise ValueError(f"{prefix}.name must be a non-empty string")
            if raw["name"] in names:
                raise ValueError(f"{prefix}.name duplicates another canonical field name")
            names.add(raw["name"])
            if not finite(raw["value"]):
                raise ValueError(f"{prefix}.value contains NaN or infinity")
            if not isinstance(raw["confidence"], (int, float)) or not 0 <= raw["confidence"] <= 1:
                raise ValueError(f"{prefix}.confidence must be between 0 and 1")
            if not isinstance(raw["page"], int) or not 1 <= raw["page"] <= payload["page_count"]:
                raise ValueError(f"{prefix}.page must refer to a page in the document")
            if not isinstance(raw["region"], str) or not raw["region"]:
                raise ValueError(f"{prefix}.region must be a non-empty string")
            if raw.get("unit") is not None and not isinstance(raw["unit"], str):
                raise ValueError(f"{prefix}.unit must be a string or null")
            bbox = raw.get("bbox")
            if bbox is not None:
                if (
                    not isinstance(bbox, list)
                    or len(bbox) != 4
                    or any(not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in bbox)
                ):
                    raise ValueError(f"{prefix}.bbox must contain four normalized numbers")
                if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                    raise ValueError(f"{prefix}.bbox must be ordered as x1,y1,x2,y2")

    def read(self, path: Path, evidence: list[EvidenceRef]) -> DocumentRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._validate_payload(payload, path)
        self.metrics.ocr_result_reads += 1
        self.metrics.pages_processed += int(payload.get("page_count", 1))
        content_hash = self._fingerprint(payload)
        document_id = self.document_id(path)
        if content_hash in self.cache:
            self.metrics.cache_hits += 1
            original = self.cache[content_hash]
            return DocumentRecord(
                document_id=document_id,
                source_file=str(path),
                document_type=original.document_type,
                page_count=int(payload.get("page_count", 1)),
                content_hash=content_hash,
                classification_method="content_hash_cache",
                duplicate_of=original.document_id,
                fields=[],
            )

        document_type = self._classify(payload.get("text", ""))
        aliases = self.pack.get("field_aliases", {})
        canonical_names = [aliases.get(raw["name"], raw["name"]) for raw in payload["fields"]]
        if len(canonical_names) != len(set(canonical_names)):
            collisions = sorted(
                name for name in set(canonical_names) if canonical_names.count(name) > 1
            )
            raise ValueError(
                f"{path}: field aliases collapse multiple inputs to canonical names: {', '.join(collisions)}"
            )
        critical_fields = set(self.pack["critical_fields"])
        threshold = float(self.pack.get("review_threshold", 0.85))
        fields: list[FieldDecision] = []
        for index, raw in enumerate(payload.get("fields", []), start=1):
            name = aliases.get(raw["name"], raw["name"])
            value = copy.deepcopy(raw.get("value"))
            confidence = float(raw.get("confidence", 0.0))
            evidence_id = f"EV-{document_id}-{index:03d}"
            quote = "[blank]" if value is None else json.dumps(value, ensure_ascii=False)
            evidence.append(
                EvidenceRef(
                    evidence_id=evidence_id,
                    document_id=document_id,
                    page=int(raw.get("page", 1)),
                    region=raw.get("region", "unknown"),
                    quote=quote,
                    bbox=raw.get("bbox", []),
                    content_hash=content_hash,
                )
            )
            missing = value is None
            accepted = not missing and confidence >= threshold
            decision = FieldDecision(
                field_id=f"FD-{document_id}-{name}",
                document_id=document_id,
                name=name,
                value=value,
                unit=raw.get("unit"),
                original_extraction=copy.deepcopy(value),
                status="MISSING" if missing else ("OBSERVED" if accepted else "LOW_CONFIDENCE"),
                acceptance="NOT_ACCEPTED" if missing else ("ACCEPTED" if accepted else "REVIEW"),
                confidence=confidence,
                critical=name in critical_fields,
                evidence_ids=[evidence_id],
                method="existing_ocr",
                rationale="Blank in existing OCR output." if missing else "Value supplied by the existing OCR adapter.",
                safe_for_operational_use=accepted,
                requires_human_confirmation=not accepted and not missing,
            )
            if document_type == "unknown" and not missing:
                decision.status = "UNCLASSIFIED_SOURCE"
                decision.acceptance = "REVIEW"
                decision.safe_for_operational_use = False
                decision.requires_human_confirmation = True
                decision.rationale = (
                    "The field was extracted, but the document did not match a configured type and cannot auto-load."
                )
            fields.append(decision)
            self.metrics.fields_processed += 1
        result = DocumentRecord(
            document_id=document_id,
            source_file=str(path),
            document_type=document_type,
            page_count=int(payload.get("page_count", 1)),
            content_hash=content_hash,
            fields=fields,
        )
        self.cache[content_hash] = result
        return result


class FixtureCroppedRegionVLMAdapter:
    """Deterministic stand-in proving a crop-only VLM boundary without network access."""

    model_name = "gpt-5.4-mini (simulated adapter)"

    def __init__(self, cache_dir: str | Path | None = None):
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def inspect_region(
        self,
        document: DocumentRecord,
        decision: FieldDecision,
        metrics: RunMetrics,
        pricing: dict[str, Any],
    ) -> dict[str, Any]:
        usage = vision_token_usage(pricing)["crop"]
        cache_key = hashlib.sha256(
            f"{self.model_name}|{document.content_hash}|{decision.name}".encode("utf-8")
        ).hexdigest()
        cache_path = self.cache_dir / f"{cache_key}.json" if self.cache_dir else None
        if cache_path and cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            recorded_integrity = cached.pop("integrity_sha256", None)
            actual_integrity = hashlib.sha256(
                json.dumps(cached, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if (
                recorded_integrity != actual_integrity
                or cached.get("cache_key") != cache_key
                or cached.get("document_content_hash") != document.content_hash
                or cached.get("field_name") != decision.name
            ):
                raise RuntimeError(f"Cached model result failed integrity validation: {cache_path}")
            metrics.model_cache_hits += 1
            cached["cache_hit"] = True
            return cached
        metrics.external_model_calls += 1
        metrics.external_regions_routed += 1
        metrics.input_tokens += usage["input_tokens"]
        metrics.output_tokens += usage["output_tokens"]
        result = {
            "candidate": 910.0,
            "unit": "MPa",
            "confidence": 0.91,
            "model": self.model_name,
            "scope": decision.name,
            "note": "Only the obscured mechanical-table crop was routed; candidate is not auto-accepted.",
            "cache_hit": False,
            "cache_key": cache_key,
            "document_content_hash": document.content_hash,
            "field_name": decision.name,
            "cache_schema_version": "1.0.0",
        }
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_payload = dict(result)
            cache_payload["integrity_sha256"] = hashlib.sha256(
                json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            cache_path.write_text(json.dumps(cache_payload, indent=2), encoding="utf-8")
        return result
