"""Command line entrypoint for Genuity Axiom."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .approvals import ApprovalEvidence
from .engine import GenuityAxiomEngine, SynthesisConfig
from .governance import IntendedUse
from .privacy_evidence import DifferentialPrivacyEvidence


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="genuity-axiom",
        description="Generate and evidence-gate synthetic engineering data from CSV.",
    )
    parser.add_argument("input_csv", help="Path to the real input CSV")
    parser.add_argument("output_csv", help="Path to write the synthetic CSV")
    parser.add_argument("--rows", type=int, default=None, help="Number of rows to generate")
    parser.add_argument("--target", default=None, help="Optional target column")
    parser.add_argument("--time-col", default=None, help="Optional time column")
    parser.add_argument("--entity-col", default=None, help="Optional entity column")
    parser.add_argument(
        "--privacy",
        default="standard",
        choices=["standard", "strict", "dp-ready"],
        help="Privacy gate level",
    )
    parser.add_argument(
        "--risk-tier",
        default="internal",
        choices=["sandbox", "internal", "external", "regulated"],
        help="Non-compensating release policy tier",
    )
    parser.add_argument("--purpose", default="internal synthetic-data evaluation")
    parser.add_argument("--recipient", default=None)
    parser.add_argument("--approvals-json", default=None, help="List of scoped, named human approval records")
    parser.add_argument("--dp-evidence-json", default=None, help="Structured formal-DP evidence JSON; a boolean assertion is not accepted")
    parser.add_argument(
        "--allow-blocked-export",
        action="store_true",
        help="Write a blocked artifact for sandbox investigation; never implies release approval",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional JSON report path. Defaults to <output_csv>.report.json",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv)
    dp_evidence = None
    if args.dp_evidence_json:
        payload = json.loads(Path(args.dp_evidence_json).read_text(encoding="utf-8"))
        dp_evidence = DifferentialPrivacyEvidence.from_dict(payload)
        if not dp_evidence.valid:
            parser.error("invalid DP evidence: " + "; ".join(dp_evidence.issues()))
    approvals: list[ApprovalEvidence] = []
    if args.approvals_json:
        payload = json.loads(Path(args.approvals_json).read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            parser.error("approvals JSON must contain a list")
        approvals = [ApprovalEvidence.from_dict(item) for item in payload]
        issues = [f"record {i}: {'; '.join(item.issues())}" for i, item in enumerate(approvals) if not item.valid]
        if issues:
            parser.error("invalid approval evidence: " + " | ".join(issues))

    config = SynthesisConfig(
        n_samples=args.rows,
        target_col=args.target,
        time_col=args.time_col,
        entity_col=args.entity_col,
        privacy_level=args.privacy,
        risk_tier=args.risk_tier,
        intended_use=IntendedUse(purpose=args.purpose, recipient=args.recipient),
        approvals=approvals,
        formal_dp_evidence=dp_evidence,
    )
    result = GenuityAxiomEngine().synthesize(df, config=config)

    output_path = Path(args.output_csv)
    report_path = Path(args.report) if args.report else output_path.with_suffix(".report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result.to_report(), indent=2), encoding="utf-8")

    blocked = result.release is not None and result.release.decision.value == "blocked"
    if not blocked or args.allow_blocked_export:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.data.to_csv(output_path, index=False)
        print(f"Wrote {len(result.data)} rows to {output_path}")
    else:
        print("Synthetic artifact was not exported because a release gate is blocked.")

    print(f"Generator: {result.generator_name}")
    print(f"Overall score: {result.evaluation.overall_score:.3f}")
    print(f"Release: {result.release.decision.value if result.release else 'not_evaluated'}")
    if result.release and not result.release.passed:
        failed = [check for check in result.release.checks if not check.passed]
        for check in failed:
            print(f"  - {check.severity}: {check.name} observed={check.observed!r} required={check.required!r}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
