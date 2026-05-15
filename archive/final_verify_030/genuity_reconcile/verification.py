"""Independent verification of an exported run directory."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def verify_output(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output_root = output.resolve()
    manifest_path = output / "run_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Missing run manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing: list[str] = []
    mismatched: list[str] = []
    unsafe_paths: list[str] = []
    artifact_hashes = manifest.get("artifact_sha256", {})
    if not isinstance(artifact_hashes, dict):
        raise ValueError("run manifest artifact_sha256 must be an object")
    for relative, expected in artifact_hashes.items():
        path = (output / relative).resolve()
        if not path.is_relative_to(output_root):
            unsafe_paths.append(relative)
            continue
        if not path.exists():
            missing.append(relative)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            mismatched.append(relative)
    core_paths = [output / name for name in ["canonical_records.json", "field_decisions.json", "demo_scorecard.json"]]
    semantic_matches = False
    field_decisions: list[dict[str, Any]] = []
    if all(path.exists() for path in core_paths):
        fingerprint_payload = {
            "connected_record": json.loads(core_paths[0].read_text(encoding="utf-8")),
            "field_decisions": json.loads(core_paths[1].read_text(encoding="utf-8")),
            "scorecard": json.loads(core_paths[2].read_text(encoding="utf-8")),
        }
        field_decisions = fingerprint_payload["field_decisions"]
        semantic_fingerprint = hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        semantic_matches = semantic_fingerprint == manifest.get("reproducibility_fingerprint")
    else:
        missing.extend(str(path.relative_to(output)).replace("\\", "/") for path in core_paths if not path.exists())
    integrity_path = output / "integrity_report.json"
    integrity = json.loads(integrity_path.read_text(encoding="utf-8")) if integrity_path.exists() else {"status": "MISSING"}
    domain_pack_path = output / "domain_pack_snapshot.json"
    domain_pack_hash_matches = False
    if domain_pack_path.exists():
        domain_pack = json.loads(domain_pack_path.read_text(encoding="utf-8"))
        actual_pack_hash = hashlib.sha256(
            json.dumps(domain_pack, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        domain_pack_hash_matches = actual_pack_hash == manifest.get("domain_pack_canonical_sha256")
    database_check = "NOT_PRESENT"
    database_semantic_matches: bool | None = None
    database_counts: dict[str, dict[str, int]] = {}
    database_path = output / "genuity_demo.db"
    if database_path.exists():
        connection = sqlite3.connect(database_path)
        try:
            database_check = connection.execute("PRAGMA integrity_check").fetchone()[0]
            evidence_path = output / "evidence.json"
            review_queue_path = output / "review_queue.json"
            expected_counts = {
                "documents": len(manifest.get("input_content_hashes", {})),
                "field_decisions": len(field_decisions),
                "evidence": len(json.loads(evidence_path.read_text(encoding="utf-8"))) if evidence_path.exists() else -1,
                "exceptions": len(json.loads(review_queue_path.read_text(encoding="utf-8"))) if review_queue_path.exists() else -1,
            }
            actual_counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in expected_counts
            }
            database_counts = {
                table: {"expected": expected_counts[table], "actual": actual_counts[table]}
                for table in expected_counts
            }
            database_semantic_matches = expected_counts == actual_counts
        finally:
            connection.close()
    resilience_path = output / "resilience_scorecard.json"
    resilience_status = (
        json.loads(resilience_path.read_text(encoding="utf-8")).get("status")
        if resilience_path.exists()
        else "NOT_PRESENT"
    )
    passed = (
        not missing
        and not mismatched
        and not unsafe_paths
        and semantic_matches
        and integrity["status"] == "PASS"
        and domain_pack_hash_matches
        and database_check in {"ok", "NOT_PRESENT"}
        and database_semantic_matches in {True, None}
        and resilience_status in {"PASS", "NOT_PRESENT"}
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "missing_artifacts": missing,
        "hash_mismatches": mismatched,
        "unsafe_artifact_paths": unsafe_paths,
        "semantic_fingerprint_matches": semantic_matches,
        "provenance_integrity_status": integrity["status"],
        "domain_pack_hash_matches": domain_pack_hash_matches,
        "domain_pack_name": manifest.get("domain_pack_name"),
        "domain_pack_version": manifest.get("domain_pack_version"),
        "sqlite_integrity_check": database_check,
        "sqlite_semantic_counts_match": database_semantic_matches,
        "sqlite_semantic_counts": database_counts,
        "resilience_status": resilience_status,
        "artifacts_verified": len(artifact_hashes),
        "integrity_model": "Hash verification detects uncoordinated changes; signer authenticity requires an external signature or trusted key.",
    }
