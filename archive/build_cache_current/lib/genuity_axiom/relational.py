"""Relational schema contracts, integrity validation, and safe baseline synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Relationship:
    parent_table: str
    parent_key: str
    child_table: str
    child_key: str
    nullable: bool = False


@dataclass
class RelationalIntegrityReport:
    passed: bool
    orphan_counts: dict[str, int]
    duplicate_primary_keys: dict[str, int]
    row_counts: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    empty_tables: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class RelationalSynthesizer:
    """Baseline that preserves PK/FK integrity while synthesizing table bodies.

    It deliberately does not claim to learn deep cross-table correlations.
    """

    def __init__(self, *, random_state: int | None = 42) -> None:
        self.random_state = random_state
        self.rng = np.random.default_rng(random_state)

    def validate(
        self,
        tables: dict[str, pd.DataFrame],
        *,
        primary_keys: dict[str, str],
        relationships: list[Relationship],
    ) -> RelationalIntegrityReport:
        orphans: dict[str, int] = {}
        duplicates: dict[str, int] = {}
        warnings: list[str] = []
        empty_tables = sorted(name for name, table in tables.items() if table.empty)
        if empty_tables:
            warnings.append("empty source tables cannot be synthesized: " + ", ".join(empty_tables))
        for table, key in primary_keys.items():
            if table not in tables or key not in tables[table]:
                duplicates[table] = len(tables.get(table, []))
                warnings.append(f"missing primary key {table}.{key}")
            else:
                duplicates[table] = int(tables[table][key].duplicated().sum() + tables[table][key].isna().sum())
        for rel in relationships:
            label = f"{rel.child_table}.{rel.child_key}->{rel.parent_table}.{rel.parent_key}"
            if rel.parent_table not in tables or rel.child_table not in tables:
                orphans[label] = len(tables.get(rel.child_table, []))
                continue
            parent = tables[rel.parent_table]
            child = tables[rel.child_table]
            if rel.parent_key not in parent or rel.child_key not in child:
                orphans[label] = len(child)
                continue
            parent_values = set(parent[rel.parent_key].dropna())
            child_values = child[rel.child_key]
            invalid = ~child_values.isin(parent_values)
            if rel.nullable:
                invalid &= child_values.notna()
            orphans[label] = int(invalid.sum())
        passed = not empty_tables and not any(orphans.values()) and not any(duplicates.values())
        return RelationalIntegrityReport(
            passed=passed,
            orphan_counts=orphans,
            duplicate_primary_keys=duplicates,
            row_counts={name: len(df) for name, df in tables.items()},
            warnings=warnings,
            empty_tables=empty_tables,
        )

    def synthesize(
        self,
        tables: dict[str, pd.DataFrame],
        *,
        primary_keys: dict[str, str],
        relationships: list[Relationship],
        scale: float = 1.0,
    ) -> tuple[dict[str, pd.DataFrame], RelationalIntegrityReport]:
        if scale <= 0:
            raise ValueError("scale must be positive")
        original_report = self.validate(tables, primary_keys=primary_keys, relationships=relationships)
        if not original_report.passed:
            raise ValueError(f"source relational integrity failed: {original_report.to_dict()}")
        output: dict[str, pd.DataFrame] = {}
        key_maps: dict[tuple[str, str], dict[Any, Any]] = {}
        for table_name, source in tables.items():
            n = max(1, int(round(len(source) * scale)))
            sampled = source.sample(n=n, replace=n > len(source), random_state=self.random_state).reset_index(drop=True).copy()
            pk = primary_keys.get(table_name)
            if pk and pk in sampled:
                original_values = sampled[pk].tolist()
                new_values = [f"SYN-{table_name.upper()}-{i:08d}" for i in range(n)]
                sampled[pk] = new_values
                mapping: dict[Any, Any] = {}
                for old, new in zip(original_values, new_values):
                    mapping.setdefault(old, new)
                key_maps[(table_name, pk)] = mapping
            output[table_name] = sampled
        for rel in relationships:
            parent_values = output[rel.parent_table][rel.parent_key].tolist()
            child = output[rel.child_table]
            if not parent_values:
                raise ValueError(f"synthetic parent table is empty: {rel.parent_table}")
            source_child = tables[rel.child_table][rel.child_key]
            null_rate = float(source_child.isna().mean()) if rel.nullable else 0.0
            choices = self.rng.choice(parent_values, size=len(child), replace=True).astype(object)
            if null_rate:
                mask = self.rng.random(len(child)) < null_rate
                choices[mask] = None
            child[rel.child_key] = choices
        report = self.validate(output, primary_keys=primary_keys, relationships=relationships)
        report.warnings.append("Local baseline preserves integrity but not full cross-table statistical dependence; use a validated relational adapter for enterprise release.")
        return output, report
