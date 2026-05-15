"""Small, serialisable domain objects used by the reconciliation pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceRef:
    evidence_id: str
    document_id: str
    page: int
    region: str
    quote: str
    content_hash: str
    bbox: list[float] = field(default_factory=list)
    evidence_type: str = "OCR_REGION"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FieldDecision:
    field_id: str
    document_id: str
    name: str
    value: Any
    unit: str | None
    original_extraction: Any
    status: str
    acceptance: str
    confidence: float
    critical: bool
    evidence_ids: list[str] = field(default_factory=list)
    method: str = "existing_ocr"
    rationale: str = ""
    rule_results: list[dict[str, Any]] = field(default_factory=list)
    alternatives_rejected: list[dict[str, Any]] = field(default_factory=list)
    safe_for_operational_use: bool = False
    analytics_only: bool = False
    requires_human_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentRecord:
    document_id: str
    source_file: str
    document_type: str
    page_count: int
    content_hash: str
    classification_method: str = "deterministic_cues"
    duplicate_of: str | None = None
    superseded_by: str | None = None
    fields: list[FieldDecision] = field(default_factory=list)

    def field(self, name: str) -> FieldDecision | None:
        return next((item for item in self.fields if item.name == name), None)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["fields"] = [item.to_dict() for item in self.fields]
        return data


@dataclass
class RunMetrics:
    pages_processed: int = 0
    fields_processed: int = 0
    cache_hits: int = 0
    ocr_calls: int = 0
    ocr_result_reads: int = 0
    rule_evaluations: int = 0
    local_model_calls: int = 0
    external_model_calls: int = 0
    model_cache_hits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    human_review_cases: int = 0
    automatically_accepted_fields: int = 0
    verified_fields: int = 0
    unresolved_fields: int = 0
    processing_time_seconds: float = 0.0
    deterministic_documents: int = 0
    external_regions_routed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineResult:
    documents: list[DocumentRecord]
    decisions: list[FieldDecision]
    evidence: list[EvidenceRef]
    exceptions: list[dict[str, Any]]
    validations: list[dict[str, Any]]
    graph: dict[str, Any]
    connected_record: dict[str, Any]
    metrics: dict[str, Any]
    cost_report: dict[str, Any]
    business_case: dict[str, Any]
    accuracy_report: dict[str, Any]
    integrity_report: dict[str, Any]
    scorecard: dict[str, Any]
    domain_pack_snapshot: dict[str, Any]
    scale_benchmark: dict[str, Any] | None = None
    resilience_scorecard: dict[str, Any] | None = None
