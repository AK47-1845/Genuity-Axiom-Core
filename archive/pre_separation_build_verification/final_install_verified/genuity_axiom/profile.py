"""Engineering-specific dataset profiling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import warnings

import numpy as np
import pandas as pd


DOMAIN_KEYWORDS = {
    "aerospace": {
        "aero",
        "wing",
        "wingspan",
        "altitude",
        "mach",
        "turbine",
        "airframe",
        "fuselage",
        "thrust",
    },
    "automotive": {
        "rpm",
        "torque",
        "emission",
        "nox",
        "co2",
        "powertrain",
        "engine",
        "vehicle",
        "ecu",
    },
    "manufacturing": {
        "machine",
        "spindle",
        "tool",
        "cycle",
        "defect",
        "line",
        "station",
        "work_order",
    },
    "materials": {
        "tensile",
        "yield",
        "hardness",
        "modulus",
        "density",
        "fatigue",
        "elongation",
        "impact",
    },
    "energy_scada": {
        "scada",
        "reactor",
        "coolant",
        "pressure",
        "flow",
        "alarm",
        "inlet",
        "outlet",
        "thermal",
    },
    "maintenance": {
        "bearing",
        "vibration",
        "fault",
        "maintenance",
        "downtime",
        "severity",
        "sensor",
    },
}


@dataclass
class ColumnProfile:
    name: str
    kind: str
    dtype: str
    missing_rate: float
    unique_count: int
    min_value: Any = None
    max_value: Any = None
    mean: float | None = None
    std: float | None = None
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class DatasetProfile:
    n_rows: int
    n_cols: int
    modality: str
    engineering_domain: str
    column_profiles: list[ColumnProfile]
    numeric_columns: list[str]
    categorical_columns: list[str]
    text_columns: list[str]
    datetime_columns: list[str]
    recommended_generators: list[str]
    risk_flags: list[str] = field(default_factory=list)
    semantic_roles: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "modality": self.modality,
            "engineering_domain": self.engineering_domain,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "text_columns": self.text_columns,
            "datetime_columns": self.datetime_columns,
            "recommended_generators": self.recommended_generators,
            "risk_flags": self.risk_flags,
            "semantic_roles": self.semantic_roles,
            "columns": [profile.__dict__ for profile in self.column_profiles],
        }


class EngineeringProfiler:
    """Profiles engineering datasets and selects a conservative fallback ladder."""

    def profile(
        self,
        df: pd.DataFrame,
        *,
        time_col: str | None = None,
        entity_col: str | None = None,
        target_col: str | None = None,
    ) -> DatasetProfile:
        if df.empty:
            raise ValueError("Cannot profile an empty dataframe")

        columns = [self._profile_column(df[col]) for col in df.columns]
        numeric = [c.name for c in columns if c.kind in {"numeric", "integer", "binary"}]
        categorical = [c.name for c in columns if c.kind == "categorical"]
        text = [c.name for c in columns if c.kind == "text"]
        datetimes = [c.name for c in columns if c.kind == "datetime"]

        if time_col and time_col in df.columns and time_col not in datetimes:
            datetimes.append(time_col)

        modality = self._detect_modality(df, text, datetimes, time_col, entity_col)
        domain = self._detect_domain(df.columns)
        risks = self._detect_dataset_risks(df, columns, target_col)
        generators = self._recommend_generators(
            df, modality=modality, numeric=numeric, categorical=categorical, text=text
        )
        roles = self._infer_semantic_roles(
            df,
            time_col=time_col,
            entity_col=entity_col,
            target_col=target_col,
        )

        return DatasetProfile(
            n_rows=len(df),
            n_cols=len(df.columns),
            modality=modality,
            engineering_domain=domain,
            column_profiles=columns,
            numeric_columns=numeric,
            categorical_columns=categorical,
            text_columns=text,
            datetime_columns=datetimes,
            recommended_generators=generators,
            risk_flags=risks,
            semantic_roles=roles,
        )

    def _profile_column(self, series: pd.Series) -> ColumnProfile:
        non_null = series.dropna()
        dtype = str(series.dtype)
        unique_count = int(non_null.nunique(dropna=True))
        missing_rate = float(series.isna().mean())
        kind = self._infer_kind(series)
        flags: list[str] = []

        min_value = max_value = mean = std = None
        if kind in {"numeric", "integer", "binary"} and len(non_null):
            numeric = pd.to_numeric(non_null, errors="coerce").dropna()
            if len(numeric):
                min_value = float(numeric.min())
                max_value = float(numeric.max())
                mean = float(numeric.mean())
                std = float(numeric.std(ddof=0))
                if std == 0:
                    flags.append("constant")
                if _has_heavy_tail(numeric):
                    flags.append("heavy_tail")
                if (numeric < 0).any() and _looks_physical_positive(series.name):
                    flags.append("negative_physical_values")

        if missing_rate > 0.4:
            flags.append("high_missingness")
        if unique_count == len(non_null) and kind not in {"numeric", "integer"}:
            flags.append("possible_identifier")

        return ColumnProfile(
            name=str(series.name),
            kind=kind,
            dtype=dtype,
            missing_rate=missing_rate,
            unique_count=unique_count,
            min_value=min_value,
            max_value=max_value,
            mean=mean,
            std=std,
            risk_flags=flags,
        )

    def _infer_kind(self, series: pd.Series) -> str:
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        if pd.api.types.is_bool_dtype(series):
            return "binary"
        if pd.api.types.is_integer_dtype(series):
            unique = series.dropna().nunique()
            if unique <= 2:
                return "binary"
            return "integer"
        if pd.api.types.is_numeric_dtype(series):
            return "numeric"

        sample = series.dropna().astype(str).head(250)
        if sample.empty:
            return "categorical"
        avg_words = float(sample.map(lambda x: len(x.split())).mean())
        cardinality_ratio = float(series.nunique(dropna=True)) / max(len(series.dropna()), 1)
        if avg_words >= 5 and cardinality_ratio > 0.25:
            return "text"
        if _can_parse_datetime(sample):
            return "datetime"
        return "categorical"

    def _detect_modality(
        self,
        df: pd.DataFrame,
        text_cols: list[str],
        datetime_cols: list[str],
        time_col: str | None,
        entity_col: str | None,
    ) -> str:
        if text_cols and len(text_cols) >= max(1, len(df.columns) // 3):
            return "textual"
        if time_col or (datetime_cols and entity_col):
            return "time_series"
        if len([c for c in df.columns if str(c).lower().endswith("_id")]) >= 2:
            return "relational_table"
        return "tabular"

    def _detect_domain(self, columns: list[str]) -> str:
        text = " ".join(str(c).lower() for c in columns)
        scores = {
            domain: sum(1 for keyword in keywords if keyword in text)
            for domain, keywords in DOMAIN_KEYWORDS.items()
        }
        domain, score = max(scores.items(), key=lambda item: item[1])
        return domain if score > 0 else "generic_engineering"

    def _detect_dataset_risks(
        self, df: pd.DataFrame, columns: list[ColumnProfile], target_col: str | None
    ) -> list[str]:
        risks: list[str] = []
        if len(df) < 200:
            risks.append("small_sample_overfit_risk")
        if len(df.columns) > max(len(df) // 2, 50):
            risks.append("wide_table_risk")
        if any("high_missingness" in c.risk_flags for c in columns):
            risks.append("high_missingness")
        if any(c.kind == "categorical" and c.unique_count > 50 for c in columns):
            risks.append("high_cardinality_categoricals")
        if target_col and target_col in df:
            counts = df[target_col].value_counts(normalize=True, dropna=True)
            if len(counts) > 1 and counts.iloc[0] >= 0.85:
                risks.append("target_imbalance")
        return risks

    def _infer_semantic_roles(
        self,
        df: pd.DataFrame,
        *,
        time_col: str | None,
        entity_col: str | None,
        target_col: str | None,
    ) -> dict[str, str]:
        roles: dict[str, str] = {}
        for col in df.columns:
            lower = str(col).lower()
            role = "feature"
            if col == target_col:
                role = "target"
            elif col == time_col or any(token in lower for token in ("timestamp", "datetime", "date", "time")):
                role = "time"
            elif col == entity_col or lower.endswith("_id") or lower in {"id", "uuid", "serial"}:
                role = "entity_or_identifier"
            elif any(token in lower for token in ("material", "alloy", "grade", "composite")):
                role = "material_descriptor"
            elif any(token in lower for token in ("length", "width", "thickness", "wingspan", "diameter", "geometry", "shape")):
                role = "geometry"
            elif any(token in lower for token in ("pressure", "temperature", "flow", "load", "rpm", "torque", "altitude", "mach")):
                role = "operating_condition"
            elif any(token in lower for token in ("sensor", "vibration", "accel", "current", "voltage", "signal")):
                role = "sensor_measurement"
            elif any(token in lower for token in ("strength", "stress", "strain", "durability", "life", "efficiency", "damping", "nox", "co2")):
                role = "response_output"
            elif any(token in lower for token in ("optimizer", "algorithm", "setting", "control", "command")):
                role = "control_input"
            roles[str(col)] = role
        return roles

    def _recommend_generators(
        self,
        df: pd.DataFrame,
        *,
        modality: str,
        numeric: list[str],
        categorical: list[str],
        text: list[str],
    ) -> list[str]:
        if modality == "textual":
            return ["stratified_bootstrap", "bootstrap"]
        if modality == "time_series":
            return ["stratified_bootstrap", "gaussian_copula", "bootstrap"]
        if len(df) < 300:
            return ["gaussian_copula", "bootstrap"]
        if len(numeric) >= 2:
            return ["gmm", "kde", "gaussian_copula", "stratified_bootstrap", "bootstrap"]
        if categorical or text:
            return ["stratified_bootstrap", "bootstrap"]
        return ["gaussian_copula", "bootstrap"]


def _can_parse_datetime(sample: pd.Series) -> bool:
    text = sample.astype(str)
    has_date_shape = text.str.contains(
        r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        regex=True,
    ).mean()
    if has_date_shape < 0.8:
        return False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(sample, errors="coerce")
    return bool(parsed.notna().mean() > 0.8)


def _has_heavy_tail(series: pd.Series) -> bool:
    if len(series) < 20:
        return False
    std = series.std(ddof=0)
    if not std:
        return False
    z = (series - series.mean()) / std
    return bool(np.nanpercentile(np.abs(z), 95) > 3.0)


def _looks_physical_positive(name: str) -> bool:
    lowered = str(name).lower()
    keywords = (
        "strength",
        "pressure",
        "density",
        "hardness",
        "rpm",
        "torque",
        "flow",
        "mass",
        "weight",
        "temperature_k",
        "modulus",
        "life",
        "duration",
        "thickness",
        "length",
    )
    return any(keyword in lowered for keyword in keywords)
