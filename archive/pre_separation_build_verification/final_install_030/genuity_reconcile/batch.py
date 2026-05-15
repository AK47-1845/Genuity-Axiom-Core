"""Isolated multi-packet orchestration for folders of connected document chains."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .pipeline import ReconciliationPipeline, export_result
from .verification import verify_output


def run_packet_batch(
    ocr_root: str | Path,
    output_root: str | Path,
    *,
    domain_pack: str | Path | None = None,
    allow_vlm: bool = False,
    cache_root: str | Path | None = None,
) -> dict[str, Any]:
    source_root = Path(ocr_root)
    destination = Path(output_root)
    packet_dirs = sorted(
        folder for folder in source_root.iterdir()
        if folder.is_dir() and any(folder.glob("*.json"))
    )
    if not packet_dirs:
        raise ValueError(f"No packet subfolders containing OCR JSON were found in {source_root}")
    destination.mkdir(parents=True, exist_ok=True)
    cache_base = Path(cache_root) if cache_root else destination / ".genuity_cache"
    packet_rows: list[dict[str, Any]] = []
    totals = {
        "packets": 0,
        "pages_processed": 0,
        "fields_processed": 0,
        "automatically_accepted_fields": 0,
        "verified_fields": 0,
        "human_review_cases": 0,
        "unresolved_fields": 0,
        "external_model_calls": 0,
        "model_cache_hits": 0,
        "estimated_total_cost_usd": 0.0,
    }
    for packet_dir in packet_dirs:
        packet_output = destination / packet_dir.name
        result = ReconciliationPipeline(
            domain_pack=domain_pack,
            allow_vlm=allow_vlm,
            cache_dir=cache_base / packet_dir.name,
        ).run(packet_dir)
        export_result(result, packet_output)
        verification = verify_output(packet_output)
        if verification["status"] != "PASS":
            raise RuntimeError(f"Packet export verification failed: {packet_dir.name}")
        selected_cost = next(
            item for item in result.cost_report["comparison"]
            if item["scenario"] == "E_Genuity_selective_routing"
        )["estimated_total_batch_cost_usd"]
        row = {
            "packet": packet_dir.name,
            "status": "PASS",
            "semantic_fingerprint": json.loads(
                (packet_output / "run_manifest.json").read_text(encoding="utf-8")
            )["reproducibility_fingerprint"],
            "pages_processed": result.metrics["pages_processed"],
            "verified_fields": result.metrics["verified_fields"],
            "human_review_cases": result.metrics["human_review_cases"],
            "unresolved_fields": result.metrics["unresolved_fields"],
            "estimated_total_cost_usd": selected_cost,
            "output_directory": str(packet_output.resolve()),
        }
        packet_rows.append(row)
        totals["packets"] += 1
        for key in [
            "pages_processed", "fields_processed", "automatically_accepted_fields", "verified_fields",
            "human_review_cases", "unresolved_fields", "external_model_calls", "model_cache_hits",
        ]:
            totals[key] += result.metrics[key]
        totals["estimated_total_cost_usd"] += selected_cost
    totals["estimated_total_cost_usd"] = round(totals["estimated_total_cost_usd"], 6)
    payload = {
        "schema_version": "genuity_packet_batch_v1",
        "status": "PASS",
        "isolation_model": "one connected procurement chain per packet subfolder",
        "totals": totals,
        "packets": packet_rows,
    }
    payload["batch_fingerprint"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    (destination / "batch_summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload
