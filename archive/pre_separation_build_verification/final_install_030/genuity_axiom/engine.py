"""Top-level Genuity Axiom engine."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from dataclasses import asdict

import pandas as pd

from .approvals import ApprovalEvidence, has_approval
from .compliance import ComplianceGate, ComplianceReport, PrivacyPolicy
from .constraints import ConstraintReport, EngineeringConstraintSet
from .datacard import DataCard
from .evaluator import EvaluationReport, SyntheticEvaluator
from .generators import FallbackSynthesizer, GeneratorAttempt
from .governance import IntendedUse, RunManifest
from .profile import DatasetProfile, EngineeringProfiler
from .preprocessing import find_nested_columns
from .privacy_evidence import DifferentialPrivacyEvidence
from .release import ReleaseAssessment, ReleasePolicy, RiskTier, SyntheticReleaseGate
from .router import GeneratorDecision, IndustrialModelRouter


_PACKAGE_VERSION = "0.3.0"


@dataclass
class SynthesisConfig:
    n_samples: int | None = None
    target_col: str | None = None
    time_col: str | None = None
    entity_col: str | None = None
    privacy_level: str = "standard"
    compliance_strategy: str = "drop"
    conditions: dict | None = None
    constraints: EngineeringConstraintSet | None = None
    fallback_order: list[str] | None = None
    random_state: int | None = 42
    repair_constraints: bool = True
    holdout_fraction: float = 0.2
    quality_mode: str = "balanced"
    risk_tier: str = "internal"
    release_policy: ReleasePolicy | None = None
    intended_use: IntendedUse = field(
        default_factory=lambda: IntendedUse(
            purpose="internal synthetic-data evaluation",
            prohibited_uses=["production safety decisions without domain validation"],
        )
    )
    formal_dp_evidence: DifferentialPrivacyEvidence | None = None
    approvals: list[ApprovalEvidence] = field(default_factory=list)


@dataclass
class GenerationResult:
    data: pd.DataFrame
    profile: DatasetProfile
    compliance: ComplianceReport
    constraints: ConstraintReport
    evaluation: EvaluationReport
    generator_name: str
    decision: GeneratorDecision | None = None
    data_card: DataCard | None = None
    attempts: list[GeneratorAttempt] = field(default_factory=list)
    candidate_scores: dict[str, float] = field(default_factory=dict)
    release: ReleaseAssessment | None = None
    manifest: RunManifest | None = None

    def to_report(self) -> dict:
        return {
            "generator_name": self.generator_name,
            "decision": None if self.decision is None else self.decision.to_dict(),
            "profile": self.profile.to_dict(),
            "compliance": self.compliance.to_dict(),
            "constraints": self.constraints.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "data_card": None if self.data_card is None else self.data_card.to_dict(),
            "attempts": [attempt.__dict__ for attempt in self.attempts],
            "candidate_scores": self.candidate_scores,
            "release": None if self.release is None else self.release.to_dict(),
            "manifest": None if self.manifest is None else self.manifest.to_dict(),
        }


class GenuityAxiomEngine:
    """One-call synthesis workflow for engineering teams."""

    def __init__(
        self,
        *,
        profiler: EngineeringProfiler | None = None,
        evaluator: SyntheticEvaluator | None = None,
        router: IndustrialModelRouter | None = None,
    ) -> None:
        self.profiler = profiler or EngineeringProfiler()
        self.evaluator = evaluator or SyntheticEvaluator()
        self.router = router or IndustrialModelRouter()

    def synthesize(
        self,
        df: pd.DataFrame,
        *,
        config: SynthesisConfig | None = None,
        n_samples: int | None = None,
        target_col: str | None = None,
        time_col: str | None = None,
        entity_col: str | None = None,
        privacy_level: str | None = None,
        conditions: dict | None = None,
        constraints: EngineeringConstraintSet | None = None,
    ) -> GenerationResult:
        cfg = config or SynthesisConfig()
        nested_columns = find_nested_columns(df)
        if nested_columns:
            raise ValueError(
                "nested values require explicit privacy-aware preparation; call prepare_messy_table first for columns: "
                + ", ".join(nested_columns)
            )
        if n_samples is not None:
            cfg.n_samples = n_samples
        if target_col is not None:
            cfg.target_col = target_col
        if time_col is not None:
            cfg.time_col = time_col
        if entity_col is not None:
            cfg.entity_col = entity_col
        if privacy_level is not None:
            cfg.privacy_level = privacy_level
        if conditions is not None:
            cfg.conditions = conditions
        if constraints is not None:
            cfg.constraints = constraints

        requested_n = cfg.n_samples or len(df)
        policy = PrivacyPolicy(level=cfg.privacy_level)
        gate = ComplianceGate(policy=policy, strategy=cfg.compliance_strategy)
        clean_df, compliance_report = gate.scrub(df)
        if clean_df.empty:
            raise ValueError("Compliance gate removed every column; provide an allowlist or mask strategy")
        _validate_conditions(clean_df, cfg.conditions)

        profile = self.profiler.profile(
            clean_df,
            time_col=cfg.time_col,
            entity_col=cfg.entity_col,
            target_col=cfg.target_col,
        )
        active_constraints = cfg.constraints or EngineeringConstraintSet.from_dataframe(
            clean_df, profile.engineering_domain
        )
        decision = self.router.select(
            profile,
            privacy_level=cfg.privacy_level,
            target_col=cfg.target_col,
            quality_mode=cfg.quality_mode,
        )
        fallback_order = cfg.fallback_order or decision.actual_order
        train_df, holdout_df, holdout_independent = _split_holdout(
            clean_df,
            fraction=cfg.holdout_fraction,
            random_state=cfg.random_state,
        )
        synthesizer = FallbackSynthesizer(
            fallback_order=fallback_order,
            random_state=cfg.random_state,
        )
        if cfg.quality_mode == "max":
            output = synthesizer.synthesize_best(
                train_df,
                requested_n,
                reference_df=holdout_df,
                evaluator=self.evaluator,
                constraints=active_constraints,
                target_col=cfg.target_col,
                conditions=cfg.conditions,
            )
        else:
            output = synthesizer.synthesize(
                train_df,
                requested_n,
                conditions=cfg.conditions,
            )

        synthetic = output.data
        if cfg.repair_constraints:
            synthetic, constraint_report = active_constraints.repair(synthetic)
        else:
            constraint_report = active_constraints.validate(synthetic)

        evaluation = self.evaluator.evaluate(
            holdout_df,
            synthetic,
            constraints=active_constraints,
            train_data=train_df,
            target_col=cfg.target_col,
        )
        condition_match_rate = _condition_match_rate(synthetic, cfg.conditions)
        evaluation.details["condition_match_rate"] = condition_match_rate
        release_policy = cfg.release_policy or ReleasePolicy.for_tier(cfg.risk_tier)
        if cfg.release_policy is None and cfg.target_col:
            utility_threshold = {
                RiskTier.SANDBOX: 0.50,
                RiskTier.INTERNAL: 0.55,
                RiskTier.EXTERNAL: 0.65,
                RiskTier.REGULATED: 0.70,
            }[release_policy.risk_tier]
            release_policy = replace(release_policy, min_utility_score=utility_threshold)
        release = SyntheticReleaseGate().assess(
            evaluation=evaluation,
            compliance=compliance_report,
            policy=release_policy,
            formal_dp_verified=bool(cfg.formal_dp_evidence and cfg.formal_dp_evidence.valid),
            domain_approved=has_approval(cfg.approvals, "domain_owner"),
            privacy_approved=has_approval(cfg.approvals, "privacy_owner"),
            holdout_independent=holdout_independent,
            modality_appropriate_evaluation=profile.modality == "tabular",
            constraint_warning_count=constraint_report.warning_violations,
            condition_match_rate=condition_match_rate,
        )
        result = GenerationResult(
            data=synthetic,
            profile=profile,
            compliance=compliance_report,
            constraints=constraint_report,
            evaluation=evaluation,
            generator_name=output.generator_name,
            decision=decision,
            attempts=output.attempts,
            candidate_scores=output.candidate_scores,
            release=release,
        )
        config_record = asdict(cfg)
        if cfg.constraints is not None:
            config_record["constraints"] = [rule.__dict__ for rule in cfg.constraints.rules]
        result.manifest = RunManifest.build(
            package_version=_PACKAGE_VERSION,
            generator=output.generator_name,
            random_state=cfg.random_state,
            input_data=clean_df,
            output_data=synthetic,
            configuration=config_record,
            intended_use=cfg.intended_use,
            release=release.to_dict(),
            limitations=release.limitations,
        )
        result.data_card = DataCard.from_result(result)
        return result


PramanaEngine = GenuityAxiomEngine


def _split_holdout(
    df: pd.DataFrame,
    *,
    fraction: float,
    random_state: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    if fraction <= 0 or len(df) < 50:
        return df.reset_index(drop=True), df.reset_index(drop=True), False
    fraction = min(max(float(fraction), 0.05), 0.4)
    holdout = df.sample(frac=fraction, random_state=random_state)
    train = df.drop(index=holdout.index)
    if train.empty or holdout.empty:
        return df.reset_index(drop=True), df.reset_index(drop=True), False
    return train.reset_index(drop=True), holdout.reset_index(drop=True), True


def _validate_conditions(df: pd.DataFrame, conditions: dict | None) -> None:
    if not conditions:
        return
    missing = sorted(set(conditions) - set(df.columns), key=str)
    if missing:
        raise ValueError("conditions reference missing or privacy-removed columns: " + ", ".join(map(str, missing)))
    if _condition_match_rate(df, conditions) == 0.0:
        raise ValueError("no source rows support all requested conditions; use the rare-event/simulator workflow")


def _condition_match_rate(df: pd.DataFrame, conditions: dict | None) -> float:
    if not conditions or df.empty:
        return 1.0
    mask = pd.Series(True, index=df.index)
    for column, expected in conditions.items():
        if column not in df:
            return 0.0
        if not isinstance(expected, dict):
            mask &= df[column] == expected
            continue
        if "ge" in expected:
            mask &= df[column] >= expected["ge"]
        if "gt" in expected:
            mask &= df[column] > expected["gt"]
        if "le" in expected:
            mask &= df[column] <= expected["le"]
        if "lt" in expected:
            mask &= df[column] < expected["lt"]
        if "in" in expected:
            mask &= df[column].isin(expected["in"])
    return float(mask.fillna(False).mean())
