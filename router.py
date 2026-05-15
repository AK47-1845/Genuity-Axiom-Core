"""Industrial model routing for Genuity Axiom."""

from __future__ import annotations

from dataclasses import dataclass, field

from .profile import DatasetProfile


@dataclass
class GeneratorDecision:
    actual_order: list[str]
    frontier_order: list[str]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    strategy: str = "balanced"

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "actual_order": self.actual_order,
            "frontier_order": self.frontier_order,
            "reasons": self.reasons,
            "warnings": self.warnings,
        }


class IndustrialModelRouter:
    """Selects a generator ladder from data shape, modality, privacy, and risk."""

    def select(
        self,
        profile: DatasetProfile,
        *,
        privacy_level: str = "standard",
        target_col: str | None = None,
        quality_mode: str = "balanced",
    ) -> GeneratorDecision:
        reasons: list[str] = []
        warnings: list[str] = []
        n_rows = profile.n_rows
        n_cols = profile.n_cols
        numeric_ratio = len(profile.numeric_columns) / max(n_cols, 1)
        categorical_ratio = len(profile.categorical_columns) / max(n_cols, 1)
        high_dimensional = n_cols >= 50 or n_cols > max(n_rows // 4, 20)
        small_data = n_rows < 500
        large_data = n_rows >= 50_000
        rare_event = "target_imbalance" in profile.risk_flags and bool(target_col)
        role_counts = {
            role: list(profile.semantic_roles.values()).count(role)
            for role in set(profile.semantic_roles.values())
        }

        actual: list[str] = []
        frontier: list[str] = []

        if privacy_level in {"strict", "dp-ready"}:
            frontier.extend(["mst_dp", "aim_dp", "pate_gan", "dp_tvae"])
            actual.extend(["stratified_bootstrap", "gaussian_copula", "bootstrap"])
            reasons.append("strict privacy prioritizes DP-capable generators before neural fidelity models")
            if privacy_level == "dp-ready":
                warnings.append("formal DP adapters are planned; current local fallback is privacy-gated but not formal DP")

        if profile.modality == "time_series":
            frontier.extend(["timegan", "doppelganger", "diffusion_ts", "fourier_synth", "neural_cde"])
            actual.extend(["stratified_bootstrap", "gaussian_copula", "bootstrap"])
            reasons.append("time-series data needs sequence-aware models; local fallback preserves distributions until adapters are installed")
        elif profile.modality == "relational_table":
            frontier.extend(["relational_graph_synth", "pk_fk_synth", "hierarchical_copula"])
            actual.extend(["stratified_bootstrap", "gaussian_copula", "bootstrap"])
            reasons.append("relational-table signals require primary-key/foreign-key preservation")
        elif profile.modality == "textual":
            frontier.extend(["engineering_log_lm", "controlled_text_augmenter", "ngram_privacy_baseline"])
            actual.extend(["stratified_bootstrap", "bootstrap"])
            reasons.append("textual engineering logs need text-native models and leakage screening")
        else:
            if small_data:
                actual.extend(["gaussian_copula", "kde", "stratified_bootstrap", "bootstrap"])
                frontier.extend(["copula", "vine_copula", "arf"])
                reasons.append("small tabular data favors copula/KDE over neural models to reduce overfit")
            elif high_dimensional:
                actual.extend(["gmm", "gaussian_copula", "kde", "stratified_bootstrap", "bootstrap"])
                frontier.extend(["masked_predictor", "arf", "forest_diffusion", "tabddpm"])
                reasons.append("wide table detected; tree/masked/diffusion models are preferred over vanilla GANs")
            elif numeric_ratio >= 0.65:
                actual.extend(["kde", "gmm", "gaussian_copula", "stratified_bootstrap", "bootstrap"])
                frontier.extend(["arf", "tabudiff", "tabddpm", "tvae"])
                reasons.append("numeric-heavy engineering data benefits from KDE/GMM/Copula baselines and diffusion adapters")
            elif categorical_ratio >= 0.4:
                actual.extend(["stratified_bootstrap", "gaussian_copula", "bootstrap"])
                frontier.extend(["arf", "ctgan", "ctabgan_plus", "real_tabformer"])
                reasons.append("categorical-heavy mixed data favors ARF/CTGAN-style conditional modeling")
            else:
                actual.extend(["gmm", "kde", "gaussian_copula", "stratified_bootstrap", "bootstrap"])
                frontier.extend(["automl_ensemble", "arf", "tvae", "ctgan", "tabudiff"])
                reasons.append("general mixed tabular data uses an AutoML-style ladder")

        if rare_event:
            actual = ["stratified_bootstrap"] + actual
            frontier = ["conditional_sampler", "smote_hybrid", "arf"] + frontier
            reasons.append("rare-event target detected; conditional/stratified sampling is placed first")

        if role_counts.get("operating_condition", 0) and role_counts.get("response_output", 0):
            frontier = ["io_coherence_selector", "causal_fidelity_adapter"] + frontier
            reasons.append("input-output engineering roles detected; causal/IO coherence checks are recommended")

        if role_counts.get("geometry", 0) and role_counts.get("material_descriptor", 0):
            frontier = ["physics_residual_sampler", "constraint_rejection_sampler"] + frontier
            reasons.append("geometry and material roles detected; physics residual checks should gate generated rows")

        if large_data:
            actual = [g for g in actual if g not in {"gmm"}] + ["gmm"]
            frontier = ["arf", "forest_diffusion", "subsampled_automl"] + frontier
            reasons.append("large data detected; CPU-stable and subsampled methods are prioritized")

        if quality_mode == "max":
            frontier = ["automl_ensemble", "composite_holdout_selector"] + frontier
            reasons.append("max quality mode requests ensemble selection with holdout ranking")
        elif quality_mode == "fast":
            actual = ["stratified_bootstrap", "gaussian_copula", "bootstrap"] + actual
            reasons.append("fast mode prioritizes deterministic statistical generation")

        return GeneratorDecision(
            actual_order=_dedupe(actual + profile.recommended_generators + ["bootstrap"]),
            frontier_order=_dedupe(frontier),
            reasons=_dedupe(reasons),
            warnings=_dedupe(warnings),
            strategy=quality_mode,
        )


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
