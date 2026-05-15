"""Command-line entry point for existing OCR reconciliation and the complete demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_domain_pack, resolve_default_pack
from .batch import run_packet_batch
from .economics import estimate_customer_roi
from .evaluation import evaluate_decisions
from .pipeline import ReconciliationPipeline, export_result, run_demo
from .review_ledger import create_review_ledger, verify_review_ledger
from .verification import verify_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="genuity-reconcile",
        description="Turn existing OCR output into evidence-linked, validated industrial records.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="Generate and process the complete non-confidential demo packet")
    demo.add_argument("--output-dir", default="genuity_demo_output")
    demo.add_argument("--domain-pack", default=str(resolve_default_pack()))
    demo.add_argument("--no-vlm", action="store_true", help="Do not invoke even the simulated crop-only VLM adapter")
    run = subparsers.add_parser("run", help="Process a folder of existing-OCR JSON files")
    run.add_argument("--ocr-dir", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--domain-pack", default=str(resolve_default_pack()))
    run.add_argument("--allow-vlm", action="store_true", help="Permit configured crop-only VLM routing")
    run.add_argument("--cache-dir", default=None, help="Optional persistent content-addressed model-result cache")
    batch = subparsers.add_parser("batch", help="Process isolated packet subfolders and aggregate their metrics")
    batch.add_argument("--ocr-root", required=True, help="Root containing one OCR JSON subfolder per connected chain")
    batch.add_argument("--output-root", required=True)
    batch.add_argument("--domain-pack", default=str(resolve_default_pack()))
    batch.add_argument("--allow-vlm", action="store_true")
    batch.add_argument("--cache-root", default=None)
    verify = subparsers.add_parser("verify", help="Verify artifact hashes, semantic fingerprint, provenance, and SQLite")
    verify.add_argument("--output-dir", required=True)
    estimate = subparsers.add_parser("estimate", help="Calculate an editable customer overlay ROI scenario")
    estimate.add_argument("--pages", type=int, required=True, help="Annual page volume")
    estimate.add_argument("--human-hourly-cost", type=float, default=45.0)
    estimate.add_argument("--review-minutes", type=float, default=1.5)
    estimate.add_argument("--current-review-cases-per-page", type=float, default=1.0)
    estimate.add_argument("--genuity-review-cases-per-page", type=float, default=0.416667)
    estimate.add_argument("--routed-regions-per-page", type=float, default=0.083333)
    estimate.add_argument("--existing-extraction-cost-per-page", type=float, default=0.0015)
    estimate.add_argument("--implementation-cost", type=float, default=100000.0)
    estimate.add_argument("--domain-pack", default=str(resolve_default_pack()))
    evaluate = subparsers.add_parser("evaluate", help="Evaluate decisions against a client blind-truth CSV")
    evaluate.add_argument("--decisions", required=True)
    evaluate.add_argument("--truth-csv", required=True)
    evaluate.add_argument("--output", default=None)
    evaluate.add_argument("--relative-tolerance", type=float, default=1e-6)
    evaluate.add_argument("--absolute-tolerance", type=float, default=1e-6)
    review = subparsers.add_parser("review-ledger", help="Validate review resolutions and create a hash-chained ledger")
    review.add_argument("--review-queue", required=True)
    review.add_argument("--resolutions-csv", required=True)
    review.add_argument("--output", required=True)
    verify_review = subparsers.add_parser("verify-review-ledger", help="Verify a review ledger and its source queue")
    verify_review.add_argument("--ledger", required=True)
    verify_review.add_argument("--review-queue", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "batch":
        report = run_packet_batch(
            args.ocr_root,
            args.output_root,
            domain_pack=args.domain_pack,
            allow_vlm=args.allow_vlm,
            cache_root=args.cache_root,
        )
        print(json.dumps(report, indent=2))
        return
    if args.command == "review-ledger":
        ledger = create_review_ledger(args.review_queue, args.resolutions_csv, args.output)
        print(json.dumps({"status": "PASS", "event_count": ledger["event_count"], "output": str(Path(args.output).resolve())}, indent=2))
        return
    if args.command == "verify-review-ledger":
        report = verify_review_ledger(args.ledger, args.review_queue)
        print(json.dumps(report, indent=2))
        if report["status"] != "PASS":
            raise SystemExit(1)
        return
    if args.command == "evaluate":
        report = evaluate_decisions(
            args.decisions,
            args.truth_csv,
            relative_tolerance=args.relative_tolerance,
            absolute_tolerance=args.absolute_tolerance,
        )
        rendered = json.dumps(report, indent=2)
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        print(rendered)
        return
    if args.command == "estimate":
        pack = load_domain_pack(args.domain_pack)
        report = estimate_customer_roi(
            pack["pricing"],
            annual_pages=args.pages,
            human_hourly_cost_usd=args.human_hourly_cost,
            review_minutes_per_case=args.review_minutes,
            current_review_cases_per_page=args.current_review_cases_per_page,
            genuity_review_cases_per_page=args.genuity_review_cases_per_page,
            routed_regions_per_page=args.routed_regions_per_page,
            existing_extraction_cost_per_page_usd=args.existing_extraction_cost_per_page,
            implementation_cost_usd=args.implementation_cost,
        )
        print(json.dumps(report, indent=2))
        return
    if args.command == "verify":
        report = verify_output(args.output_dir)
        print(json.dumps(report, indent=2))
        if report["status"] != "PASS":
            raise SystemExit(1)
        return
    if args.command == "demo":
        result = run_demo(args.output_dir, domain_pack=args.domain_pack, allow_vlm=not args.no_vlm)
    else:
        result = ReconciliationPipeline(
            args.domain_pack, allow_vlm=args.allow_vlm, cache_dir=args.cache_dir
        ).run(args.ocr_dir)
        export_result(result, Path(args.output_dir))
    selected = result.cost_report["comparison"][-1]
    print("Genuity industrial reconciliation complete")
    print(f"Ten-behaviour scorecard: {'PASS' if result.scorecard['all_ten_behaviours_proved'] else 'FAIL'}")
    print(f"Pages: {result.metrics['pages_processed']}")
    print(f"Accepted / verified: {result.metrics['automatically_accepted_fields']} / {result.metrics['verified_fields']}")
    print(f"External regions: {result.metrics['external_regions_routed']}")
    print(f"Human review cases: {result.metrics['human_review_cases']}")
    print(f"Estimated batch cost: ${selected['estimated_total_batch_cost_usd']:.4f}")
    print(f"Outputs: {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()
