"""Evaluation reports for synthetic engineering data."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .constraints import EngineeringConstraintSet


@dataclass
class EvaluationReport:
    overall_score: float
    similarity_score: float
    correlation_score: float
    privacy_score: float
    utility_score: float | None = None
    missingness_score: float | None = None
    range_score: float | None = None
    membership_attack_score: float | None = None
    holdout_similarity_gap: float | None = None
    detectability_score: float | None = None
    constraint_score: float | None = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "similarity_score": self.similarity_score,
            "correlation_score": self.correlation_score,
            "privacy_score": self.privacy_score,
            "utility_score": self.utility_score,
            "missingness_score": self.missingness_score,
            "range_score": self.range_score,
            "membership_attack_score": self.membership_attack_score,
            "holdout_similarity_gap": self.holdout_similarity_gap,
            "detectability_score": self.detectability_score,
            "constraint_score": self.constraint_score,
            "details": self.details,
        }


class SyntheticEvaluator:
    """Computes lightweight but useful quality, privacy, and safety metrics."""

    def evaluate(
        self,
        real: pd.DataFrame,
        synthetic: pd.DataFrame,
        *,
        constraints: EngineeringConstraintSet | None = None,
        train_data: pd.DataFrame | None = None,
        target_col: str | None = None,
    ) -> EvaluationReport:
        common = [c for c in real.columns if c in synthetic.columns]
        real = real[common].reset_index(drop=True)
        synthetic = synthetic[common].reset_index(drop=True)

        similarity, similarity_details = _similarity_score(real, synthetic)
        train_similarity = None
        holdout_gap = None
        if train_data is not None:
            train_common = [c for c in train_data.columns if c in synthetic.columns]
            if train_common:
                train_similarity, _ = _similarity_score(
                    train_data[train_common].reset_index(drop=True),
                    synthetic[train_common].reset_index(drop=True),
                )
                holdout_gap = max(0.0, float(train_similarity - similarity))
        correlation = _correlation_score(real, synthetic)
        privacy_reference = train_data if train_data is not None else real
        privacy, privacy_details = _privacy_score(privacy_reference, synthetic)
        membership_attack = None
        if train_data is not None and len(real) >= 5:
            membership_attack = _membership_attack_score(train_data, real, synthetic)
            if membership_attack is not None:
                privacy = 0.65 * privacy + 0.35 * membership_attack
        detectability = _detectability_score(real, synthetic)
        utility = _utility_score(
            train_data if train_data is not None else real,
            real,
            synthetic,
            target_col,
        )
        missingness = _missingness_score(real, synthetic)
        range_score = _range_score(
            pd.concat([privacy_reference, real], ignore_index=True),
            synthetic,
        )
        constraint_score = None
        if constraints:
            report = constraints.validate(synthetic)
            blocking_rules = sum(1 for rule in constraints.rules if rule.severity != "warning")
            denom = max(len(synthetic) * max(blocking_rules, 1), 1)
            constraint_score = 1.0 - min(report.blocking_violations / denom, 1.0)

        weighted = [
            (similarity, 0.35),
            (correlation, 0.20),
            (privacy, 0.25),
            (missingness, 0.05),
            (range_score, 0.05),
        ]
        if utility is not None:
            weighted.append((utility, 0.15))
        if detectability is not None:
            weighted.append((detectability, 0.10))
        if constraint_score is not None:
            weighted.append((constraint_score, 0.10))
        total_weight = sum(weight for _, weight in weighted)
        overall = sum(score * weight for score, weight in weighted) / total_weight

        return EvaluationReport(
            overall_score=float(_clamp01(overall)),
            similarity_score=float(_clamp01(similarity)),
            correlation_score=float(_clamp01(correlation)),
            privacy_score=float(_clamp01(privacy)),
            utility_score=None if utility is None else float(_clamp01(utility)),
            missingness_score=float(_clamp01(missingness)),
            range_score=float(_clamp01(range_score)),
            membership_attack_score=None if membership_attack is None else float(_clamp01(membership_attack)),
            holdout_similarity_gap=holdout_gap,
            detectability_score=None if detectability is None else float(_clamp01(detectability)),
            constraint_score=None if constraint_score is None else float(_clamp01(constraint_score)),
            details={
                "similarity": similarity_details,
                "privacy": privacy_details,
                "train_similarity": train_similarity,
                "constraint_warning_violations": (
                    None if constraints is None else constraints.validate(synthetic).warning_violations
                ),
            },
        )


def _similarity_score(real: pd.DataFrame, synthetic: pd.DataFrame) -> tuple[float, dict]:
    scores: list[float] = []
    details: dict = {}
    for col in real.columns:
        if pd.api.types.is_numeric_dtype(real[col]) and pd.api.types.is_numeric_dtype(
            synthetic[col]
        ):
            score = _numeric_distribution_score(real[col], synthetic[col])
        else:
            score = _categorical_distribution_score(real[col], synthetic[col])
        scores.append(score)
        details[col] = score
    return (float(np.mean(scores)) if scores else 1.0), details


def _numeric_distribution_score(real: pd.Series, synthetic: pd.Series) -> float:
    r = pd.to_numeric(real, errors="coerce").dropna().to_numpy(dtype=float)
    s = pd.to_numeric(synthetic, errors="coerce").dropna().to_numpy(dtype=float)
    if len(r) == 0 or len(s) == 0:
        return 0.0
    quantiles = np.linspace(0.05, 0.95, 19)
    rq = np.quantile(r, quantiles)
    sq = np.quantile(s, quantiles)
    scale = np.nanstd(r) or (np.nanmax(r) - np.nanmin(r)) or 1.0
    quantile_error = float(np.mean(np.abs(rq - sq)) / scale)
    mean_error = abs(float(np.mean(r) - np.mean(s))) / scale
    return _clamp01(1.0 - (0.7 * quantile_error + 0.3 * mean_error))


def _categorical_distribution_score(real: pd.Series, synthetic: pd.Series) -> float:
    r = real.astype("object").fillna("__NA__").value_counts(normalize=True)
    s = synthetic.astype("object").fillna("__NA__").value_counts(normalize=True)
    labels = sorted(set(r.index).union(set(s.index)), key=str)
    tvd = 0.5 * sum(abs(float(r.get(label, 0.0)) - float(s.get(label, 0.0))) for label in labels)
    return _clamp01(1.0 - tvd)


def _correlation_score(real: pd.DataFrame, synthetic: pd.DataFrame) -> float:
    numeric_cols = [
        c
        for c in real.columns
        if pd.api.types.is_numeric_dtype(real[c])
        and c in synthetic
        and pd.api.types.is_numeric_dtype(synthetic[c])
    ]
    if len(numeric_cols) < 2:
        return 1.0
    rc = real[numeric_cols].corr(numeric_only=True).fillna(0.0)
    sc = synthetic[numeric_cols].corr(numeric_only=True).fillna(0.0)
    diff = np.abs(rc.to_numpy() - sc.to_numpy())
    return _clamp01(1.0 - float(np.mean(diff)) / 2.0)


def _privacy_score(real: pd.DataFrame, synthetic: pd.DataFrame) -> tuple[float, dict]:
    common = [c for c in real.columns if c in synthetic.columns]
    exact_rate = _exact_duplicate_rate(real[common], synthetic[common])
    nn_score = _nearest_neighbor_score(real[common], synthetic[common])
    score = 0.6 * (1.0 - exact_rate) + 0.4 * nn_score
    return _clamp01(score), {
        "exact_duplicate_rate": exact_rate,
        "nearest_neighbor_score": nn_score,
    }


def _membership_attack_score(
    train: pd.DataFrame,
    holdout: pd.DataFrame,
    synthetic: pd.DataFrame,
) -> float | None:
    numeric_cols = [
        c
        for c in train.columns
        if c in holdout
        and c in synthetic
        and pd.api.types.is_numeric_dtype(train[c])
        and pd.api.types.is_numeric_dtype(holdout[c])
        and pd.api.types.is_numeric_dtype(synthetic[c])
    ]
    if not numeric_cols or len(train) < 5 or len(holdout) < 5 or len(synthetic) < 5:
        return None

    train_sample = train[numeric_cols].sample(min(len(train), 1000), random_state=31)
    hold_sample = holdout[numeric_cols].sample(min(len(holdout), 1000), random_state=32)
    syn_sample = synthetic[numeric_cols].sample(min(len(synthetic), 1000), random_state=33)
    combined = pd.concat([train_sample, hold_sample, syn_sample], ignore_index=True)
    combined = combined.apply(pd.to_numeric, errors="coerce")
    combined = combined.fillna(combined.median(numeric_only=True)).fillna(0.0)
    values = combined.to_numpy(dtype=float)
    scale = values.std(axis=0)
    scale[scale == 0] = 1.0
    scaled = (values - values.mean(axis=0)) / scale
    n_train = len(train_sample)
    n_hold = len(hold_sample)
    train_x = scaled[:n_train]
    hold_x = scaled[n_train:n_train + n_hold]
    syn_x = scaled[n_train + n_hold:]
    d_train = _min_pairwise_distances(syn_x, train_x)
    d_hold = _min_pairwise_distances(syn_x, hold_x)
    attack_rate = float((d_train < d_hold).mean())
    excess = max(0.0, attack_rate - 0.5)
    return _clamp01(1.0 - 2.0 * excess)


def _exact_duplicate_rate(real: pd.DataFrame, synthetic: pd.DataFrame) -> float:
    real_rows = set(map(tuple, real.astype("object").fillna("__NA__").to_numpy()))
    if not real_rows or synthetic.empty:
        return 0.0
    synthetic_rows = map(tuple, synthetic.astype("object").fillna("__NA__").to_numpy())
    hits = sum(1 for row in synthetic_rows if row in real_rows)
    return hits / max(len(synthetic), 1)


def _nearest_neighbor_score(real: pd.DataFrame, synthetic: pd.DataFrame) -> float:
    numeric_cols = [
        c
        for c in real.columns
        if pd.api.types.is_numeric_dtype(real[c])
        and c in synthetic
        and pd.api.types.is_numeric_dtype(synthetic[c])
    ]
    if not numeric_cols or len(real) < 3 or len(synthetic) < 3:
        return 1.0

    sample_real = real[numeric_cols].sample(
        min(len(real), 1000), random_state=17
    )
    sample_syn = synthetic[numeric_cols].sample(
        min(len(synthetic), 1000), random_state=19
    )
    combined = pd.concat([sample_real, sample_syn], ignore_index=True)
    combined = combined.apply(pd.to_numeric, errors="coerce")
    combined = combined.fillna(combined.median(numeric_only=True)).fillna(0.0)
    values = combined.to_numpy(dtype=float)
    scale = values.std(axis=0)
    scale[scale == 0] = 1.0
    scaled = (values - values.mean(axis=0)) / scale
    r = scaled[: len(sample_real)]
    s = scaled[len(sample_real) :]
    nearest = _min_pairwise_distances(s, r)
    real_nearest = float(np.median(_within_set_nearest_distances(r)))
    if not np.isfinite(real_nearest) or real_nearest <= 0:
        return 1.0
    ratio = float(np.median(nearest) / real_nearest)
    return _clamp01(min(ratio, 1.5) / 1.5)


def _min_pairwise_distances(left: np.ndarray, right: np.ndarray, *, batch_size: int = 256) -> np.ndarray:
    if len(left) == 0 or len(right) == 0:
        return np.array([], dtype=float)
    output = np.empty(len(left), dtype=float)
    right_norm = (right * right).sum(axis=1)
    for start in range(0, len(left), batch_size):
        batch = left[start:start + batch_size]
        squared = (batch * batch).sum(axis=1)[:, None] + right_norm[None, :] - 2.0 * (batch @ right.T)
        output[start:start + len(batch)] = np.sqrt(np.maximum(squared.min(axis=1), 0.0))
    return output


def _within_set_nearest_distances(values: np.ndarray, *, batch_size: int = 256) -> np.ndarray:
    if len(values) < 2:
        return np.full(len(values), np.inf)
    output = np.empty(len(values), dtype=float)
    norms = (values * values).sum(axis=1)
    for start in range(0, len(values), batch_size):
        batch = values[start:start + batch_size]
        squared = (batch * batch).sum(axis=1)[:, None] + norms[None, :] - 2.0 * (batch @ values.T)
        rows = np.arange(len(batch))
        squared[rows, start + rows] = np.inf
        output[start:start + len(batch)] = np.sqrt(np.maximum(squared.min(axis=1), 0.0))
    return output


def _missingness_score(real: pd.DataFrame, synthetic: pd.DataFrame) -> float:
    common = [c for c in real.columns if c in synthetic.columns]
    if not common:
        return 1.0
    diffs = [abs(float(real[c].isna().mean()) - float(synthetic[c].isna().mean())) for c in common]
    return _clamp01(1.0 - float(np.mean(diffs)))


def _range_score(real: pd.DataFrame, synthetic: pd.DataFrame) -> float:
    numeric_cols = [
        c
        for c in real.columns
        if c in synthetic
        and pd.api.types.is_numeric_dtype(real[c])
        and pd.api.types.is_numeric_dtype(synthetic[c])
    ]
    if not numeric_cols:
        return 1.0
    total = 0
    bad = 0
    for col in numeric_cols:
        r = pd.to_numeric(real[col], errors="coerce").dropna()
        s = pd.to_numeric(synthetic[col], errors="coerce").dropna()
        if r.empty or s.empty:
            continue
        low = float(r.min())
        high = float(r.max())
        total += len(s)
        bad += int(((s < low) | (s > high)).sum())
    if total == 0:
        return 1.0
    return _clamp01(1.0 - bad / total)


def _utility_score(
    train_real: pd.DataFrame,
    test_real: pd.DataFrame,
    synthetic: pd.DataFrame,
    target_col: str | None,
) -> float | None:
    if not target_col or target_col not in synthetic or target_col not in test_real:
        return None
    common = [c for c in train_real.columns if c in test_real.columns and c in synthetic.columns]
    if target_col not in common or len(common) < 2 or len(test_real) < 10 or len(synthetic) < 10:
        return None
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.metrics import accuracy_score, f1_score, r2_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except Exception:
        return None

    features = [c for c in common if c != target_col]
    y_syn = synthetic[target_col]
    y_test = test_real[target_col]
    task = "regression" if pd.api.types.is_numeric_dtype(y_test) and y_test.nunique() > 10 else "classification"
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(synthetic[c])]
    categorical = [c for c in features if c not in numeric]
    transformer = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ],
        remainder="drop",
    )
    model = RandomForestRegressor(n_estimators=80, random_state=23) if task == "regression" else RandomForestClassifier(n_estimators=80, random_state=23)
    pipeline = Pipeline([("prep", transformer), ("model", model)])
    try:
        pipeline.fit(synthetic[features], y_syn)
        pred = pipeline.predict(test_real[features])
        if task == "regression":
            return _clamp01((float(r2_score(y_test, pred)) + 1.0) / 2.0)
        if y_test.nunique() <= 1:
            return None
        return _clamp01(0.5 * accuracy_score(y_test, pred) + 0.5 * f1_score(y_test, pred, average="weighted"))
    except Exception:
        return None


def _detectability_score(real: pd.DataFrame, synthetic: pd.DataFrame) -> float | None:
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except Exception:
        return None

    common = [c for c in real.columns if c in synthetic.columns]
    if len(real) < 20 or len(synthetic) < 20 or not common:
        return None
    r = real[common].sample(min(len(real), len(synthetic)), random_state=7)
    s = synthetic[common].sample(len(r), random_state=8)
    x = pd.concat([r, s], ignore_index=True)
    y = np.array([0] * len(r) + [1] * len(s))
    numeric = [c for c in common if pd.api.types.is_numeric_dtype(x[c])]
    categorical = [c for c in common if c not in numeric]
    if len(set(y)) < 2:
        return None
    transformer = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ],
        remainder="drop",
    )
    model = Pipeline(
        steps=[
            ("prep", transformer),
            ("clf", RandomForestClassifier(n_estimators=80, random_state=13)),
        ]
    )
    try:
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.35, random_state=11, stratify=y
        )
        model.fit(x_train, y_train)
        acc = accuracy_score(y_test, model.predict(x_test))
    except Exception:
        return None
    return _clamp01(1.0 - max(0.0, float(acc) - 0.5) * 2.0)


def _clamp01(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))
