"""Fail-closed provenance and policy integrity checks."""

from __future__ import annotations

import re
from typing import Any

from .models import DocumentRecord, EvidenceRef, FieldDecision


def build_integrity_report(
    documents: list[DocumentRecord],
    decisions: list[FieldDecision],
    evidence: list[EvidenceRef],
    exceptions: list[dict[str, Any]],
    graph: dict[str, Any],
    domain_pack: dict[str, Any],
) -> dict[str, Any]:
    evidence_ids = [item.evidence_id for item in evidence]
    evidence_set = set(evidence_ids)
    document_ids = [doc.document_id for doc in documents]
    field_ids = [item.field_id for item in decisions]
    document_hashes = {doc.document_id: doc.content_hash for doc in documents}
    checks: list[dict[str, Any]] = []

    def add(check_id: str, passed: bool, details: Any) -> None:
        checks.append(
            {"check_id": check_id, "result": "PASS" if passed else "FAIL", "details": details}
        )

    add(
        "unique_evidence_ids",
        len(evidence_ids) == len(evidence_set),
        {"total": len(evidence_ids), "unique": len(evidence_set)},
    )
    add(
        "unique_document_ids",
        len(document_ids) == len(set(document_ids)),
        {"total": len(document_ids), "unique": len(set(document_ids))},
    )
    add(
        "unique_field_ids",
        len(field_ids) == len(set(field_ids)),
        {"total": len(field_ids), "unique": len(set(field_ids))},
    )
    unresolved_field_evidence = sorted(
        {ref for item in decisions for ref in item.evidence_ids if ref not in evidence_set}
    )
    add("all_field_evidence_resolves", not unresolved_field_evidence, unresolved_field_evidence)
    accepted_without_evidence = sorted(
        item.field_id for item in decisions if item.acceptance == "ACCEPTED" and not item.evidence_ids
    )
    add("accepted_fields_have_evidence", not accepted_without_evidence, accepted_without_evidence)
    unsafe_accepted = sorted(
        item.field_id
        for item in decisions
        if item.acceptance == "ACCEPTED" and not item.safe_for_operational_use
    )
    add("accepted_fields_are_operationally_safe", not unsafe_accepted, unsafe_accepted)
    synthetic_accepted = sorted(
        item.field_id
        for item in decisions
        if item.acceptance == "ACCEPTED" and item.analytics_only
    )
    add("analytics_imputations_not_accepted", not synthetic_accepted, synthetic_accepted)
    unsupported_reconstructions = sorted(
        item.field_id
        for item in decisions
        if item.acceptance == "ACCEPTED"
        and item.status not in {"OBSERVED"}
        and not item.rule_results
    )
    add(
        "accepted_reconstructions_have_rule_support",
        not unsupported_reconstructions,
        unsupported_reconstructions,
    )
    review_marked_safe = sorted(
        item.field_id
        for item in decisions
        if item.acceptance in {"REVIEW", "NOT_ACCEPTED", "ANALYTICS_ONLY"}
        and item.safe_for_operational_use
    )
    add("nonaccepted_fields_not_marked_safe", not review_marked_safe, review_marked_safe)
    invalid_hashes = sorted(
        item.evidence_id
        for item in evidence
        if not re.fullmatch(r"[0-9a-f]{64}", item.content_hash)
    )
    add("evidence_content_hashes_are_sha256", not invalid_hashes, invalid_hashes)
    mismatched_hashes = sorted(
        item.evidence_id
        for item in evidence
        if document_hashes.get(item.document_id) != item.content_hash
    )
    add("evidence_hash_matches_document", not mismatched_hashes, mismatched_hashes)
    graph_refs = {
        ref for edge in graph.get("edges", []) for ref in edge.get("evidence", [])
    }
    missing_graph_refs = sorted(graph_refs - evidence_set)
    add("graph_evidence_resolves", not missing_graph_refs, missing_graph_refs)
    exception_refs = {
        ref for item in exceptions for ref in item.get("evidence_ids", [])
    }
    missing_exception_refs = sorted(exception_refs - evidence_set)
    add("exception_evidence_resolves", not missing_exception_refs, missing_exception_refs)
    unsafe_exceptions = sorted(
        item["exception_id"] for item in exceptions if item.get("safe_for_operational_use")
    )
    add("exceptions_are_blocked_from_operational_use", not unsafe_exceptions, unsafe_exceptions)
    expected_exception_fields = {
        item.field_id
        for item in decisions
        if item.acceptance in {"REVIEW", "NOT_ACCEPTED", "ANALYTICS_ONLY"}
    }
    actual_exception_fields = [item.get("field_id") for item in exceptions]
    exception_coverage_ok = (
        set(actual_exception_fields) == expected_exception_fields
        and len(actual_exception_fields) == len(set(actual_exception_fields))
    )
    add(
        "all_nonaccepted_fields_appear_once_in_exception_queue",
        exception_coverage_ok,
        {
            "missing": sorted(expected_exception_fields - set(actual_exception_fields)),
            "unexpected": sorted(set(actual_exception_fields) - expected_exception_fields),
            "duplicate_count": len(actual_exception_fields) - len(set(actual_exception_fields)),
        },
    )
    dedupe_keys = [item.get("dedupe_key") for item in exceptions]
    invalid_exception_routing = sorted(
        item["exception_id"]
        for item in exceptions
        if not item.get("reason_code")
        or not item.get("suggested_owner")
        or not isinstance(item.get("sla_hours"), int)
        or item["sla_hours"] <= 0
        or not item.get("dedupe_key")
    )
    add(
        "exceptions_have_operational_routing_metadata",
        not invalid_exception_routing,
        invalid_exception_routing,
    )
    add(
        "exception_dedupe_keys_are_unique",
        len(dedupe_keys) == len(set(dedupe_keys)),
        {"total": len(dedupe_keys), "unique": len(set(dedupe_keys))},
    )
    duplicate_errors = []
    by_id = {doc.document_id: doc for doc in documents}
    for doc in documents:
        if doc.duplicate_of:
            original = by_id.get(doc.duplicate_of)
            if original is None or original.content_hash != doc.content_hash:
                duplicate_errors.append(doc.document_id)
    add("duplicates_share_content_hash", not duplicate_errors, duplicate_errors)
    unknown_accepted = sorted(
        item.field_id
        for doc in documents
        if doc.document_type == "unknown"
        for item in doc.fields
        if item.acceptance == "ACCEPTED"
    )
    add("unknown_document_fields_not_accepted", not unknown_accepted, unknown_accepted)
    permitted_methods = set(domain_pack.get("permitted_reconstruction_methods", []))
    disallowed_methods = sorted(
        item.field_id
        for item in decisions
        if item.acceptance == "ACCEPTED"
        and item.status != "OBSERVED"
        and item.method not in permitted_methods
    )
    add(
        "accepted_reconstruction_method_permitted_by_domain_pack",
        not disallowed_methods,
        {"disallowed_fields": disallowed_methods, "permitted_methods": sorted(permitted_methods)},
    )
    imputation_policy_ok = all(
        not item.analytics_only
        or "analytics_only" in domain_pack.get("permitted_imputation_purposes", [])
        for item in decisions
    )
    add(
        "analytics_imputation_purpose_permitted_by_domain_pack",
        imputation_policy_ok,
        domain_pack.get("permitted_imputation_purposes", []),
    )

    passed = sum(item["result"] == "PASS" for item in checks)
    return {
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
    }


def enforce_integrity(report: dict[str, Any]) -> None:
    if report["status"] != "PASS":
        failures = [item["check_id"] for item in report["checks"] if item["result"] == "FAIL"]
        raise RuntimeError(f"Fail-closed integrity gate rejected output: {', '.join(failures)}")
