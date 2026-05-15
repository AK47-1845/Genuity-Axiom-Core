"""Non-compensating release gates for synthetic data.

Quality scores are useful for model selection. They are not release authority.
This module prevents strong fidelity from hiding a failed privacy, constraint,
lineage, or human-approval requirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskTier(str, Enum):
    SANDBOX = "sandbox"
    INTERNAL = "internal"
    EXTERNAL = "external"
    REGULATED = "regulated"


class ReleaseDecision(str, Enum):
    APPROVED = "approved"
    REVIEW = "review"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ReleasePolicy:
    risk_tier: RiskTier = RiskTier.INTERNAL
    min_similarity_score: float = 0.70
    min_missingness_score: float = 0.90
    min_privacy_score: float = 0.75
    min_constraint_score: float = 0.98
    min_range_score: float = 0.98
    min_membership_attack_score: float = 0.70
    max_exact_duplicate_rate: float = 0.01
    max_holdout_similarity_gap: float = 0.15
    min_utility_score: float | None = None
    require_holdout: bool = True
    require_no_direct_identifiers: bool = True
    require_formal_dp: bool = False
    require_domain_approval: bool = False
    require_privacy_approval: bool = False
    require_recipient: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.risk_tier, RiskTier):
            object.__setattr__(self, "risk_tier", RiskTier(str(self.risk_tier)))

    def issues(self) -> list[str]:
        issues: list[str] = []
        minimums = {
            "min_similarity_score": self.min_similarity_score,
            "min_missingness_score": self.min_missingness_score,
            "min_privacy_score": self.min_privacy_score,
            "min_constraint_score": self.min_constraint_score,
            "min_range_score": self.min_range_score,
            "min_membership_attack_score": self.min_membership_attack_score,
        }
        if self.min_utility_score is not None:
            minimums["min_utility_score"] = self.min_utility_score
        maximums = {
            "max_exact_duplicate_rate": self.max_exact_duplicate_rate,
            "max_holdout_similarity_gap": self.max_holdout_similarity_gap,
        }
        for name, value in {**minimums, **maximums}.items():
            if not 0 <= float(value) <= 1:
                issues.append(f"{name} must be in [0, 1]")
        return issues

    @classmethod
    def for_tier(cls, tier: str | RiskTier) -> "ReleasePolicy":
        normalized = tier if isinstance(tier, RiskTier) else RiskTier(str(tier))
        if normalized == RiskTier.SANDBOX:
            return cls(
                risk_tier=normalized,
                min_similarity_score=0.50,
                min_missingness_score=0.80,
                min_privacy_score=0.60,
                min_constraint_score=0.90,
                min_range_score=0.90,
                min_membership_attack_score=0.55,
                max_exact_duplicate_rate=0.05,
                max_holdout_similarity_gap=0.25,
                require_holdout=False,
                require_no_direct_identifiers=True,
            )
        if normalized == RiskTier.EXTERNAL:
            return cls(
                risk_tier=normalized,
                min_similarity_score=0.80,
                min_missingness_score=0.95,
                min_privacy_score=0.85,
                min_constraint_score=0.99,
                min_range_score=0.99,
                min_membership_attack_score=0.80,
                max_exact_duplicate_rate=0.0,
                max_holdout_similarity_gap=0.10,
                require_domain_approval=True,
                require_privacy_approval=True,
                require_recipient=True,
            )
        if normalized == RiskTier.REGULATED:
            return cls(
                risk_tier=normalized,
                min_similarity_score=0.85,
                min_missingness_score=0.98,
                min_privacy_score=0.90,
                min_constraint_score=0.995,
                min_range_score=0.995,
                min_membership_attack_score=0.85,
                max_exact_duplicate_rate=0.0,
                max_holdout_similarity_gap=0.08,
                require_domain_approval=True,
                require_privacy_approval=True,
                require_recipient=True,
            )
        return cls(risk_tier=RiskTier.INTERNAL)


@dataclass(frozen=True)
class GateCheck:
    name: str
    passed: bool
    severity: str
    observed: Any
    required: Any
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "observed": self.observed,
            "required": self.required,
            "explanation": self.explanation,
        }


@dataclass
class ReleaseAssessment:
    decision: ReleaseDecision
    risk_tier: RiskTier
    checks: list[GateCheck] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.decision == ReleaseDecision.APPROVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "risk_tier": self.risk_tier.value,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "limitations": self.limitations,
        }


class SyntheticReleaseGate:
    """Evaluates independent hard gates; no weighted average can override them."""

    def assess(
        self,
        *,
        evaluation: Any,
        compliance: Any,
        policy: ReleasePolicy,
        formal_dp_verified: bool = False,
        domain_approved: bool = False,
        privacy_approved: bool = False,
        holdout_independent: bool = True,
        modality_appropriate_evaluation: bool = True,
        constraint_warning_count: int = 0,
        condition_match_rate: float = 1.0,
        intended_use_complete: bool = True,
    ) -> ReleaseAssessment:
        checks: list[GateCheck] = []
        limitations: list[str] = []

        policy_issues = policy.issues()
        checks.append(
            GateCheck(
                "release_policy_valid",
                not policy_issues,
                "blocker",
                policy_issues,
                [],
                "Release thresholds and requirements must form a valid policy",
            )
        )

        def minimum(name: str, observed: float | None, required: float, explanation: str) -> None:
            checks.append(
                GateCheck(
                    name=name,
                    passed=observed is not None and float(observed) >= required,
                    severity="blocker",
                    observed=observed,
                    required=f">={required}",
                    explanation=explanation,
                )
            )

        def maximum(name: str, observed: float | None, required: float, explanation: str) -> None:
            checks.append(
                GateCheck(
                    name=name,
                    passed=observed is not None and float(observed) <= required,
                    severity="blocker",
                    observed=observed,
                    required=f"<={required}",
                    explanation=explanation,
                )
            )

        minimum("similarity_score", evaluation.similarity_score, policy.min_similarity_score, "Minimum statistical fitness for the declared tabular use")
        minimum("missingness_score", evaluation.missingness_score, policy.min_missingness_score, "Missing-data behavior must remain within the approved tolerance")
        minimum("privacy_score", evaluation.privacy_score, policy.min_privacy_score, "Attack-inspired aggregate privacy gate")
        minimum("constraint_score", evaluation.constraint_score, policy.min_constraint_score, "Domain and engineering constraints must pass independently")
        minimum("range_score", evaluation.range_score, policy.min_range_score, "Generated numeric values must remain inside approved support")
        minimum("condition_match_rate", condition_match_rate, 1.0, "Every released row must satisfy the requested generation conditions")
        checks.append(GateCheck("intended_use_complete", intended_use_complete, "blocker", intended_use_complete, True, "Purpose, recipient where required, and retention must be valid"))
        minimum(
            "membership_attack_score",
            evaluation.membership_attack_score,
            policy.min_membership_attack_score,
            "Train membership should not be easier to infer than holdout membership",
        )
        exact_rate = evaluation.details.get("privacy", {}).get("exact_duplicate_rate")
        maximum("exact_duplicate_rate", exact_rate, policy.max_exact_duplicate_rate, "Direct record reuse is release-sensitive")
        maximum(
            "holdout_similarity_gap",
            evaluation.holdout_similarity_gap,
            policy.max_holdout_similarity_gap,
            "Train-vs-holdout gap is an overfit warning",
        )

        if policy.min_utility_score is not None:
            minimum("utility_score", evaluation.utility_score, policy.min_utility_score, "Use-case utility threshold")
        compliance_passed = bool(getattr(compliance, "passed", False))
        checks.append(
            GateCheck(
                "compliance_precheck",
                compliance_passed,
                "blocker",
                compliance_passed,
                True,
                "Pre-generation privacy/compliance blockers must be resolved",
            )
        )
        checks.append(
            GateCheck(
                "modality_appropriate_evaluation",
                modality_appropriate_evaluation,
                "blocker",
                modality_appropriate_evaluation,
                True,
                "The generator and evaluator must test the structure and dynamics of the declared modality",
            )
        )
        checks.append(
            GateCheck(
                "constraint_warnings_reviewed",
                constraint_warning_count == 0,
                "review",
                constraint_warning_count,
                0,
                "Non-blocking domain warnings require an accountable review before the artifact is treated as fully approved",
            )
        )
        if policy.require_holdout:
            checks.append(GateCheck("independent_holdout", holdout_independent, "blocker", holdout_independent, True, "Training data cannot serve as its own release test"))
        if policy.require_no_direct_identifiers:
            retained = set(getattr(compliance, "retained_columns", []))
            risky = set(getattr(compliance, "pii_columns", [])) | set(getattr(compliance, "identifier_columns", []))
            residual = sorted(retained.intersection(risky))
            checks.append(GateCheck("direct_identifiers_removed", not residual, "blocker", residual, [], "Detected identifiers cannot remain in a released dataset"))
        if policy.require_formal_dp:
            checks.append(GateCheck("formal_dp_accounting", formal_dp_verified, "blocker", formal_dp_verified, True, "DP claims require an accountant and recorded epsilon/delta"))
        if policy.require_domain_approval:
            checks.append(GateCheck("domain_owner_approval", domain_approved, "review", domain_approved, True, "A domain owner must approve intended use and constraints"))
        if policy.require_privacy_approval:
            checks.append(GateCheck("privacy_owner_approval", privacy_approved, "review", privacy_approved, True, "A privacy owner must approve recipient and release context"))

        blockers = [c for c in checks if not c.passed and c.severity == "blocker"]
        reviews = [c for c in checks if not c.passed and c.severity == "review"]
        if blockers:
            decision = ReleaseDecision.BLOCKED
        elif reviews:
            decision = ReleaseDecision.REVIEW
        else:
            decision = ReleaseDecision.APPROVED

        if policy.risk_tier == RiskTier.REGULATED and not policy.require_formal_dp:
            limitations.append("Formal differential privacy is not automatically required for every regulated use; if claimed or required, supply a custom policy and verified accountant evidence.")
        if not compliance_passed:
            limitations.extend(list(getattr(compliance, "warnings", [])))
        limitations.append("A release decision does not establish GDPR, HIPAA, DPDP, PCI, safety, or sector compliance; legal, privacy, security, and domain obligations remain contextual.")
        limitations.append("Scores describe the evaluated dataset, recipient model, holdout, and threat assumptions; they are not universal anonymity guarantees.")
        return ReleaseAssessment(decision=decision, risk_tier=policy.risk_tier, checks=checks, limitations=limitations)
