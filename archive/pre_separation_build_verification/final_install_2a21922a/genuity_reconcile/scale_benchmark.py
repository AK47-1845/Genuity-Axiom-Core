"""Dependency-free throughput smoke benchmark for the adapter/reconciliation path."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any


def run_scale_benchmark(
    domain_pack: str | Path,
    *,
    document_count: int = 1000,
    duplicate_fraction: float = 0.20,
) -> dict[str, Any]:
    # Local import avoids a module cycle with pipeline.run_demo.
    from .pipeline import ReconciliationPipeline

    unique_count = max(1, round(document_count * (1.0 - duplicate_fraction)))
    payloads: list[dict[str, Any]] = []
    for index in range(unique_count):
        po_number = "SCALE-SINGLE-CHAIN"
        part_number = "CLIENT-SCALE-PART"
        payloads.append(
            {
                "page_count": 1,
                "text": f"PURCHASE ORDER\nPO NUMBER: {po_number}\nPART NUMBER: {part_number}\nQUANTITY: 1 PCS\nPAGE INDEX: {index}",
                "fields": [
                    {"name": "po_number", "value": po_number, "confidence": 0.99, "page": 1, "region": "header"},
                    {"name": "part_number", "value": part_number, "confidence": 0.99, "page": 1, "region": "line"},
                    {"name": "supplier", "value": "Scale Fixture Supplier", "confidence": 0.99, "page": 1, "region": "header"},
                    {"name": "quantity", "value": 1, "unit": "pcs", "confidence": 0.99, "page": 1, "region": "line"},
                ],
            }
        )
    duplicate_count = document_count - unique_count
    with tempfile.TemporaryDirectory() as temp:
        ocr_dir = Path(temp) / "ocr"
        ocr_dir.mkdir()
        for index in range(document_count):
            payload = payloads[index] if index < unique_count else payloads[index - unique_count]
            (ocr_dir / f"scale_{index:07d}.json").write_text(
                json.dumps(payload, separators=(",", ":")), encoding="utf-8"
            )
        started = time.perf_counter()
        result = ReconciliationPipeline(domain_pack=domain_pack, allow_vlm=False).run(ocr_dir)
        elapsed = time.perf_counter() - started
    return {
        "benchmark_type": "local_smoke_not_capacity_claim",
        "scope": "one connected chain with many source documents; multi-chain throughput uses the isolated batch command",
        "documents": document_count,
        "pages": result.metrics["pages_processed"],
        "unique_documents": unique_count,
        "duplicate_documents": duplicate_count,
        "cache_hits": result.metrics["cache_hits"],
        "fields_processed": result.metrics["fields_processed"],
        "external_model_calls": result.metrics["external_model_calls"],
        "integrity_status": result.integrity_report["status"],
        "elapsed_seconds": round(elapsed, 6),
        "documents_per_second": round(document_count / max(elapsed, 1e-9), 2),
        "fields_per_second": round(result.metrics["fields_processed"] / max(elapsed, 1e-9), 2),
        "environment_note": "Single-process local filesystem smoke test; rerun on deployment hardware for capacity planning.",
    }
