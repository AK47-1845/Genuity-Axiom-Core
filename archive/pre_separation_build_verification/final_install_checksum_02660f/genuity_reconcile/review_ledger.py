"""Validated, tamper-evident human-review decisions for exception handoff."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DISPOSITIONS = {
    "CONFIRM_CANDIDATE",
    "ACCEPT_CORRECTED_VALUE",
    "REJECT_CANDIDATE",
    "NEEDS_NEW_EVIDENCE",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _parse_timestamp(value: str, row_number: int) -> str:
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"resolution row {row_number}: reviewed_at_utc must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"resolution row {row_number}: reviewed_at_utc must include a UTC offset")
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"resolution row {row_number}: reviewed_at_utc must be UTC")
    return parsed.isoformat().replace("+00:00", "Z")


def create_review_ledger(
    review_queue_path: str | Path,
    resolutions_csv_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    queue_path = Path(review_queue_path)
    queue_bytes = queue_path.read_bytes()
    queue = json.loads(queue_bytes)
    if not isinstance(queue, list):
        raise ValueError("review queue must be a JSON array")
    by_id = {item["exception_id"]: item for item in queue}
    if len(by_id) != len(queue):
        raise ValueError("review queue contains duplicate exception IDs")

    resolution_path = Path(resolutions_csv_path)
    with resolution_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "exception_id", "disposition", "resolved_value_json", "reviewer",
            "reviewed_at_utc", "evidence_reference", "note",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"resolution CSV is missing columns: {', '.join(sorted(missing))}")
        rows = list(reader)

    seen: set[str] = set()
    events: list[dict[str, Any]] = []
    previous_hash = "0" * 64
    queue_hash = _sha256(queue_bytes)
    for row_number, row in enumerate(rows, start=2):
        exception_id = row["exception_id"].strip()
        if exception_id not in by_id:
            raise ValueError(f"resolution row {row_number}: unknown exception_id {exception_id}")
        if exception_id in seen:
            raise ValueError(f"resolution row {row_number}: duplicate exception_id {exception_id}")
        seen.add(exception_id)
        disposition = row["disposition"].strip().upper()
        if disposition not in DISPOSITIONS:
            raise ValueError(f"resolution row {row_number}: unsupported disposition {disposition}")
        reviewer = row["reviewer"].strip()
        if not reviewer:
            raise ValueError(f"resolution row {row_number}: reviewer is required")
        reviewed_at = _parse_timestamp(row["reviewed_at_utc"], row_number)
        evidence_reference = row["evidence_reference"].strip()
        if disposition in {"CONFIRM_CANDIDATE", "ACCEPT_CORRECTED_VALUE"} and not evidence_reference:
            raise ValueError(f"resolution row {row_number}: an accepting disposition requires evidence_reference")
        exception = by_id[exception_id]
        if disposition == "CONFIRM_CANDIDATE" and exception.get("candidate") is None:
            raise ValueError(f"resolution row {row_number}: cannot confirm a blank candidate")
        resolved_value: Any = None
        raw_value = row["resolved_value_json"].strip()
        if disposition == "ACCEPT_CORRECTED_VALUE":
            if not raw_value:
                raise ValueError(f"resolution row {row_number}: corrected value is required")
            try:
                resolved_value = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"resolution row {row_number}: resolved_value_json is invalid") from exc
        elif raw_value:
            raise ValueError(
                f"resolution row {row_number}: resolved_value_json is only allowed for ACCEPT_CORRECTED_VALUE"
            )
        event = {
            "exception_id": exception_id,
            "field_id": exception["field_id"],
            "queue_dedupe_key": exception["dedupe_key"],
            "disposition": disposition,
            "candidate_snapshot": exception.get("candidate"),
            "resolved_value": resolved_value,
            "reviewer": reviewer,
            "reviewed_at_utc": reviewed_at,
            "evidence_reference": evidence_reference,
            "note": row["note"].strip(),
            "previous_event_hash": previous_hash,
        }
        event_hash = _sha256(_canonical(event))
        event["event_hash"] = event_hash
        events.append(event)
        previous_hash = event_hash

    ledger = {
        "schema_version": "genuity_review_ledger_v1",
        "review_queue_sha256": queue_hash,
        "event_count": len(events),
        "events": events,
        "final_chain_hash": previous_hash,
        "operational_note": (
            "This hash chain records human dispositions and detects uncoordinated edits; it does not authenticate the "
            "reviewer's identity without an external signature. Downstream mutation remains a separate controlled step."
        ),
    }
    Path(output_path).write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ledger


def verify_review_ledger(ledger_path: str | Path, review_queue_path: str | Path | None = None) -> dict[str, Any]:
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    errors: list[str] = []
    previous_hash = "0" * 64
    for position, stored in enumerate(ledger.get("events", []), start=1):
        event = dict(stored)
        claimed_hash = event.pop("event_hash", None)
        if event.get("previous_event_hash") != previous_hash:
            errors.append(f"event {position} previous hash mismatch")
        actual_hash = _sha256(_canonical(event))
        if claimed_hash != actual_hash:
            errors.append(f"event {position} content hash mismatch")
        previous_hash = claimed_hash or actual_hash
    if ledger.get("event_count") != len(ledger.get("events", [])):
        errors.append("event count mismatch")
    if ledger.get("final_chain_hash") != previous_hash:
        errors.append("final chain hash mismatch")
    if review_queue_path is not None:
        actual_queue_hash = _sha256(Path(review_queue_path).read_bytes())
        if ledger.get("review_queue_sha256") != actual_queue_hash:
            errors.append("review queue hash mismatch")
    return {
        "status": "PASS" if not errors else "FAIL",
        "event_count": len(ledger.get("events", [])),
        "final_chain_hash": previous_hash,
        "errors": errors,
    }
