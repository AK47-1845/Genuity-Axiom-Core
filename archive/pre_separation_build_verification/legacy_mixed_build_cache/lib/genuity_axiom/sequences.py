"""Deterministic sequence baselines and temporal integrity checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SequenceReport:
    rows: int
    entities: int
    monotonic_entities: int
    duplicate_timestamps: int
    block_length: int
    invalid_timestamps: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.invalid_timestamps == 0 and self.monotonic_entities == self.entities and self.duplicate_timestamps == 0

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["passed"] = self.passed
        return payload


class TimeSeriesBlockSynthesizer:
    """Always-available block bootstrap preserving local temporal coherence."""

    def __init__(self, *, block_length: int = 24, random_state: int | None = 42) -> None:
        if block_length < 2:
            raise ValueError("block_length must be >= 2")
        self.block_length = block_length
        self.random_state = random_state
        self.rng = np.random.default_rng(random_state)

    def synthesize(
        self,
        df: pd.DataFrame,
        *,
        time_col: str,
        entity_col: str | None = None,
        n_entities: int | None = None,
        rows_per_entity: int | None = None,
    ) -> tuple[pd.DataFrame, SequenceReport]:
        if time_col not in df:
            raise ValueError(f"missing time column: {time_col}")
        working = df.copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce")
        if working[time_col].isna().any():
            raise ValueError("time column contains unparseable values")
        group_key = entity_col if entity_col and entity_col in working else None
        groups = [g.sort_values(time_col).reset_index(drop=True) for _, g in working.groupby(group_key, dropna=False)] if group_key else [working.sort_values(time_col).reset_index(drop=True)]
        groups = [g for g in groups if len(g) >= 2]
        if not groups:
            raise ValueError("no sequence has at least two observations")
        target_entities = n_entities or len(groups)
        target_rows = rows_per_entity or max(2, int(np.median([len(g) for g in groups])))
        outputs: list[pd.DataFrame] = []
        for entity_index in range(target_entities):
            source = groups[int(self.rng.integers(0, len(groups)))]
            blocks: list[pd.DataFrame] = []
            while sum(len(b) for b in blocks) < target_rows:
                size = min(self.block_length, len(source), target_rows - sum(len(b) for b in blocks))
                start_max = max(0, len(source) - size)
                start = int(self.rng.integers(0, start_max + 1))
                blocks.append(source.iloc[start:start+size].copy())
            out = pd.concat(blocks, ignore_index=True).head(target_rows)
            source_delta = source[time_col].sort_values().diff().dropna().median()
            delta = source_delta if pd.notna(source_delta) and source_delta > pd.Timedelta(0) else pd.Timedelta(seconds=1)
            start_time = source[time_col].min()
            out[time_col] = [start_time + i * delta for i in range(len(out))]
            if group_key:
                out[group_key] = f"SYN-{entity_index:06d}"
            outputs.append(out)
        synthetic = pd.concat(outputs, ignore_index=True)
        report = self.validate(synthetic, time_col=time_col, entity_col=group_key)
        report.block_length = self.block_length
        report.warnings.append("Block bootstrap is a baseline; use a validated sequence-model adapter for long-range dynamics, irregular sampling, or control-response simulation.")
        return synthetic, report

    def validate(self, df: pd.DataFrame, *, time_col: str, entity_col: str | None = None) -> SequenceReport:
        groups = list(df.groupby(entity_col, dropna=False)) if entity_col and entity_col in df else [("all", df)]
        monotonic = 0
        duplicates = 0
        invalid = 0
        for _, group in groups:
            times = pd.to_datetime(group[time_col], errors="coerce")
            invalid += int(times.isna().sum())
            monotonic += int(times.is_monotonic_increasing)
            duplicates += int(times.duplicated().sum())
        return SequenceReport(len(df), len(groups), monotonic, duplicates, self.block_length, invalid)
