"""Run data-card reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class DataCard:
    title: str
    created_at: str
    summary: dict
    risks: list[str]
    recommended_next_actions: list[str]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "created_at": self.created_at,
            "summary": self.summary,
            "risks": self.risks,
            "recommended_next_actions": self.recommended_next_actions,
        }

    @classmethod
    def from_result(cls, result: object) -> "DataCard":
        evaluation = result.evaluation
        risks: list[str] = []
        actions: list[str] = []
        release = getattr(result, "release", None)

        if result.compliance.removed_columns:
            risks.append("direct_or_quasi_identifiers_removed")
        if not result.constraints.passed:
            risks.append("constraint_violations_remaining")
            actions.append("tighten domain constraints or use rejection sampling")
        if getattr(result.constraints, "warning_violations", 0):
            risks.append("domain_constraint_warnings_require_review")
            actions.append("have the accountable domain owner review non-blocking constraint warnings")
        if evaluation.privacy_score < 0.75:
            risks.append("privacy_score_below_release_threshold")
            actions.append("increase privacy level, reduce exact reuse, or use DP adapter")
        if evaluation.utility_score is not None and evaluation.utility_score < 0.55:
            risks.append("utility_score_below_training_threshold")
            actions.append("run model router in max mode or add task-specific conditional generation")
        if evaluation.holdout_similarity_gap is not None and evaluation.holdout_similarity_gap > 0.15:
            risks.append("possible_train_holdout_overfit_gap")
            actions.append("increase holdout size and run membership audit")

        if release is not None and not release.passed:
            risks.append(f"release_{release.decision.value}")
            failed = [check.name for check in release.checks if not check.passed]
            actions.append("resolve failed release gates: " + ", ".join(failed))

        if not actions and release is not None and release.passed:
            actions.append("eligible for internal engineering sandbox use after human domain review")
        elif not actions:
            actions.append("run the configured release gate before sharing or operational use")

        return cls(
            title="Genuity Axiom Synthetic Data Card",
            created_at=datetime.now(timezone.utc).isoformat(),
            summary={
                "generator": result.generator_name,
                "rows": len(result.data),
                "columns": len(result.data.columns),
                "domain": result.profile.engineering_domain,
                "modality": result.profile.modality,
                "overall_score": evaluation.overall_score,
                "privacy_score": evaluation.privacy_score,
                "constraint_score": evaluation.constraint_score,
                "release_decision": None if release is None else release.decision.value,
                "risk_tier": None if release is None else release.risk_tier.value,
            },
            risks=risks,
            recommended_next_actions=actions,
        )
