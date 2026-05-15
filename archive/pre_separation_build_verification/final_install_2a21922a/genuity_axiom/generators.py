"""Fallback synthetic generators.

These generators are deliberately conservative. They are meant to be the
always-available safety ladder beneath heavier neural models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import pandas as pd


@dataclass
class GeneratorAttempt:
    name: str
    status: str
    message: str = ""


@dataclass
class GeneratorOutput:
    data: pd.DataFrame
    generator_name: str
    attempts: list[GeneratorAttempt] = field(default_factory=list)
    candidate_scores: dict[str, float] = field(default_factory=dict)


class Generator(Protocol):
    name: str

    def fit(self, df: pd.DataFrame) -> "Generator":
        ...

    def generate(self, n_samples: int, conditions: dict | None = None) -> pd.DataFrame:
        ...


class BaseGenerator:
    name = "base"

    def __init__(self, random_state: int | None = None) -> None:
        self.random_state = random_state
        self.rng = np.random.default_rng(random_state)
        self.df: pd.DataFrame | None = None
        self.numeric_cols: list[str] = []
        self.categorical_cols: list[str] = []
        self.datetime_cols: list[str] = []
        self.integer_cols: list[str] = []
        self.bounds: dict[str, tuple[float, float]] = {}

    def fit(self, df: pd.DataFrame) -> "BaseGenerator":
        if df.empty:
            raise ValueError("Cannot fit generator on an empty dataframe")
        self.df = df.reset_index(drop=True).copy()
        self.numeric_cols = [
            c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
        ]
        self.integer_cols = [
            c for c in self.numeric_cols if pd.api.types.is_integer_dtype(df[c])
        ]
        self.datetime_cols = [
            c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])
        ]
        self.categorical_cols = [
            c
            for c in df.columns
            if c not in self.numeric_cols and c not in self.datetime_cols
        ]
        self.bounds = {
            c: (float(df[c].min()), float(df[c].max()))
            for c in self.numeric_cols
            if df[c].notna().any()
        }
        return self

    def _source_for_conditions(self, conditions: dict | None) -> pd.DataFrame:
        assert self.df is not None
        source = self.df
        if not conditions:
            return source
        for column, expected in conditions.items():
            if column not in source:
                raise ValueError(f"condition references missing column: {column}")
            if isinstance(expected, dict):
                mask = pd.Series(True, index=source.index)
                if "ge" in expected:
                    mask &= source[column] >= expected["ge"]
                if "gt" in expected:
                    mask &= source[column] > expected["gt"]
                if "le" in expected:
                    mask &= source[column] <= expected["le"]
                if "lt" in expected:
                    mask &= source[column] < expected["lt"]
                if "in" in expected:
                    mask &= source[column].isin(expected["in"])
                source = source[mask]
            else:
                source = source[source[column] == expected]
        if source.empty:
            raise ValueError("no source rows support the requested conditions; use an approved rare-event or simulator workflow")
        return source

    def _apply_requested_conditions(self, df: pd.DataFrame, conditions: dict | None) -> pd.DataFrame:
        if not conditions:
            return df
        output = df.copy()
        for column, expected in conditions.items():
            if column not in output:
                raise ValueError(f"condition references missing generated column: {column}")
            if not isinstance(expected, dict):
                output[column] = expected
                continue
            if "in" in expected:
                allowed = list(expected["in"])
                if not allowed:
                    raise ValueError(f"condition {column}.in cannot be empty")
                output[column] = self.rng.choice(allowed, size=len(output))
            numeric = pd.to_numeric(output[column], errors="coerce")
            if "ge" in expected:
                numeric = numeric.clip(lower=expected["ge"])
            if "gt" in expected:
                numeric = numeric.clip(lower=np.nextafter(float(expected["gt"]), np.inf))
            if "le" in expected:
                numeric = numeric.clip(upper=expected["le"])
            if "lt" in expected:
                numeric = numeric.clip(upper=np.nextafter(float(expected["lt"]), -np.inf))
            if any(key in expected for key in ("ge", "gt", "le", "lt")):
                output[column] = numeric
        return output

    def _finalize(self, df: pd.DataFrame) -> pd.DataFrame:
        for col, (low, high) in self.bounds.items():
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce").clip(low, high)
        for col in self.integer_cols:
            if col in df:
                df[col] = df[col].round().astype("Int64")
        return df


class BootstrapGenerator(BaseGenerator):
    name = "bootstrap"

    def generate(self, n_samples: int, conditions: dict | None = None) -> pd.DataFrame:
        source = self._source_for_conditions(conditions)
        sampled = source.sample(n=n_samples, replace=True, random_state=self.random_state)
        sampled = sampled.reset_index(drop=True).copy()

        for col in self.numeric_cols:
            if col not in sampled:
                continue
            std = float(source[col].std(ddof=0) or 0.0)
            if std > 0:
                sampled[col] = sampled[col].astype(float) + self.rng.normal(
                    0.0, std * 0.015, size=n_samples
                )
        return self._finalize(self._apply_requested_conditions(sampled, conditions))


class StratifiedBootstrapGenerator(BootstrapGenerator):
    name = "stratified_bootstrap"

    def generate(self, n_samples: int, conditions: dict | None = None) -> pd.DataFrame:
        source = self._source_for_conditions(conditions)
        strat_col = _choose_stratification_column(source)
        if not strat_col:
            return super().generate(n_samples, conditions)

        counts = source[strat_col].value_counts(normalize=True, dropna=False)
        parts: list[pd.DataFrame] = []
        remaining = n_samples
        for idx, (value, ratio) in enumerate(counts.items()):
            take = int(round(n_samples * float(ratio)))
            if idx == len(counts) - 1:
                take = remaining
            remaining -= take
            bucket = source[source[strat_col].isna()] if pd.isna(value) else source[source[strat_col] == value]
            if len(bucket) and take > 0:
                parts.append(
                    bucket.sample(n=take, replace=True, random_state=self.random_state)
                )
        if not parts:
            return super().generate(n_samples, conditions)

        sampled = pd.concat(parts, ignore_index=True).sample(
            frac=1.0, random_state=self.random_state
        )
        sampled = sampled.reset_index(drop=True).copy()
        for col in self.numeric_cols:
            std = float(source[col].std(ddof=0) or 0.0)
            if std > 0:
                sampled[col] = sampled[col].astype(float) + self.rng.normal(
                    0.0, std * 0.01, size=len(sampled)
                )
        return self._finalize(self._apply_requested_conditions(sampled.head(n_samples), conditions))


class GaussianCopulaLiteGenerator(BaseGenerator):
    name = "gaussian_copula"

    def fit(self, df: pd.DataFrame) -> "GaussianCopulaLiteGenerator":
        super().fit(df)
        if not self.numeric_cols:
            raise ValueError("Gaussian copula requires numeric columns")
        numeric = df[self.numeric_cols].apply(pd.to_numeric, errors="coerce")
        self.means = numeric.mean().fillna(0.0).to_numpy(dtype=float)
        cov = numeric.cov().fillna(0.0).to_numpy(dtype=float)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])
        cov = _stabilize_covariance(cov)
        self.cov = cov
        self.category_distributions = {
            c: df[c].value_counts(normalize=True, dropna=False)
            for c in self.categorical_cols
        }
        return self

    def generate(self, n_samples: int, conditions: dict | None = None) -> pd.DataFrame:
        assert self.df is not None
        if conditions:
            conditioned = self._source_for_conditions(conditions)
            if len(conditioned) >= max(10, len(self.numeric_cols) + 2):
                return GaussianCopulaLiteGenerator(self.random_state).fit(
                    conditioned
                ).generate(n_samples)

        values = self.rng.multivariate_normal(self.means, self.cov, size=n_samples)
        out = pd.DataFrame(values, columns=self.numeric_cols)

        for col, dist in self.category_distributions.items():
            labels = dist.index.to_list()
            probs = dist.to_numpy(dtype=float)
            probs = probs / probs.sum()
            out[col] = self.rng.choice(labels, size=n_samples, p=probs)

        for col in self.datetime_cols:
            source = self.df[col].dropna()
            out[col] = self.rng.choice(source, size=n_samples) if len(source) else pd.NaT

        return self._finalize(self._apply_requested_conditions(out[list(self.df.columns)], conditions))


class KDEGenerator(BaseGenerator):
    name = "kde"

    def fit(self, df: pd.DataFrame) -> "KDEGenerator":
        super().fit(df)
        if not self.numeric_cols:
            raise ValueError("KDE requires numeric columns")
        try:
            from sklearn.neighbors import KernelDensity
            from sklearn.preprocessing import StandardScaler
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for KDE") from exc

        self.scaler = StandardScaler()
        numeric = df[self.numeric_cols].apply(pd.to_numeric, errors="coerce")
        numeric = numeric.fillna(numeric.median(numeric_only=True)).fillna(0.0)
        matrix = self.scaler.fit_transform(numeric)
        bandwidth = max(0.15, matrix.shape[0] ** (-1.0 / (matrix.shape[1] + 4)))
        self.model = KernelDensity(kernel="gaussian", bandwidth=bandwidth)
        self.model.fit(matrix)
        self.category_distributions = {
            c: df[c].value_counts(normalize=True, dropna=False)
            for c in self.categorical_cols
        }
        return self

    def generate(self, n_samples: int, conditions: dict | None = None) -> pd.DataFrame:
        if conditions:
            conditioned = self._source_for_conditions(conditions)
            if len(conditioned) >= max(20, len(self.numeric_cols) * 5):
                return KDEGenerator(self.random_state).fit(conditioned).generate(n_samples)

        values = self.model.sample(n_samples, random_state=self.random_state)
        values = self.scaler.inverse_transform(values)
        out = pd.DataFrame(values, columns=self.numeric_cols)
        for col, dist in self.category_distributions.items():
            labels = dist.index.to_list()
            probs = dist.to_numpy(dtype=float)
            out[col] = self.rng.choice(labels, size=n_samples, p=probs / probs.sum())
        assert self.df is not None
        for col in self.datetime_cols:
            source = self.df[col].dropna()
            out[col] = self.rng.choice(source, size=n_samples) if len(source) else pd.NaT
        return self._finalize(self._apply_requested_conditions(out[list(self.df.columns)], conditions))


class GMMGenerator(BaseGenerator):
    name = "gmm"

    def fit(self, df: pd.DataFrame) -> "GMMGenerator":
        super().fit(df)
        if not self.numeric_cols:
            raise ValueError("GMM requires numeric columns")
        try:
            from sklearn.mixture import GaussianMixture
            from sklearn.preprocessing import StandardScaler
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for GMM") from exc

        numeric = df[self.numeric_cols].apply(pd.to_numeric, errors="coerce")
        numeric = numeric.fillna(numeric.median(numeric_only=True)).fillna(0.0)
        self.scaler = StandardScaler()
        matrix = self.scaler.fit_transform(numeric)
        n_components = min(5, max(1, len(df) // 100), len(df) - 1)
        self.model = GaussianMixture(
            n_components=n_components,
            covariance_type="full",
            random_state=self.random_state,
            reg_covar=1e-5,
        )
        self.model.fit(matrix)
        self.category_distributions = {
            c: df[c].value_counts(normalize=True, dropna=False)
            for c in self.categorical_cols
        }
        return self

    def generate(self, n_samples: int, conditions: dict | None = None) -> pd.DataFrame:
        if conditions:
            conditioned = self._source_for_conditions(conditions)
            if len(conditioned) >= max(50, len(self.numeric_cols) * 8):
                return GMMGenerator(self.random_state).fit(conditioned).generate(n_samples)

        values, _ = self.model.sample(n_samples)
        values = self.scaler.inverse_transform(values)
        out = pd.DataFrame(values, columns=self.numeric_cols)
        for col, dist in self.category_distributions.items():
            labels = dist.index.to_list()
            probs = dist.to_numpy(dtype=float)
            out[col] = self.rng.choice(labels, size=n_samples, p=probs / probs.sum())
        assert self.df is not None
        for col in self.datetime_cols:
            source = self.df[col].dropna()
            out[col] = self.rng.choice(source, size=n_samples) if len(source) else pd.NaT
        return self._finalize(self._apply_requested_conditions(out[list(self.df.columns)], conditions))


class FallbackSynthesizer:
    """Tries generators in order and never leaves the caller without a result."""

    registry = {
        "gmm": GMMGenerator,
        "kde": KDEGenerator,
        "gaussian_copula": GaussianCopulaLiteGenerator,
        "stratified_bootstrap": StratifiedBootstrapGenerator,
        "bootstrap": BootstrapGenerator,
    }

    def __init__(
        self,
        fallback_order: list[str] | None = None,
        random_state: int | None = None,
    ) -> None:
        self.fallback_order = fallback_order or [
            "gmm",
            "kde",
            "gaussian_copula",
            "stratified_bootstrap",
            "bootstrap",
        ]
        if "bootstrap" not in self.fallback_order:
            self.fallback_order.append("bootstrap")
        self.random_state = random_state

    def synthesize(
        self,
        df: pd.DataFrame,
        n_samples: int,
        *,
        conditions: dict | None = None,
    ) -> GeneratorOutput:
        attempts: list[GeneratorAttempt] = []
        for name in self.fallback_order:
            generator_cls = self.registry.get(name)
            if generator_cls is None:
                attempts.append(GeneratorAttempt(name, "skipped", "unknown generator"))
                continue
            try:
                generator = generator_cls(random_state=self.random_state).fit(df)
                synthetic = generator.generate(n_samples, conditions=conditions)
                attempts.append(GeneratorAttempt(name, "success"))
                return GeneratorOutput(
                    data=synthetic,
                    generator_name=name,
                    attempts=attempts,
                )
            except Exception as exc:
                attempts.append(GeneratorAttempt(name, "failed", str(exc)))

        raise RuntimeError("All fallback generators failed, including bootstrap")

    def synthesize_best(
        self,
        df: pd.DataFrame,
        n_samples: int,
        *,
        reference_df: pd.DataFrame,
        evaluator: object,
        constraints: object | None = None,
        target_col: str | None = None,
        conditions: dict | None = None,
        max_candidates: int = 5,
    ) -> GeneratorOutput:
        attempts: list[GeneratorAttempt] = []
        candidate_scores: dict[str, float] = {}
        best_name: str | None = None
        best_data: pd.DataFrame | None = None
        best_score = -1.0
        tried = 0

        for name in self.fallback_order:
            generator_cls = self.registry.get(name)
            if generator_cls is None:
                attempts.append(GeneratorAttempt(name, "skipped", "unknown generator"))
                continue
            if tried >= max_candidates and best_data is not None:
                break
            tried += 1
            try:
                generator = generator_cls(random_state=self.random_state).fit(df)
                synthetic = generator.generate(n_samples, conditions=conditions)
                score = evaluator.evaluate(
                    reference_df,
                    synthetic,
                    constraints=constraints,
                    train_data=df,
                    target_col=target_col,
                ).overall_score
                candidate_scores[name] = float(score)
                attempts.append(GeneratorAttempt(name, "success", f"score={score:.4f}"))
                if score > best_score:
                    best_name = name
                    best_data = synthetic
                    best_score = float(score)
            except Exception as exc:
                attempts.append(GeneratorAttempt(name, "failed", str(exc)))

        if best_data is not None and best_name is not None:
            return GeneratorOutput(
                data=best_data,
                generator_name=best_name,
                attempts=attempts,
                candidate_scores=candidate_scores,
            )
        return self.synthesize(df, n_samples, conditions=conditions)


def _choose_stratification_column(df: pd.DataFrame) -> str | None:
    candidates: list[tuple[int, str]] = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        unique = df[col].nunique(dropna=False)
        if 2 <= unique <= min(25, max(2, len(df) // 3)):
            candidates.append((unique, col))
    if not candidates:
        return None
    return sorted(candidates)[0][1]


def _stabilize_covariance(cov: np.ndarray) -> np.ndarray:
    cov = np.asarray(cov, dtype=float)
    if cov.ndim == 0:
        cov = np.array([[float(cov)]])
    if cov.shape == (1, 1):
        cov[0, 0] = max(float(cov[0, 0]), 1e-6)
        return cov
    cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
    cov = (cov + cov.T) / 2.0
    cov += np.eye(cov.shape[0]) * 1e-6
    return cov
