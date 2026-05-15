"""Constraint validation and repair for engineering synthetic data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Rule:
    name: str
    column: str
    op: str
    value: Any = None
    other_column: str | None = None
    severity: str = "error"
    message: str | None = None

    def mask(self, df: pd.DataFrame) -> pd.Series:
        if self.column not in df:
            return pd.Series(False, index=df.index)

        left = df[self.column]
        right = df[self.other_column] if self.other_column else self.value

        if self.op == "ge":
            return left >= right
        if self.op == "gt":
            return left > right
        if self.op == "le":
            return left <= right
        if self.op == "lt":
            return left < right
        if self.op == "eq":
            return left == right
        if self.op == "between":
            low, high = self.value
            return (left >= low) & (left <= high)
        if self.op == "in":
            return left.isin(self.value)
        if self.op == "not_null":
            return left.notna()
        raise ValueError(f"Unsupported rule op: {self.op}")


@dataclass(frozen=True)
class ExpressionRule:
    name: str
    expression: str
    severity: str = "error"
    message: str | None = None

    def mask(self, df: pd.DataFrame) -> pd.Series:
        try:
            result = df.eval(self.expression, engine="python")
        except Exception:
            return pd.Series(False, index=df.index)
        if not isinstance(result, pd.Series):
            return pd.Series(bool(result), index=df.index)
        return result.astype(bool)


@dataclass
class ConstraintReport:
    total_rules: int
    total_violations: int
    violations_by_rule: dict[str, int]
    repaired_rows: int = 0
    blocking_violations: int = 0
    warning_violations: int = 0

    @property
    def passed(self) -> bool:
        return self.blocking_violations == 0

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "total_rules": self.total_rules,
            "total_violations": self.total_violations,
            "violations_by_rule": self.violations_by_rule,
            "repaired_rows": self.repaired_rows,
            "blocking_violations": self.blocking_violations,
            "warning_violations": self.warning_violations,
        }


@dataclass
class EngineeringConstraintSet:
    rules: list[Rule | ExpressionRule] = field(default_factory=list)

    def add(self, rule: Rule | ExpressionRule) -> "EngineeringConstraintSet":
        self.rules.append(rule)
        return self

    def add_expression(
        self,
        name: str,
        expression: str,
        *,
        severity: str = "error",
        message: str | None = None,
    ) -> "EngineeringConstraintSet":
        self.add(ExpressionRule(name=name, expression=expression, severity=severity, message=message))
        return self

    def add_bound(
        self,
        column: str,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
        severity: str = "error",
    ) -> "EngineeringConstraintSet":
        if min_value is not None and max_value is not None:
            self.add(
                Rule(
                    name=f"{column}_between",
                    column=column,
                    op="between",
                    value=(min_value, max_value),
                    severity=severity,
                )
            )
        elif min_value is not None:
            self.add(
                Rule(
                    name=f"{column}_ge_{min_value}",
                    column=column,
                    op="ge",
                    value=min_value,
                    severity=severity,
                )
            )
        elif max_value is not None:
            self.add(
                Rule(
                    name=f"{column}_le_{max_value}",
                    column=column,
                    op="le",
                    value=max_value,
                    severity=severity,
                )
            )
        return self

    def add_comparison(
        self,
        left_column: str,
        op: str,
        right_column: str,
        *,
        severity: str = "error",
    ) -> "EngineeringConstraintSet":
        self.add(
            Rule(
                name=f"{left_column}_{op}_{right_column}",
                column=left_column,
                op=op,
                other_column=right_column,
                severity=severity,
            )
        )
        return self

    def validate(self, df: pd.DataFrame) -> ConstraintReport:
        violations: dict[str, int] = {}
        total = 0
        blocking = 0
        warning = 0
        for rule in self.rules:
            try:
                passed = rule.mask(df).fillna(False)
                count = int((~passed).sum())
            except Exception:
                count = len(df)
            violations[rule.name] = count
            total += count
            if rule.severity == "warning":
                warning += count
            else:
                blocking += count
        return ConstraintReport(
            total_rules=len(self.rules),
            total_violations=total,
            violations_by_rule=violations,
            blocking_violations=blocking,
            warning_violations=warning,
        )

    def repair(self, df: pd.DataFrame) -> tuple[pd.DataFrame, ConstraintReport]:
        repaired = df.copy()
        changed_rows: set[int] = set()

        for rule in self.rules:
            if isinstance(rule, ExpressionRule):
                continue
            if rule.column not in repaired:
                continue
            try:
                passed = rule.mask(repaired).fillna(False)
            except Exception:
                continue
            bad = ~passed
            if not bad.any():
                continue

            if rule.op == "ge" and rule.other_column is None:
                repaired.loc[bad, rule.column] = rule.value
            elif rule.op == "gt" and rule.other_column is None:
                repaired.loc[bad, rule.column] = np.nextafter(float(rule.value), np.inf)
            elif rule.op == "le" and rule.other_column is None:
                repaired.loc[bad, rule.column] = rule.value
            elif rule.op == "lt" and rule.other_column is None:
                repaired.loc[bad, rule.column] = np.nextafter(float(rule.value), -np.inf)
            elif rule.op == "between":
                low, high = rule.value
                repaired[rule.column] = pd.to_numeric(
                    repaired[rule.column], errors="coerce"
                ).clip(low, high)
            elif rule.op == "in":
                allowed = list(rule.value)
                if allowed:
                    repaired.loc[bad, rule.column] = allowed[0]
            elif rule.op == "not_null":
                fill_value = _fallback_fill_value(repaired[rule.column])
                repaired.loc[bad, rule.column] = fill_value
            else:
                continue

            changed_rows.update(repaired.index[bad].tolist())

        report = self.validate(repaired)
        report.repaired_rows = len(changed_rows)
        return repaired, report

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, domain: str = "generic_engineering") -> "EngineeringConstraintSet":
        constraints = cls()
        lowered = {str(c).lower(): c for c in df.columns}

        for lower, original in lowered.items():
            if any(token in lower for token in _POSITIVE_PHYSICAL_TOKENS):
                if pd.api.types.is_numeric_dtype(df[original]):
                    constraints.add_bound(original, min_value=0.0)

            if "percentage" in lower or lower.endswith("_pct") or lower.endswith("_percent"):
                if pd.api.types.is_numeric_dtype(df[original]):
                    constraints.add_bound(original, min_value=0.0, max_value=100.0)

            if lower in {"pass_fail", "status"}:
                values = list(df[original].dropna().unique())
                if values:
                    constraints.add(Rule(f"{original}_known_values", original, "in", values))

        pairs = [
            ("yield", "tensile", "le"),
            ("inlet", "outlet", "le"),
            ("min", "max", "le"),
            ("lower", "upper", "le"),
        ]
        for left_token, right_token, op in pairs:
            left = _find_column_containing(lowered, left_token)
            right = _find_column_containing(lowered, right_token)
            if left and right and left != right:
                constraints.add_comparison(left, op, right, severity="warning")

        if domain == "materials":
            poisson = _find_column_containing(lowered, "poisson")
            if poisson:
                constraints.add_bound(poisson, min_value=0.0, max_value=0.5, severity="error")
        if domain == "energy_scada":
            flow = _find_column_containing(lowered, "flow")
            pressure = _find_column_containing(lowered, "pressure")
            if flow:
                constraints.add_bound(flow, min_value=0.0)
            if pressure:
                constraints.add_bound(pressure, min_value=0.0)
        if domain == "automotive":
            rpm = _find_column_containing(lowered, "rpm")
            torque = _find_column_containing(lowered, "torque")
            if rpm:
                constraints.add_bound(rpm, min_value=0.0)
            if torque:
                constraints.add_bound(torque, min_value=0.0)

        return constraints


_POSITIVE_PHYSICAL_TOKENS = (
    "strength",
    "pressure",
    "density",
    "hardness",
    "rpm",
    "torque",
    "flow",
    "mass",
    "weight",
    "modulus",
    "life",
    "duration",
    "thickness",
    "wingspan",
    "load",
    "energy",
)


def _find_column_containing(lowered: dict[str, str], token: str) -> str | None:
    matches = [original for lower, original in lowered.items() if token in lower]
    return matches[0] if matches else None


def _fallback_fill_value(series: pd.Series) -> Any:
    if pd.api.types.is_numeric_dtype(series):
        return float(series.median()) if series.notna().any() else 0.0
    mode = series.mode(dropna=True)
    return mode.iloc[0] if len(mode) else "UNKNOWN"
