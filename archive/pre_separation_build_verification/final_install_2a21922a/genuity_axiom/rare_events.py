"""Constraint-aware rare-event and boundary scenario generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .constraints import EngineeringConstraintSet


@dataclass(frozen=True)
class RareEventSpec:
    name: str
    conditions: dict[str, Any] = field(default_factory=dict)
    tail_columns: tuple[str, ...] = ()
    tail: str = "both"
    quantile: float = 0.90
    min_novelty_distance: float = 0.0
    oversample_factor: int = 8


@dataclass
class RareEventReport:
    requested: int
    generated: int
    candidates: int
    condition_match_rate: float
    constraint_pass_rate: float
    duplicate_rate: float
    tail_coverage: dict[str, float]
    novelty_pass_rate: float = 1.0
    minimum_observed_distance: float | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.generated == self.requested and self.condition_match_rate == 1.0 and self.constraint_pass_rate == 1.0

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["passed"] = self.passed
        return payload


class RareEventGenerator:
    """Produces boundary candidates, rejects invalid rows, and reports coverage."""

    def __init__(self, *, random_state: int | None = 42) -> None:
        self.random_state = random_state
        self.rng = np.random.default_rng(random_state)

    def generate(
        self,
        df: pd.DataFrame,
        *,
        n_samples: int,
        spec: RareEventSpec,
        constraints: EngineeringConstraintSet | None = None,
    ) -> tuple[pd.DataFrame, RareEventReport]:
        if n_samples <= 0 or df.empty:
            raise ValueError("n_samples and source data must be non-empty")
        if spec.tail not in {"low", "high", "both"}:
            raise ValueError("tail must be low, high, or both")
        if not 0.5 < spec.quantile < 1.0:
            raise ValueError("quantile must be between 0.5 and 1.0")
        if spec.min_novelty_distance < 0:
            raise ValueError("min_novelty_distance cannot be negative")
        source = self._condition(df, spec.conditions)
        if source.empty:
            raise ValueError("no source rows satisfy requested rare-event conditions")
        candidate_n = max(n_samples, n_samples * max(1, spec.oversample_factor))
        candidates = source.sample(n=candidate_n, replace=True, random_state=self.random_state).reset_index(drop=True).copy()
        tail_coverage: dict[str, float] = {}
        for col in spec.tail_columns:
            if col not in df or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            values = pd.to_numeric(df[col], errors="coerce").dropna()
            if values.empty:
                continue
            low = float(values.quantile(1.0 - spec.quantile))
            high = float(values.quantile(spec.quantile))
            std = float(values.std(ddof=0) or 1.0)
            choose_high = self.rng.random(candidate_n) >= 0.5
            if spec.tail == "high":
                choose_high[:] = True
            elif spec.tail == "low":
                choose_high[:] = False
            high_values = self.rng.uniform(high, float(values.max()) + 0.05 * std, size=candidate_n)
            low_values = self.rng.uniform(float(values.min()) - 0.05 * std, low, size=candidate_n)
            candidates[col] = np.where(choose_high, high_values, low_values)
            tail_coverage[col] = float(((candidates[col] >= high) | (candidates[col] <= low)).mean())
        candidates = self._apply_conditions(candidates, spec.conditions)
        if constraints:
            mask = pd.Series(True, index=candidates.index)
            for rule in constraints.rules:
                try:
                    mask &= rule.mask(candidates).fillna(False)
                except Exception:
                    mask &= False
            constraint_rate = float(mask.mean())
        else:
            mask = pd.Series(True, index=candidates.index)
            constraint_rate = 1.0
        distances = self._novelty_distances(df, candidates)
        if distances is not None and spec.min_novelty_distance > 0:
            novelty_mask = pd.Series(distances >= spec.min_novelty_distance, index=candidates.index)
            novelty_rate = float(novelty_mask.mean())
            mask &= novelty_mask
        elif distances is None and spec.min_novelty_distance > 0:
            raise ValueError("novelty distance requires at least one numeric source column")
        else:
            novelty_rate = 1.0
        valid = candidates[mask].copy()
        valid_distances = None if distances is None else distances[mask.to_numpy()]
        valid = valid.drop_duplicates().head(n_samples).reset_index(drop=True)
        if len(valid) < n_samples:
            warnings = ["Insufficient valid unique candidates; increase source coverage, relax an approved condition, or use a domain simulator."]
        else:
            warnings = []
        condition_rate = float(self._condition_mask(valid, spec.conditions).mean()) if len(valid) else 0.0
        duplicate_rate = 1.0 - len(candidates.drop_duplicates()) / max(len(candidates), 1)
        return valid, RareEventReport(
            requested=n_samples,
            generated=len(valid),
            candidates=len(candidates),
            condition_match_rate=condition_rate,
            constraint_pass_rate=constraint_rate,
            duplicate_rate=duplicate_rate,
            tail_coverage=tail_coverage,
            novelty_pass_rate=novelty_rate,
            minimum_observed_distance=(
                None if valid_distances is None or len(valid_distances) == 0 else float(valid_distances.min())
            ),
            warnings=warnings,
        )

    def _condition(self, df: pd.DataFrame, conditions: dict[str, Any]) -> pd.DataFrame:
        return df[self._condition_mask(df, conditions)]

    def _condition_mask(self, df: pd.DataFrame, conditions: dict[str, Any]) -> pd.Series:
        mask = pd.Series(True, index=df.index)
        for col, expected in conditions.items():
            if col not in df:
                return pd.Series(False, index=df.index)
            if isinstance(expected, dict):
                if "ge" in expected:
                    mask &= df[col] >= expected["ge"]
                if "gt" in expected:
                    mask &= df[col] > expected["gt"]
                if "le" in expected:
                    mask &= df[col] <= expected["le"]
                if "lt" in expected:
                    mask &= df[col] < expected["lt"]
                if "in" in expected:
                    mask &= df[col].isin(expected["in"])
            else:
                mask &= df[col] == expected
        return mask.fillna(False)

    def _apply_conditions(self, df: pd.DataFrame, conditions: dict[str, Any]) -> pd.DataFrame:
        output = df.copy()
        for col, expected in conditions.items():
            if col not in output:
                continue
            if not isinstance(expected, dict):
                output[col] = expected
            elif "in" in expected and expected["in"]:
                output[col] = self.rng.choice(expected["in"], size=len(output))
            else:
                if "ge" in expected:
                    output[col] = pd.to_numeric(output[col], errors="coerce").clip(lower=expected["ge"])
                if "gt" in expected:
                    output[col] = pd.to_numeric(output[col], errors="coerce").clip(lower=np.nextafter(float(expected["gt"]), np.inf))
                if "le" in expected:
                    output[col] = pd.to_numeric(output[col], errors="coerce").clip(upper=expected["le"])
                if "lt" in expected:
                    output[col] = pd.to_numeric(output[col], errors="coerce").clip(upper=np.nextafter(float(expected["lt"]), -np.inf))
        return output

    def _novelty_distances(self, source: pd.DataFrame, candidates: pd.DataFrame) -> np.ndarray | None:
        numeric = [
            col for col in source.columns
            if col in candidates and pd.api.types.is_numeric_dtype(source[col])
        ]
        if not numeric:
            return None
        reference = source[numeric].apply(pd.to_numeric, errors="coerce")
        candidate = candidates[numeric].apply(pd.to_numeric, errors="coerce")
        medians = reference.median(numeric_only=True)
        reference = reference.fillna(medians).fillna(0.0)
        candidate = candidate.fillna(medians).fillna(0.0)
        scale = reference.std(ddof=0).replace(0, 1.0).fillna(1.0)
        ref = ((reference - reference.mean()) / scale).to_numpy(dtype=float)
        cand = ((candidate - reference.mean()) / scale).to_numpy(dtype=float)
        if len(ref) > 2000:
            indices = self.rng.choice(len(ref), size=2000, replace=False)
            ref = ref[indices]
        minima = np.empty(len(cand), dtype=float)
        ref_norm = (ref * ref).sum(axis=1)
        for start in range(0, len(cand), 256):
            batch = cand[start:start + 256]
            squared = (batch * batch).sum(axis=1)[:, None] + ref_norm[None, :] - 2.0 * (batch @ ref.T)
            minima[start:start + len(batch)] = np.sqrt(np.maximum(squared.min(axis=1), 0.0))
        return minima
