"""Lightweight source-drift evidence and revalidation triggers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FeatureDrift:
    column: str
    kind: str
    distribution_drift: float
    missingness_delta: float
    threshold: float

    @property
    def alert(self) -> bool:
        return self.distribution_drift > self.threshold or self.missingness_delta > 0.10

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "kind": self.kind,
            "distribution_drift": self.distribution_drift,
            "missingness_delta": self.missingness_delta,
            "threshold": self.threshold,
            "alert": self.alert,
        }


@dataclass
class DatasetDriftReport:
    added_columns: list[str]
    removed_columns: list[str]
    features: list[FeatureDrift]
    requires_revalidation: bool
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_columns": self.added_columns,
            "removed_columns": self.removed_columns,
            "features": [feature.to_dict() for feature in self.features],
            "requires_revalidation": self.requires_revalidation,
            "limitations": self.limitations,
        }


class DriftMonitor:
    """Compares current source data with the release reference distribution."""

    def compare(self, reference: pd.DataFrame, current: pd.DataFrame) -> DatasetDriftReport:
        added = sorted(set(current.columns) - set(reference.columns), key=str)
        removed = sorted(set(reference.columns) - set(current.columns), key=str)
        features: list[FeatureDrift] = []
        for col in [c for c in reference.columns if c in current.columns]:
            missing_delta = abs(float(reference[col].isna().mean()) - float(current[col].isna().mean()))
            if pd.api.types.is_numeric_dtype(reference[col]) and pd.api.types.is_numeric_dtype(current[col]):
                score = _population_stability_index(reference[col], current[col])
                features.append(FeatureDrift(str(col), "numeric_psi", score, missing_delta, 0.20))
            else:
                score = _categorical_tvd(reference[col], current[col])
                features.append(FeatureDrift(str(col), "categorical_tvd", score, missing_delta, 0.10))
        requires = bool(added or removed or any(feature.alert for feature in features))
        return DatasetDriftReport(
            added,
            removed,
            features,
            requires,
            ["Default drift thresholds are screening values; owners must calibrate them to the operating decision and false-alert cost."],
        )


def _population_stability_index(reference: pd.Series, current: pd.Series) -> float:
    ref = pd.to_numeric(reference, errors="coerce").dropna().to_numpy(dtype=float)
    cur = pd.to_numeric(current, errors="coerce").dropna().to_numpy(dtype=float)
    if len(ref) < 5 or len(cur) < 5:
        return 0.0 if len(ref) == len(cur) else 1.0
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, 11)))
    if len(edges) < 3:
        return 0.0 if np.isclose(np.mean(ref), np.mean(cur)) else 1.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref_hist = np.histogram(ref, bins=edges)[0] / len(ref)
    cur_hist = np.histogram(cur, bins=edges)[0] / len(cur)
    epsilon = 1e-6
    ref_hist = np.clip(ref_hist, epsilon, None)
    cur_hist = np.clip(cur_hist, epsilon, None)
    return float(np.sum((cur_hist - ref_hist) * np.log(cur_hist / ref_hist)))


def _categorical_tvd(reference: pd.Series, current: pd.Series) -> float:
    ref = reference.astype("object").fillna("__NA__").value_counts(normalize=True)
    cur = current.astype("object").fillna("__NA__").value_counts(normalize=True)
    labels = set(ref.index).union(cur.index)
    return float(0.5 * sum(abs(float(ref.get(v, 0.0)) - float(cur.get(v, 0.0))) for v in labels))
