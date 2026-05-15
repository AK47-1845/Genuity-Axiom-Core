"""Portable JSON data contracts for OCR adapters and decision exports."""

from __future__ import annotations


OCR_INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://genuity.io/contracts/existing-ocr-v1.schema.json",
    "title": "Genuity existing OCR adapter input",
    "type": "object",
    "required": ["page_count", "text", "fields"],
    "properties": {
        "adapter": {"type": "string"},
        "page_count": {"type": "integer", "minimum": 1},
        "text": {"type": "string"},
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "value", "confidence", "page", "region"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "value": {},
                    "unit": {"type": ["string", "null"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "page": {"type": "integer", "minimum": 1},
                    "region": {"type": "string", "minLength": 1},
                    "bbox": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "additionalProperties": True,
            },
        },
    },
    "additionalProperties": True,
}


FIELD_DECISION_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://genuity.io/contracts/field-decision-v1.schema.json",
    "title": "Genuity evidence-linked field decision",
    "type": "object",
    "required": [
        "field_id",
        "document_id",
        "name",
        "value",
        "original_extraction",
        "status",
        "acceptance",
        "evidence_ids",
        "method",
        "rationale",
        "safe_for_operational_use",
        "analytics_only",
    ],
    "properties": {
        "field_id": {"type": "string"},
        "document_id": {"type": "string"},
        "name": {"type": "string"},
        "value": {},
        "unit": {"type": ["string", "null"]},
        "original_extraction": {},
        "status": {"type": "string"},
        "acceptance": {"enum": ["ACCEPTED", "REVIEW", "NOT_ACCEPTED", "ANALYTICS_ONLY"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "critical": {"type": "boolean"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "method": {"type": "string"},
        "rationale": {"type": "string"},
        "rule_results": {"type": "array"},
        "alternatives_rejected": {"type": "array"},
        "safe_for_operational_use": {"type": "boolean"},
        "analytics_only": {"type": "boolean"},
        "requires_human_confirmation": {"type": "boolean"},
    },
    "additionalProperties": False,
}
