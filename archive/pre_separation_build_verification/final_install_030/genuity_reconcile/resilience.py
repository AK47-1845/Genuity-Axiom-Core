"""Executable failure-injection checks used by the one-command demonstration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from .config import resolve_default_pack
from .fixtures import generate_demo_packet


def _write_ocr(folder: Path, name: str, payload: dict[str, Any]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(payload), encoding="utf-8")


def run_resilience_scorecard(domain_pack: str | Path | None = None) -> dict[str, Any]:
    # Local import avoids making the primary pipeline depend on this optional demo harness.
    from .pipeline import ReconciliationPipeline

    checks: list[dict[str, Any]] = []

    def record(check_id: str, fn: Callable[[], tuple[bool, str]]) -> None:
        try:
            passed, observation = fn()
        except Exception as exc:  # The scorecard must report a failed control rather than hide it.
            passed, observation = False, f"unexpected {type(exc).__name__}: {exc}"
        checks.append(
            {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observation": observation}
        )

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)

        def malformed_contract() -> tuple[bool, str]:
            folder = root / "malformed"
            _write_ocr(
                folder,
                "bad.json",
                {
                    "page_count": 1,
                    "text": "PURCHASE ORDER",
                    "fields": [{"name": "po_number", "value": "BAD", "confidence": 1.2, "page": 1, "region": "header"}],
                },
            )
            try:
                ReconciliationPipeline(domain_pack, allow_vlm=False).run(folder)
            except ValueError as exc:
                return "confidence must be between 0 and 1" in str(exc), "invalid confidence rejected before reconciliation"
            return False, "malformed confidence was accepted"

        record("malformed_ocr_contract_rejected", malformed_contract)

        def unknown_quarantine() -> tuple[bool, str]:
            folder = root / "unknown"
            _write_ocr(
                folder,
                "legacy.json",
                {
                    "page_count": 1,
                    "text": "UNCONFIGURED LEGACY SHEET",
                    "fields": [{"name": "part_number", "value": "P-1", "confidence": 0.99, "page": 1, "region": "body"}],
                },
            )
            result = ReconciliationPipeline(domain_pack, allow_vlm=False).run(folder)
            field = result.decisions[0]
            passed = field.status == "UNCLASSIFIED_SOURCE" and field.acceptance == "REVIEW"
            return passed, f"status={field.status}; acceptance={field.acceptance}"

        record("unknown_document_quarantined", unknown_quarantine)

        def required_omission() -> tuple[bool, str]:
            folder = root / "omission"
            _write_ocr(
                folder,
                "po.json",
                {
                    "page_count": 1,
                    "text": "PURCHASE ORDER\nPO NUMBER: P-7",
                    "fields": [
                        {"name": "po_number", "value": "P-7", "confidence": 0.99, "page": 1, "region": "header"},
                        {"name": "part_number", "value": "PART-7", "confidence": 0.99, "page": 1, "region": "line"},
                    ],
                },
            )
            result = ReconciliationPipeline(domain_pack, allow_vlm=False).run(folder)
            missing = {item["field_name"] for item in result.exceptions if item["status"] == "UNRESOLVED"}
            return missing == {"supplier", "quantity"}, f"unresolved={sorted(missing)}"

        record("omitted_required_fields_escalated", required_omission)

        def alias_collision() -> tuple[bool, str]:
            folder = root / "alias_collision"
            _write_ocr(
                folder,
                "collision.json",
                {
                    "page_count": 1,
                    "text": "PURCHASE ORDER",
                    "fields": [
                        {"name": "po_no", "value": "PO-A", "confidence": 0.99, "page": 1, "region": "header"},
                        {"name": "po_number", "value": "PO-B", "confidence": 0.99, "page": 1, "region": "header"},
                    ],
                },
            )
            try:
                ReconciliationPipeline(domain_pack, allow_vlm=False).run(folder)
            except ValueError as exc:
                return "aliases collapse multiple inputs" in str(exc), "canonical po_number alias collision rejected"
            return False, "multiple source fields collapsed to one canonical field"

        record("canonical_field_alias_collision_rejected", alias_collision)

        def tampered_cache() -> tuple[bool, str]:
            packet = generate_demo_packet(root / "cache_packet")
            cache = root / "model_cache"
            ReconciliationPipeline(domain_pack, allow_vlm=True, cache_dir=cache).run(packet["ocr"])
            cache_path = next(cache.glob("*.json"))
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            payload["candidate"] = 123456
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
            try:
                ReconciliationPipeline(domain_pack, allow_vlm=True, cache_dir=cache).run(packet["ocr"])
            except RuntimeError as exc:
                return "failed integrity validation" in str(exc), "altered cached candidate failed integrity validation"
            return False, "altered model cache was trusted"

        record("tampered_model_cache_rejected", tampered_cache)

        def disallowed_reconstruction() -> tuple[bool, str]:
            source_pack = Path(domain_pack) if domain_pack else resolve_default_pack()
            pack = json.loads(source_pack.read_text(encoding="utf-8"))
            pack["permitted_reconstruction_methods"].remove("quantity_times_unit_price")
            restricted = root / "restricted_pack.json"
            restricted.write_text(json.dumps(pack), encoding="utf-8")
            packet = generate_demo_packet(root / "policy_packet")
            try:
                ReconciliationPipeline(restricted, allow_vlm=False).run(packet["ocr"])
            except RuntimeError as exc:
                return "integrity gate rejected output" in str(exc), "forbidden reconstruction failed the integrity gate"
            return False, "domain policy violation did not fail closed"

        record("domain_policy_violation_rejected", disallowed_reconstruction)

    passed = sum(item["result"] == "PASS" for item in checks)
    return {
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "scope": "Executable demo failure injections; not a substitute for production red-team testing.",
    }
