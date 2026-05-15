"""Expiry, revalidation, and revocation records for released artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from .governance import RunManifest


class ReleaseState(str, Enum):
    ACTIVE = "active"
    REVIEW = "review"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class RevalidationAssessment:
    state: ReleaseState
    usable: bool
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.state.value, "usable": self.usable, "reasons": self.reasons}


@dataclass
class ReleaseLifecycleRecord:
    artifact_id: str
    run_id: str
    state: ReleaseState
    issued_at: str
    expires_at: str
    configuration_fingerprint: str
    recipient: str | None
    purpose: str
    revocation_reason: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_manifest(cls, manifest: RunManifest, *, validity_days: int = 90) -> "ReleaseLifecycleRecord":
        if validity_days <= 0:
            raise ValueError("validity_days must be positive")
        issued = datetime.fromisoformat(manifest.created_at)
        decision = str(manifest.release.get("decision", "blocked"))
        state = {
            "approved": ReleaseState.ACTIVE,
            "review": ReleaseState.REVIEW,
        }.get(decision, ReleaseState.BLOCKED)
        return cls(
            artifact_id=manifest.output_fingerprint[:24],
            run_id=manifest.run_id,
            state=state,
            issued_at=issued.isoformat(),
            expires_at=(issued + timedelta(days=validity_days)).isoformat(),
            configuration_fingerprint=manifest.configuration_fingerprint,
            recipient=manifest.intended_use.recipient,
            purpose=manifest.intended_use.purpose,
            history=[{"at": issued.isoformat(), "event": "issued", "state": state.value}],
        )

    def assess(
        self,
        *,
        now: datetime | None = None,
        configuration_fingerprint: str | None = None,
        recipient: str | None = None,
        purpose: str | None = None,
        drift_requires_revalidation: bool = False,
        policy_changed: bool = False,
        incident_open: bool = False,
    ) -> RevalidationAssessment:
        current = now or datetime.now(timezone.utc)
        reasons: list[str] = []
        if self.state == ReleaseState.REVOKED:
            reasons.append("artifact was revoked" + (f": {self.revocation_reason}" if self.revocation_reason else ""))
        if self.state in {ReleaseState.BLOCKED, ReleaseState.REVIEW}:
            reasons.append(f"artifact issuance state is {self.state.value}")
        if current >= datetime.fromisoformat(self.expires_at):
            reasons.append("release expired")
        if configuration_fingerprint is not None and configuration_fingerprint != self.configuration_fingerprint:
            reasons.append("generation configuration changed")
        if recipient is not None and recipient != self.recipient:
            reasons.append("recipient changed")
        if purpose is not None and purpose != self.purpose:
            reasons.append("intended purpose changed")
        if drift_requires_revalidation:
            reasons.append("source distribution or schema drift requires revalidation")
        if policy_changed:
            reasons.append("release policy changed")
        if incident_open:
            reasons.append("open privacy, security, safety, or quality incident")
        usable = not reasons and self.state == ReleaseState.ACTIVE
        if self.state == ReleaseState.REVOKED:
            state = ReleaseState.REVOKED
        elif "release expired" in reasons:
            state = ReleaseState.EXPIRED
        else:
            state = self.state if usable else ReleaseState.REVIEW
        return RevalidationAssessment(state, usable, reasons)

    def revoke(self, reason: str, *, at: datetime | None = None) -> None:
        if not reason.strip():
            raise ValueError("revocation reason is required")
        timestamp = (at or datetime.now(timezone.utc)).isoformat()
        self.state = ReleaseState.REVOKED
        self.revocation_reason = reason
        self.history.append({"at": timestamp, "event": "revoked", "reason": reason})

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["state"] = self.state.value
        return payload
