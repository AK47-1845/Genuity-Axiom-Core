"""Evidence-oriented control catalog; never a compliance certification engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ControlRequirement:
    control_id: str
    frameworks: tuple[str, ...]
    requirement: str
    evidence: tuple[str, ...]


@dataclass
class ControlAssessment:
    covered: list[str]
    gaps: list[str]
    not_applicable: list[str] = field(default_factory=list)
    disclaimer: str = "A control mapping supports diligence; it does not establish legal compliance or certification."

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class ComplianceControlCatalog:
    """Maps product controls to common buyer evidence requests."""

    def __init__(self) -> None:
        self.controls = [
            ControlRequirement("PURPOSE-001", ("GDPR", "DPDP", "NIST-AI-RMF", "EU-AI-ACT"), "Document intended purpose, recipient, prohibited uses, and retention", ("intended-use record", "data processing inventory", "retention policy")),
            ControlRequirement("MINIMIZE-001", ("GDPR", "DPDP", "HIPAA"), "Limit source fields and records to what the approved use requires", ("column allowlist", "subsetting plan", "data flow")),
            ControlRequirement("PII-001", ("GDPR", "DPDP", "HIPAA", "PCI-DSS"), "Detect and transform direct and contextual identifiers", ("PII scan", "transform log", "residual scan", "expert review where required")),
            ControlRequirement("PRIV-001", ("GDPR", "HIPAA", "NIST-AI-RMF"), "Evaluate disclosure and linkage risk for the release context", ("duplicate/DCR report", "membership/attribute attack report", "recipient model", "expert determination if applicable")),
            ControlRequirement("DP-001", ("GDPR", "NIST-AI-RMF"), "Record formal differential-privacy budget when a DP claim is made", ("mechanism", "epsilon", "delta", "accountant", "composition ledger")),
            ControlRequirement("QUALITY-001", ("EU-AI-ACT", "NIST-AI-RMF"), "Evaluate fitness for intended training, validation, testing, or software-test use", ("holdout", "utility report", "coverage report", "known limitations")),
            ControlRequirement("BIAS-001", ("EU-AI-ACT", "NIST-AI-RMF"), "Measure subgroup representation and downstream performance where people are affected", ("subgroup metrics", "fairness review", "mitigation decision")),
            ControlRequirement("LINEAGE-001", ("EU-AI-ACT", "NIST-AI-RMF", "ISO-27001", "SOC2"), "Preserve source, configuration, model, seed, output, and approval lineage", ("run manifest", "artifact hashes", "audit log", "approvals")),
            ControlRequirement("SEC-001", ("DPDP", "GDPR", "ISO-27001", "SOC2"), "Protect confidentiality, integrity, availability, and tenant boundaries", ("architecture", "access review", "encryption", "logging", "incident response", "backup/restore")),
            ControlRequirement("HUMAN-001", ("EU-AI-ACT", "NIST-AI-RMF"), "Define accountable human review and release authority", ("RACI", "review ledger", "release decision", "escalation policy")),
            ControlRequirement("VENDOR-001", ("GDPR", "DPDP", "ISO-27001", "SOC2"), "Control subprocessors, model providers, and external runners", ("vendor inventory", "DPA", "data residency", "model-routing policy")),
            ControlRequirement("LIFE-001", ("NIST-AI-RMF", "EU-AI-ACT", "SOC2"), "Monitor drift, schema change, model expiry, and release revocation", ("monitoring plan", "expiry", "revalidation trigger", "revocation record")),
        ]

    def assess(self, evidence_ids: set[str], *, applicable_frameworks: set[str] | None = None) -> ControlAssessment:
        covered: list[str] = []
        gaps: list[str] = []
        not_applicable: list[str] = []
        for control in self.controls:
            if applicable_frameworks and not set(control.frameworks).intersection(applicable_frameworks):
                not_applicable.append(control.control_id)
            elif control.control_id in evidence_ids:
                covered.append(control.control_id)
            else:
                gaps.append(control.control_id)
        return ControlAssessment(covered, gaps, not_applicable)

    def to_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "control_id": c.control_id,
                "frameworks": list(c.frameworks),
                "requirement": c.requirement,
                "evidence": list(c.evidence),
            }
            for c in self.controls
        ]
