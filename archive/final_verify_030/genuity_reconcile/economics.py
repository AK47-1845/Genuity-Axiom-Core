"""Transparent token, cost, sensitivity, and scale calculations."""

from __future__ import annotations

import math
from typing import Any


def vision_token_usage(pricing: dict[str, Any]) -> dict[str, Any]:
    """Calculate billed image-token units from the official patch-based formula."""
    cfg = pricing["vision_tokenization"]
    patch = int(cfg["patch_size_pixels"])
    multiplier = float(cfg["gpt_5_4_mini_multiplier"])
    crop_patches = math.ceil(cfg["crop_width_pixels"] / patch) * math.ceil(
        cfg["crop_height_pixels"] / patch
    )
    crop_image_tokens = math.ceil(crop_patches * multiplier)
    full_image_tokens = math.ceil(cfg["full_page_post_resize_patches"] * multiplier)
    return {
        "formula": "ceil(post_resize_patch_count * model_multiplier) + prompt_text_tokens",
        "patch_size_pixels": patch,
        "patch_budget": cfg["high_detail_patch_budget"],
        "model_multiplier": multiplier,
        "full_page": {
            "dimensions_pixels": [cfg["full_page_width_pixels"], cfg["full_page_height_pixels"]],
            "post_resize_patch_count": cfg["full_page_post_resize_patches"],
            "image_tokens": full_image_tokens,
            "prompt_text_tokens": cfg["full_page_prompt_text_tokens"],
            "input_tokens": full_image_tokens + cfg["full_page_prompt_text_tokens"],
            "output_tokens": cfg["full_page_output_tokens"],
        },
        "crop": {
            "dimensions_pixels": [cfg["crop_width_pixels"], cfg["crop_height_pixels"]],
            "patch_count": crop_patches,
            "image_tokens": crop_image_tokens,
            "prompt_text_tokens": cfg["crop_prompt_text_tokens"],
            "input_tokens": crop_image_tokens + cfg["crop_prompt_text_tokens"],
            "output_tokens": cfg["crop_output_tokens"],
        },
        "source": pricing["vision_tokenization_source"],
    }


def build_business_case(cost_report: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """Build bottom-up scale economics without presenting scenario math as market fact."""
    scenarios = {item["scenario"]: item for item in cost_report["comparison"]}
    selected = scenarios["E_Genuity_selective_routing"]
    full_vlm = scenarios["D_full_page_VLM"]
    ocr_only = scenarios["A_OCR_only"]
    pages = max(int(metrics["pages_processed"]), 1)
    selected_per_page = selected["estimated_total_batch_cost_usd"] / pages
    full_per_page = full_vlm["estimated_total_batch_cost_usd"] / pages
    ocr_only_per_page = ocr_only["estimated_total_batch_cost_usd"] / pages
    save_full = max(full_per_page - selected_per_page, 0.0)
    save_ocr = max(ocr_only_per_page - selected_per_page, 0.0)

    scale_rows = []
    for volume in [100_000, 1_000_000, 10_000_000, 100_000_000, 1_000_000_000]:
        scale_rows.append(
            {
                "annual_pages": volume,
                "genuity_estimated_cost_usd": round(selected_per_page * volume, 2),
                "full_page_vlm_estimated_cost_usd": round(full_per_page * volume, 2),
                "ocr_only_with_review_estimated_cost_usd": round(ocr_only_per_page * volume, 2),
                "savings_vs_full_page_vlm_usd": round(save_full * volume, 2),
                "savings_vs_ocr_only_with_review_usd": round(save_ocr * volume, 2),
                "illustrative_revenue_at_15pct_of_full_vlm_savings_usd": round(save_full * volume * 0.15, 2),
            }
        )

    fixed_cost_break_even = []
    for fixed_cost in [50_000, 100_000, 250_000, 1_000_000]:
        fixed_cost_break_even.append(
            {
                "implementation_cost_usd": fixed_cost,
                "pages_to_break_even_vs_full_page_vlm": (
                    math.ceil(fixed_cost / save_full) if save_full else None
                ),
                "pages_to_break_even_vs_ocr_only_with_review": (
                    math.ceil(fixed_cost / save_ocr) if save_ocr else None
                ),
            }
        )

    pricing = cost_report["pricing"]
    token_usage = cost_report["token_calculation"]
    input_rate = pricing["input_usd_per_million_tokens"]
    output_rate = pricing["output_usd_per_million_tokens"]
    crop_api_cost = (
        token_usage["crop"]["input_tokens"] * input_rate
        + token_usage["crop"]["output_tokens"] * output_rate
    ) / 1_000_000
    full_api_cost = (
        token_usage["full_page"]["input_tokens"] * input_rate
        + token_usage["full_page"]["output_tokens"] * output_rate
    ) / 1_000_000
    selected_machine_per_page = (
        selected["local_or_ocr_compute_cost_usd"] + selected["external_api_cost_usd"]
    ) / pages
    full_machine_per_page = (
        full_vlm["local_or_ocr_compute_cost_usd"] + full_vlm["external_api_cost_usd"]
    ) / pages
    selected_review_cases_per_page = selected["review_cases"] / pages
    full_review_cases_per_page = full_vlm["review_cases"] / pages
    review_minutes = cost_report["human_review_assumptions"]["minutes_per_case"]
    human_sensitivity = []
    for hourly_rate in [10.0, 25.0, 45.0, 75.0]:
        selected_sensitive = selected_machine_per_page + (
            selected_review_cases_per_page * review_minutes * hourly_rate / 60.0
        )
        full_sensitive = full_machine_per_page + (
            full_review_cases_per_page * review_minutes * hourly_rate / 60.0
        )
        human_sensitivity.append(
            {
                "human_hourly_cost_usd": hourly_rate,
                "genuity_cost_per_page_usd": round(selected_sensitive, 6),
                "full_page_vlm_cost_per_page_usd": round(full_sensitive, 6),
                "savings_percent": round((1.0 - selected_sensitive / full_sensitive) * 100, 2),
            }
        )

    routing_sensitivity = []
    local_per_page = pricing["local_compute_usd_per_page"]
    ocr_per_page = pricing["ocr_baseline_usd_per_page_assumption"]
    for routing_rate in [0.01, 0.05, 0.10, 0.25, 1.0]:
        routing_sensitivity.append(
            {
                "routed_regions_per_page": routing_rate,
                "selective_machine_cost_per_page_usd": round(
                    ocr_per_page + local_per_page + routing_rate * crop_api_cost, 8
                ),
                "full_page_vlm_machine_cost_per_page_usd": round(
                    full_api_cost, 8
                ),
                "machine_cost_reduction_percent": round(
                    (1.0 - (ocr_per_page + local_per_page + routing_rate * crop_api_cost) / full_api_cost)
                    * 100,
                    2,
                ),
            }
        )

    billion_threshold = {
        "pages_for_1b_usd_savings_vs_full_page_vlm": math.ceil(1_000_000_000 / save_full)
        if save_full
        else None,
        "pages_for_1b_usd_savings_vs_ocr_only_with_review": math.ceil(1_000_000_000 / save_ocr)
        if save_ocr
        else None,
        "interpretation": (
            "These are portfolio-throughput thresholds under the stated demo assumptions, not a market-size forecast."
        ),
    }
    return {
        "model_type": "bottom_up_scenario_not_market_forecast",
        "base_batch_pages": pages,
        "unit_economics": {
            "genuity_cost_per_page_usd": round(selected_per_page, 6),
            "full_page_vlm_cost_per_page_usd": round(full_per_page, 6),
            "ocr_only_with_review_cost_per_page_usd": round(ocr_only_per_page, 6),
            "savings_per_page_vs_full_page_vlm_usd": round(save_full, 6),
            "savings_per_page_vs_ocr_only_with_review_usd": round(save_ocr, 6),
        },
        "scale_scenarios": scale_rows,
        "implementation_break_even": fixed_cost_break_even,
        "human_cost_sensitivity": human_sensitivity,
        "routing_sensitivity": routing_sensitivity,
        "billion_dollar_threshold": billion_threshold,
        "external_market_price_anchors": pricing.get("market_benchmarks", []),
        "commercial_principle": (
            "Price against measured avoided exception-handling cost, with a pilot holdout and shared audit metrics; "
            "do not price against unverified top-down market claims."
        ),
        "limitations": [
            "Linear scale scenarios do not include volume discounts, infrastructure step costs, or integration cost.",
            "Review-case rates come from the controlled packet and must be replaced with a client pilot distribution.",
            "Error-avoidance, cycle-time, working-capital, and compliance value are intentionally excluded until measured.",
        ],
    }


def estimate_customer_roi(
    pricing: dict[str, Any],
    *,
    annual_pages: int,
    human_hourly_cost_usd: float,
    review_minutes_per_case: float,
    current_review_cases_per_page: float,
    genuity_review_cases_per_page: float,
    routed_regions_per_page: float,
    existing_extraction_cost_per_page_usd: float,
    implementation_cost_usd: float,
) -> dict[str, Any]:
    """Calculate a client-editable overlay ROI scenario with common OCR cost on both arms."""
    if annual_pages <= 0:
        raise ValueError("annual_pages must be positive")
    nonnegative = {
        "human_hourly_cost_usd": human_hourly_cost_usd,
        "review_minutes_per_case": review_minutes_per_case,
        "current_review_cases_per_page": current_review_cases_per_page,
        "genuity_review_cases_per_page": genuity_review_cases_per_page,
        "routed_regions_per_page": routed_regions_per_page,
        "existing_extraction_cost_per_page_usd": existing_extraction_cost_per_page_usd,
        "implementation_cost_usd": implementation_cost_usd,
    }
    invalid = [key for key, value in nonnegative.items() if value < 0]
    if invalid:
        raise ValueError(f"ROI inputs must be non-negative: {', '.join(invalid)}")
    usage = vision_token_usage(pricing)["crop"]
    crop_cost = (
        usage["input_tokens"] * pricing["input_usd_per_million_tokens"]
        + usage["output_tokens"] * pricing["output_usd_per_million_tokens"]
    ) / 1_000_000
    human_case_cost = human_hourly_cost_usd * review_minutes_per_case / 60.0
    current_per_page = existing_extraction_cost_per_page_usd + current_review_cases_per_page * human_case_cost
    genuity_per_page = (
        existing_extraction_cost_per_page_usd
        + pricing["local_compute_usd_per_page"]
        + routed_regions_per_page * crop_cost
        + genuity_review_cases_per_page * human_case_cost
    )
    current_annual = current_per_page * annual_pages
    genuity_annual_run = genuity_per_page * annual_pages
    recurring_savings = current_annual - genuity_annual_run
    first_year_net = recurring_savings - implementation_cost_usd
    return {
        "scenario_type": "client_editable_overlay_roi_not_quote",
        "inputs": {"annual_pages": annual_pages, **nonnegative},
        "unit_costs": {
            "model_crop_cost_usd": round(crop_cost, 8),
            "human_review_case_cost_usd": round(human_case_cost, 6),
            "current_cost_per_page_usd": round(current_per_page, 6),
            "genuity_cost_per_page_usd": round(genuity_per_page, 6),
        },
        "annual": {
            "current_process_cost_usd": round(current_annual, 2),
            "genuity_run_cost_usd": round(genuity_annual_run, 2),
            "recurring_savings_usd": round(recurring_savings, 2),
            "first_year_net_savings_after_implementation_usd": round(first_year_net, 2),
            "recurring_savings_percent": round(recurring_savings / current_annual * 100, 2)
            if current_annual
            else None,
            "payback_months": round(implementation_cost_usd / recurring_savings * 12, 2)
            if recurring_savings > 0
            else None,
        },
        "warning": "Replace every default with measured pilot telemetry before using this as a commercial quote.",
    }
