"""Configuration loading for client/domain packs."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


def load_domain_pack(path: str | Path) -> dict[str, Any]:
    pack_path = Path(path)
    def reject_constant(value: str) -> None:
        raise ValueError(f"Domain pack contains non-finite JSON number: {value}")

    data = json.loads(pack_path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    if not isinstance(data, dict):
        raise ValueError("Domain pack must be a JSON object")
    required = {
        "document_types",
        "critical_fields",
        "source_authority",
        "join_keys",
        "allowed_part_numbers",
        "normalisation",
        "permitted_reconstruction_methods",
        "permitted_imputation_purposes",
        "pricing",
        "human_review",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"Domain pack is missing required keys: {', '.join(missing)}")
    if (
        not isinstance(data["document_types"], dict)
        or not data["document_types"]
        or not all(
            isinstance(name, str)
            and name
            and isinstance(cues, list)
            and cues
            and all(isinstance(cue, str) and cue for cue in cues)
            for name, cues in data["document_types"].items()
        )
    ):
        raise ValueError("Every configured document type must define at least one classification cue")
    for list_key in [
        "critical_fields", "join_keys", "allowed_part_numbers", "permitted_reconstruction_methods",
        "permitted_imputation_purposes",
    ]:
        values = data[list_key]
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"{list_key} must be an array of non-empty strings")
        if len(values) != len(set(values)):
            raise ValueError(f"{list_key} must not contain duplicates")
    if not isinstance(data["source_authority"], dict) or any(
        not isinstance(order, list) or not order or any(item not in data["document_types"] for item in order)
        for order in data["source_authority"].values()
    ):
        raise ValueError("source_authority entries must name configured document types")
    if not 0.0 <= float(data.get("review_threshold", 0.0)) <= 1.0:
        raise ValueError("review_threshold must be between 0 and 1")
    hourly_cost = float(data["human_review"].get("hourly_cost_usd", -1))
    if not math.isfinite(hourly_cost) or hourly_cost < 0:
        raise ValueError("human_review.hourly_cost_usd must be non-negative")
    minutes_per_case = float(data["human_review"].get("minutes_per_case", -1))
    if not math.isfinite(minutes_per_case) or minutes_per_case < 0:
        raise ValueError("human_review.minutes_per_case must be non-negative")
    required_fields = data.get("required_fields", {})
    if not isinstance(required_fields, dict) or any(
        document_type not in data["document_types"]
        or not isinstance(fields, list)
        or any(not isinstance(field, str) or not field for field in fields)
        or len(fields) != len(set(fields))
        for document_type, fields in required_fields.items()
    ):
        raise ValueError("required_fields must map configured document types to unique field names")
    normalisation = data["normalisation"]
    try:
        tensile = normalisation["tensile_strength_mpa"]
        tensile_minimum = float(tensile["minimum"])
        tensile_maximum = float(tensile["maximum"])
        psi_to_mpa = float(normalisation["unit_conversions"]["psi_to_mpa"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("normalisation must define tensile bounds and psi_to_mpa") from exc
    if (
        not all(math.isfinite(value) for value in [tensile_minimum, tensile_maximum, psi_to_mpa])
        or tensile_minimum >= tensile_maximum
        or psi_to_mpa <= 0
    ):
        raise ValueError("normalisation tensile bounds and psi_to_mpa must be valid positive values")
    pricing = data["pricing"]
    for key in [
        "input_usd_per_million_tokens", "output_usd_per_million_tokens", "local_compute_usd_per_page",
        "ocr_baseline_usd_per_page_assumption",
    ]:
        value = float(pricing.get(key, -1))
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"pricing.{key} must be non-negative")
    tokenization = pricing.get("vision_tokenization", {})
    required_token_keys = {
        "patch_size_pixels",
        "high_detail_patch_budget",
        "gpt_5_4_mini_multiplier",
        "full_page_width_pixels",
        "full_page_height_pixels",
        "full_page_post_resize_patches",
        "full_page_prompt_text_tokens",
        "full_page_output_tokens",
        "crop_width_pixels",
        "crop_height_pixels",
        "crop_prompt_text_tokens",
        "crop_output_tokens",
    }
    token_missing = sorted(required_token_keys - set(tokenization))
    if token_missing:
        raise ValueError(f"pricing.vision_tokenization is missing: {', '.join(token_missing)}")
    positive_token_keys = {
        "patch_size_pixels", "high_detail_patch_budget", "gpt_5_4_mini_multiplier",
        "full_page_width_pixels", "full_page_height_pixels", "full_page_post_resize_patches",
        "crop_width_pixels", "crop_height_pixels",
    }
    invalid_token_values = sorted(
        key for key in required_token_keys
        if not isinstance(tokenization[key], (int, float))
        or not math.isfinite(float(tokenization[key]))
        or float(tokenization[key]) < (0 if key not in positive_token_keys else 1)
    )
    if invalid_token_values:
        raise ValueError(
            "pricing.vision_tokenization contains invalid numeric values: "
            + ", ".join(invalid_token_values)
        )
    return data


def resolve_default_pack() -> Path:
    filename = "industrial_material_packet.json"
    candidates = [
        Path(__file__).resolve().parent.parent / "domain_packs" / filename,
        Path(sys.prefix) / "domain_packs" / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Default industrial domain pack was not installed; pass --domain-pack explicitly"
    )
