"""Auditable human approval records for release-policy checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ApprovalEvidence:
    role: str
    approver: str
    decision: str
    approved_at: str
    scope: str
    evidence_reference: str

    def issues(self) -> list[str]:
        issues: list[str] = []
        if self.role not in {"domain_owner", "privacy_owner", "security_owner", "model_owner", "legal_owner"}:
            issues.append("unsupported approval role")
        if self.decision not in {"approved", "rejected"}:
            issues.append("decision must be approved or rejected")
        for field_name in ("approver", "approved_at", "scope", "evidence_reference"):
            if not str(getattr(self, field_name)).strip():
                issues.append(f"{field_name} is required")
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
    def from_dict(cls, payload: dict[str, Any]) -> "ApprovalEvidence":
        return cls(**{field: payload[field] for field in cls.__dataclass_fields__})


def has_approval(evidence: list[ApprovalEvidence], role: str) -> bool:
    relevant = [item for item in evidence if item.role == role and item.valid]
    return bool(relevant) and relevant[-1].decision == "approved"
