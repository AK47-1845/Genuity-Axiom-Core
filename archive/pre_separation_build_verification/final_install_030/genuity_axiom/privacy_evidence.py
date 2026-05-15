"""Structured evidence required before Axiom recognizes a formal-DP claim."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DifferentialPrivacyEvidence:
    mechanism: str
    epsilon: float
    delta: float
    accountant: str
    adjacency_definition: str
    clipping_or_sensitivity: str
    composition_ledger_reference: str
    verified_by: str
    verified_at: str

    def issues(self) -> list[str]:
        issues: list[str] = []
        for field_name in (
            "mechanism", "accountant", "adjacency_definition", "clipping_or_sensitivity",
            "composition_ledger_reference", "verified_by", "verified_at",
        ):
            if not str(getattr(self, field_name)).strip():
                issues.append(f"{field_name} is required")
        if not 0 < float(self.epsilon) < float("inf"):
            issues.append("epsilon must be finite and positive")
        if not 0 <= float(self.delta) < 1:
            issues.append("delta must be in [0, 1)")
        return issues

    @property
    def valid(self) -> bool:
        return not self.issues()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["valid"] = self.valid
        payload["issues"] = self.issues()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DifferentialPrivacyEvidence":
        return cls(**{field: payload[field] for field in cls.__dataclass_fields__})
