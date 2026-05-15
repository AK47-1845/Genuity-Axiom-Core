"""Truthful modality inventory and adapter capability registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Modality(str, Enum):
    TABULAR = "tabular"
    RELATIONAL = "relational"
    TIME_SERIES = "time_series"
    EVENT = "event"
    TEXT = "text"
    DOCUMENT = "document"
    GRAPH = "graph"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    SIMULATION = "simulation"
    MULTIMODAL = "multimodal"


class CapabilityLevel(str, Enum):
    NATIVE = "native"
    BASELINE = "baseline"
    VALIDATION_ONLY = "validation_only"
    ADAPTER_REQUIRED = "adapter_required"


@dataclass(frozen=True)
class ModalityCapability:
    modality: Modality
    level: CapabilityLevel
    operations: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "modality": self.modality.value,
            "level": self.level.value,
            "operations": list(self.operations),
            "limitations": list(self.limitations),
        }


@dataclass
class DataAsset:
    name: str
    modality: Modality
    payload: Any
    content_type: str | None = None
    role: str = "source"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataBundle:
    assets: list[DataAsset]
    relationships: list[dict[str, Any]] = field(default_factory=list)
    intended_use: str = "unspecified"

    @property
    def modalities(self) -> set[Modality]:
        return {asset.modality for asset in self.assets}

    def validate(self) -> list[str]:
        issues: list[str] = []
        names = [asset.name for asset in self.assets]
        if len(names) != len(set(names)):
            issues.append("asset names must be unique")
        if not self.assets:
            issues.append("bundle must contain at least one asset")
        for asset in self.assets:
            if asset.payload is None:
                issues.append(f"asset {asset.name!r} has no payload")
        known = set(names)
        for index, relationship in enumerate(self.relationships):
            source = relationship.get("source")
            target = relationship.get("target")
            if source not in known or target not in known:
                issues.append(f"relationship {index} references an unknown source or target asset")
        return issues


class CapabilityRegistry:
    """Prevents documentation from overstating what the local package executes."""

    def __init__(self) -> None:
        self._capabilities = {
            Modality.TABULAR: ModalityCapability(Modality.TABULAR, CapabilityLevel.NATIVE, ("profile", "generate", "condition", "constrain", "evaluate", "release")),
            Modality.TIME_SERIES: ModalityCapability(Modality.TIME_SERIES, CapabilityLevel.BASELINE, ("profile", "block_bootstrap", "evaluate"), ("neural sequence models require an external adapter",)),
            Modality.EVENT: ModalityCapability(Modality.EVENT, CapabilityLevel.BASELINE, ("profile", "block_bootstrap", "rare_event_sampling")),
            Modality.RELATIONAL: ModalityCapability(Modality.RELATIONAL, CapabilityLevel.BASELINE, ("schema_validate", "pk_fk_validate", "independent_table_generate", "key_remap"), ("cross-table generative dependence is not learned by the local baseline",)),
            Modality.TEXT: ModalityCapability(Modality.TEXT, CapabilityLevel.BASELINE, ("detect", "redact", "consistent_replace", "leakage_audit"), ("high-quality text generation requires an approved language-model adapter",)),
            Modality.DOCUMENT: ModalityCapability(Modality.DOCUMENT, CapabilityLevel.BASELINE, ("recursive_redact", "schema_extract", "leakage_audit"), ("layout-faithful PDF/DOCX generation requires a document-rendering adapter",)),
            Modality.GRAPH: ModalityCapability(Modality.GRAPH, CapabilityLevel.VALIDATION_ONLY, ("schema_validate", "edge_integrity", "coverage_spec"), ("graph generation adapter is not implemented locally",)),
            Modality.IMAGE: ModalityCapability(Modality.IMAGE, CapabilityLevel.ADAPTER_REQUIRED, ("metadata_contract", "annotation_contract", "privacy_review"), ("pixel generation and visual-fidelity evaluation are not implemented locally",)),
            Modality.AUDIO: ModalityCapability(Modality.AUDIO, CapabilityLevel.ADAPTER_REQUIRED, ("metadata_contract", "transcript_redaction", "privacy_review"), ("waveform generation is not implemented locally",)),
            Modality.VIDEO: ModalityCapability(Modality.VIDEO, CapabilityLevel.ADAPTER_REQUIRED, ("metadata_contract", "annotation_contract", "privacy_review"), ("video generation and temporal visual evaluation are not implemented locally",)),
            Modality.SIMULATION: ModalityCapability(Modality.SIMULATION, CapabilityLevel.VALIDATION_ONLY, ("scenario_contract", "parameter_manifest", "constraint_validate"), ("Axiom orchestrates approved simulators; it is not a physics solver",)),
            Modality.MULTIMODAL: ModalityCapability(Modality.MULTIMODAL, CapabilityLevel.VALIDATION_ONLY, ("bundle_inventory", "cross_asset_relationships", "release_manifest"), ("each asset requires a capable modality adapter",)),
        }

    def get(self, modality: str | Modality) -> ModalityCapability:
        key = modality if isinstance(modality, Modality) else Modality(str(modality))
        return self._capabilities[key]

    def matrix(self) -> list[dict[str, Any]]:
        return [self._capabilities[key].to_dict() for key in Modality]


_EXTENSIONS = {
    Modality.TABULAR: {".csv", ".parquet", ".xlsx", ".xls"},
    Modality.TEXT: {".txt", ".md", ".log"},
    Modality.DOCUMENT: {".pdf", ".docx", ".pptx", ".html", ".xml", ".eml"},
    Modality.IMAGE: {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"},
    Modality.AUDIO: {".wav", ".mp3", ".flac", ".m4a"},
    Modality.VIDEO: {".mp4", ".mov", ".avi", ".mkv"},
    Modality.GRAPH: {".graphml", ".gexf"},
}


def infer_modality(path: str | Path) -> Modality:
    suffix = Path(path).suffix.lower()
    for modality, suffixes in _EXTENSIONS.items():
        if suffix in suffixes:
            return modality
    if suffix in {".json", ".jsonl"}:
        return Modality.DOCUMENT
    return Modality.MULTIMODAL
