"""Scenario-as-code contracts and non-compensating business acceptance."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any


@dataclass(frozen=True)
class AcceptanceCriterion:
    metric: str
    op: str
    threshold: float
    blocker: bool = True

    def evaluate(self, metrics: dict[str, float]) -> bool:
        if self.metric not in metrics:
            return False
        value = float(metrics[self.metric])
        operations = {
            "ge": value >= self.threshold,
            "gt": value > self.threshold,
            "le": value <= self.threshold,
            "lt": value < self.threshold,
            "eq": value == self.threshold,
        }
        if self.op not in operations:
            raise ValueError(f"unsupported criterion op: {self.op}")
        return operations[self.op]


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    name: str
    buyer_decision: str
    operational_definition: str
    expected_outcome: str
    severity: str
    required_validators: tuple[str, ...]
    acceptance: tuple[AcceptanceCriterion, ...]
    prohibited_uses: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def validate(self) -> list[str]:
        issues: list[str] = []
        for field_name in ("scenario_id", "name", "buyer_decision", "operational_definition", "expected_outcome"):
            if not str(getattr(self, field_name)).strip():
                issues.append(f"{field_name} is required")
        if self.severity not in {"low", "medium", "high", "critical"}:
            issues.append("severity must be low, medium, high, or critical")
        if not self.acceptance:
            issues.append("at least one acceptance criterion is required")
        metric_names = [criterion.metric for criterion in self.acceptance]
        if len(metric_names) != len(set(metric_names)):
            issues.append("acceptance metric names must be unique")
        for criterion in self.acceptance:
            if criterion.op not in {"ge", "gt", "le", "lt", "eq"}:
                issues.append(f"unsupported criterion op for {criterion.metric}: {criterion.op}")
            if not math.isfinite(float(criterion.threshold)):
                issues.append(f"criterion threshold must be finite: {criterion.metric}")
        if not self.required_validators:
            issues.append("at least one accountable validator is required")
        return issues


@dataclass
class ScenarioAssessment:
    scenario_id: str
    approved: bool
    metric_checks: dict[str, bool]
    validator_checks: dict[str, bool]
    metrics: dict[str, float]
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def assess_scenario(
    definition: ScenarioDefinition,
    *,
    metrics: dict[str, float],
    validator_approvals: dict[str, bool],
) -> ScenarioAssessment:
    issues = definition.validate()
    if issues:
        raise ValueError("invalid scenario definition: " + "; ".join(issues))
    metric_checks = {criterion.metric: criterion.evaluate(metrics) for criterion in definition.acceptance}
    validator_checks = {name: bool(validator_approvals.get(name, False)) for name in definition.required_validators}
    failed_blockers = [
        criterion.metric for criterion in definition.acceptance
        if criterion.blocker and not metric_checks[criterion.metric]
    ]
    approved = not failed_blockers and all(validator_checks.values())
    limitations: list[str] = []
    if failed_blockers:
        limitations.append("failed blocker metrics: " + ", ".join(failed_blockers))
    failed_advisory = [
        criterion.metric for criterion in definition.acceptance
        if not criterion.blocker and not metric_checks[criterion.metric]
    ]
    if failed_advisory:
        limitations.append("failed advisory metrics: " + ", ".join(failed_advisory))
    missing = [name for name, passed in validator_checks.items() if not passed]
    if missing:
        limitations.append("missing validator approvals: " + ", ".join(missing))
    return ScenarioAssessment(definition.scenario_id, approved, metric_checks, validator_checks, metrics, limitations)
