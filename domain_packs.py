"""Discovery and validation for Axiom JSON domain packs."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


_REQUIRED = {"pack_id", "buyer_decision", "modalities", "scenario_families", "hard_constraints", "acceptance_metrics", "required_approvers"}
_LIST_FIELDS = {"modalities", "scenario_families", "hard_constraints", "acceptance_metrics", "required_approvers"}
_MODALITIES = {"tabular", "relational", "time_series", "event", "text", "document", "graph", "image", "audio", "video", "simulation", "multimodal"}


def domain_pack_directories() -> list[Path]:
    candidates = [
        Path(__file__).resolve().parent / "domain_packs",
        Path(__file__).resolve().parent.parent / "domain_packs",
        Path(sys.prefix) / "domain_packs",
    ]
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique and candidate.is_dir():
            unique.append(candidate)
    return unique


def list_domain_packs(*, include_legacy: bool = False) -> list[str]:
    names: set[str] = set()
    for directory in domain_pack_directories():
        for path in directory.glob("*.json"):
            if include_legacy:
                names.add(path.stem)
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not validate_domain_pack(payload):
                names.add(path.stem)
    return sorted(names)


def load_domain_pack(name: str) -> dict[str, Any]:
    safe_name = Path(name).stem
    for directory in domain_pack_directories():
        path = directory / f"{safe_name}.json"
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            issues = validate_domain_pack(payload)
            if issues:
                raise ValueError(f"invalid domain pack {safe_name!r}: " + "; ".join(issues))
            return payload
    raise FileNotFoundError(f"domain pack not found: {safe_name}")


def validate_domain_pack(payload: dict[str, Any]) -> list[str]:
    issues = [f"missing required field: {key}" for key in sorted(_REQUIRED - set(payload))]
    for key in _REQUIRED.intersection(payload):
        if payload[key] in (None, "", []):
            issues.append(f"required field is empty: {key}")
    if "pack_id" in payload and (not isinstance(payload["pack_id"], str) or not payload["pack_id"].startswith("axiom.")):
        issues.append("pack_id must be a versioned axiom.* string")
    if "buyer_decision" in payload and not isinstance(payload["buyer_decision"], str):
        issues.append("buyer_decision must be a string")
    for key in _LIST_FIELDS.intersection(payload):
        value = payload[key]
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            issues.append(f"{key} must be a non-empty list of strings")
        elif len(value) != len(set(value)):
            issues.append(f"{key} contains duplicates")
    if isinstance(payload.get("modalities"), list):
        unsupported = sorted(set(payload["modalities"]) - _MODALITIES)
        if unsupported:
            issues.append("unsupported modalities: " + ", ".join(unsupported))
    return issues
