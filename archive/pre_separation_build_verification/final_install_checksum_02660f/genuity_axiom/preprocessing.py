"""Explicit, privacy-aware preparation for messy tabular inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

import numpy as np
import pandas as pd

from .unstructured import TextSafetyReport, UnstructuredPrivacyProcessor


@dataclass
class TabularPreparationReport:
    nested_values_normalized: dict[str, int]
    infinite_values_replaced: dict[str, int]
    text_safety: TextSafetyReport | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nested_values_normalized": self.nested_values_normalized,
            "infinite_values_replaced": self.infinite_values_replaced,
            "text_safety": None if self.text_safety is None else self.text_safety.to_dict(),
            "warnings": self.warnings,
        }


def prepare_messy_table(
    df: pd.DataFrame,
    *,
    privacy_processor: UnstructuredPrivacyProcessor | None = None,
    replace_infinity: bool = True,
) -> tuple[pd.DataFrame, TabularPreparationReport]:
    """Convert nested cells to stable JSON after recursive privacy transformation."""

    if df.columns.duplicated().any():
        duplicates = sorted(set(df.columns[df.columns.duplicated()].astype(str)))
        raise ValueError("duplicate column names must be resolved explicitly: " + ", ".join(duplicates))
    processor = privacy_processor or UnstructuredPrivacyProcessor()
    output = df.copy()
    nested_counts: dict[str, int] = {}
    transformed_reports: list[TextSafetyReport] = []
    for col in output.columns:
        count = 0

        def normalize(value: Any) -> Any:
            nonlocal count
            if isinstance(value, (dict, list, tuple, set)):
                count += 1
                safe_value, report = processor.transform(value)
                transformed_reports.append(report)
                if isinstance(safe_value, set):
                    safe_value = sorted(safe_value, key=str)
                return json.dumps(safe_value, sort_keys=True, separators=(",", ":"), default=str)
            return value

        output[col] = output[col].map(normalize)
        if count:
            nested_counts[str(col)] = count
    infinite: dict[str, int] = {}
    if replace_infinity:
        for col in output.select_dtypes(include=[np.number]).columns:
            values = pd.to_numeric(output[col], errors="coerce")
            count = int(np.isinf(values).sum())
            if count:
                output[col] = values.replace([np.inf, -np.inf], np.nan)
                infinite[str(col)] = count
    text_report = None
    if transformed_reports:
        labels = set().union(*(report.replacements_by_type for report in transformed_reports))
        text_report = TextSafetyReport(
            {label: sum(r.replacements_by_type.get(label, 0) for r in transformed_reports) for label in labels},
            {label: sum(r.residual_matches.get(label, 0) for r in transformed_reports) for label in labels},
            warnings=sorted({warning for report in transformed_reports for warning in report.warnings}),
        )
    warnings = ["Nested structures were serialized rather than relationally modeled; use explicit table/asset schemas when internal relationships matter."] if nested_counts else []
    return output, TabularPreparationReport(nested_counts, infinite, text_report, warnings)


def find_nested_columns(df: pd.DataFrame, *, sample_size: int = 500) -> list[str]:
    nested: list[str] = []
    for col in df.columns:
        sample = df[col].dropna().head(sample_size)
        if sample.map(lambda value: isinstance(value, (dict, list, tuple, set))).any():
            nested.append(str(col))
    return nested
