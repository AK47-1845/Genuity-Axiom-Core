"""Evaluate exported field decisions against a client-supplied blind truth CSV."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


def _parse_expected(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def evaluate_decisions(
    decisions_path: str | Path,
    truth_csv_path: str | Path,
    *,
    relative_tolerance: float = 1e-6,
    absolute_tolerance: float = 1e-6,
) -> dict[str, Any]:
    decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates: list[tuple[str, str]] = []
    for item in decisions:
        key = (item["document_id"], item["name"])
        if key in by_key:
            duplicates.append(key)
        by_key[key] = item
    if duplicates:
        raise ValueError(f"Decision export contains duplicate document/field keys: {duplicates[:3]}")
    with Path(truth_csv_path).open(encoding="utf-8-sig", newline="") as handle:
        truth_rows = list(csv.DictReader(handle))
    required = {"document_id", "field_name", "expected_json", "critical"}
    if not truth_rows:
        raise ValueError("Truth CSV contains no rows")
    missing_columns = sorted(required - set(truth_rows[0]))
    if missing_columns:
        raise ValueError(f"Truth CSV is missing columns: {', '.join(missing_columns)}")

    rows: list[dict[str, Any]] = []
    for truth in truth_rows:
        key = (truth["document_id"], truth["field_name"])
        expected = _parse_expected(truth["expected_json"])
        decision = by_key.get(key)
        actual = decision.get("value") if decision else None
        if isinstance(expected, (int, float)) and not isinstance(expected, bool) and isinstance(actual, (int, float)) and not isinstance(actual, bool):
            correct = math.isclose(
                float(expected), float(actual), rel_tol=relative_tolerance, abs_tol=absolute_tolerance
            )
        else:
            correct = expected == actual
        accepted = bool(decision and decision.get("acceptance") == "ACCEPTED")
        critical = truth["critical"].strip().casefold() in {"true", "1", "yes", "y"}
        rows.append(
            {
                "document_id": key[0],
                "field_name": key[1],
                "critical": critical,
                "expected": expected,
                "actual": actual,
                "emitted": decision is not None,
                "accepted": accepted,
                "correct": correct,
                "accepted_correct": accepted and correct,
                "incorrect_auto_accept": accepted and not correct,
                "evidence_ids": decision.get("evidence_ids", []) if decision else [],
            }
        )

    def metrics(scope: list[dict[str, Any]]) -> dict[str, Any]:
        accepted = [item for item in scope if item["accepted"]]
        accepted_correct = [item for item in accepted if item["correct"]]
        return {
            "expected_fields": len(scope),
            "emitted_fields": sum(item["emitted"] for item in scope),
            "accepted_fields": len(accepted),
            "correctly_accepted_fields": len(accepted_correct),
            "incorrect_auto_accepts": sum(item["incorrect_auto_accept"] for item in scope),
            "precision": round(len(accepted_correct) / len(accepted), 6) if accepted else None,
            "automatic_coverage": round(len(accepted_correct) / len(scope), 6) if scope else None,
            "accepted_evidence_coverage": round(
                sum(bool(item["evidence_ids"]) for item in accepted) / len(accepted), 6
            )
            if accepted
            else None,
        }

    critical_rows = [item for item in rows if item["critical"]]
    return {
        "evaluation_type": "client_supplied_blind_truth",
        "tolerances": {"relative": relative_tolerance, "absolute": absolute_tolerance},
        "overall": metrics(rows),
        "critical": metrics(critical_rows),
        "rows": rows,
        "gate_recommendation": {
            "zero_incorrect_critical_auto_accepts": not any(
                item["critical"] and item["incorrect_auto_accept"] for item in rows
            ),
            "critical_accepted_evidence_coverage_100_percent": (
                metrics(critical_rows)["accepted_evidence_coverage"] in {1.0, None}
            ),
        },
    }
