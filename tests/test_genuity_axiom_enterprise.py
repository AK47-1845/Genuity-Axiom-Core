"""Standard-library verification for the unified Axiom enterprise surface."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from genuity_axiom import (
    AcceptanceCriterion,
    ApprovalEvidence,
    AdapterDescriptor,
    AdapterPolicy,
    AdapterRegistry,
    AdapterRequest,
    AxiomEnterpriseEngine,
    DataBoundary,
    DriftMonitor,
    DifferentialPrivacyEvidence,
    EngineeringConstraintSet,
    EvaluationReport,
    GenuityAxiomEngine,
    IntendedUse,
    Modality,
    RareEventGenerator,
    RareEventSpec,
    Relationship,
    RelationalSynthesizer,
    ReleaseDecision,
    ReleasePolicy,
    ReleaseLifecycleRecord,
    RiskTier,
    Rule,
    SynthesisConfig,
    SyntheticReleaseGate,
    TimeSeriesBlockSynthesizer,
    UnstructuredPrivacyProcessor,
    ScenarioDefinition,
    assess_scenario,
    list_domain_packs,
    load_domain_pack,
    prepare_messy_table,
)
from genuity_axiom.compliance import ComplianceReport
from genuity_axiom.compliance import ComplianceGate
from genuity_axiom.evaluator import SyntheticEvaluator


class EnterpriseSurfaceTests(unittest.TestCase):
    def test_decimal_sensor_columns_are_not_misclassified_as_phone_numbers(self) -> None:
        data = pd.DataFrame({"x": np.linspace(0, 1, 100), "pressure": np.linspace(10, 20, 100)})
        cleaned, report = ComplianceGate().scrub(data)
        self.assertEqual(list(cleaned.columns), ["x", "pressure"])
        self.assertEqual(report.pii_columns, [])

    def test_business_features_are_not_dropped_by_broad_privacy_keywords(self) -> None:
        data = pd.DataFrame({
            "customer_id": [f"C-{i}" for i in range(30)],
            "customer_name": [f"Person {i}" for i in range(30)],
            "customer_income": np.arange(30) * 1000,
            "account_balance": np.arange(30) * 10,
            "product_name": ["turbine"] * 30,
        })
        cleaned, report = ComplianceGate().scrub(data)
        self.assertNotIn("customer_id", cleaned)
        self.assertNotIn("customer_name", cleaned)
        self.assertIn("customer_income", cleaned)
        self.assertIn("account_balance", cleaned)
        self.assertIn("product_name", cleaned)

    def test_nested_cells_require_explicit_privacy_aware_preparation(self) -> None:
        raw = pd.DataFrame({"payload": [{"contact": "a@example.com"}] * 30, "value": range(30)})
        with self.assertRaises(ValueError):
            GenuityAxiomEngine().synthesize(raw)
        prepared, report = prepare_messy_table(
            raw,
            privacy_processor=UnstructuredPrivacyProcessor(secret="project-test"),
        )
        self.assertEqual(report.nested_values_normalized["payload"], 30)
        self.assertNotIn("a@example.com", prepared.loc[0, "payload"])

    def test_builtin_domain_pack_can_be_discovered_and_validated(self) -> None:
        names = list_domain_packs()
        self.assertIn("predictive_maintenance_rare_events", names)
        for name in names:
            self.assertTrue(load_domain_pack(name)["pack_id"].startswith("axiom."))
        pack = load_domain_pack("predictive_maintenance_rare_events")
        self.assertEqual(pack["pack_id"], "axiom.predictive-maintenance.rare-events.v1")

    def test_drift_and_expiry_trigger_revalidation(self) -> None:
        reference = pd.DataFrame({"temperature": np.linspace(20, 30, 100), "state": ["a", "b"] * 50})
        current = pd.DataFrame({"temperature": np.linspace(60, 80, 100), "state": ["c"] * 100})
        drift = DriftMonitor().compare(reference, current)
        self.assertTrue(drift.requires_revalidation)

        result = GenuityAxiomEngine().synthesize(
            pd.DataFrame({"x": np.linspace(0, 1, 100), "y": np.linspace(1, 2, 100)}),
            config=SynthesisConfig(n_samples=20, risk_tier="sandbox"),
        )
        lifecycle = ReleaseLifecycleRecord.from_manifest(result.manifest, validity_days=1)
        after_expiry = datetime.fromisoformat(lifecycle.expires_at) + timedelta(seconds=1)
        assessment = lifecycle.assess(now=after_expiry)
        self.assertFalse(assessment.usable)
        self.assertIn("release expired", assessment.reasons)

    def test_scenario_acceptance_requires_metrics_and_human_validators(self) -> None:
        scenario = ScenarioDefinition(
            "bearing-hot-01",
            "Bearing overheating",
            "Validate alarm coverage",
            "Temperature above approved boundary under load",
            "Alarm occurs before shutdown boundary",
            "high",
            ("reliability_owner",),
            (AcceptanceCriterion("constraint_pass_rate", "ge", 1.0),),
        )
        assessment = assess_scenario(
            scenario,
            metrics={"constraint_pass_rate": 1.0},
            validator_approvals={},
        )
        self.assertFalse(assessment.approved)

    def test_sensitive_external_adapter_is_rejected_by_policy(self) -> None:
        class DummyAdapter:
            descriptor = AdapterDescriptor(
                "external-video",
                "1.0",
                (Modality.VIDEO,),
                ("generate",),
                DataBoundary.EXTERNAL_SERVICE,
                provider_retains_input=False,
            )

        registry = AdapterRegistry()
        registry.register(DummyAdapter())
        with self.assertRaises(PermissionError):
            registry.resolve(
                "external-video",
                modality="video",
                request=AdapterRequest("generate", sensitive=True),
                policy=AdapterPolicy(
                    allowed_boundaries=(DataBoundary.EXTERNAL_SERVICE,),
                    prohibit_external_for_sensitive=True,
                ),
            )

    def test_capability_registry_is_truthful(self) -> None:
        engine = AxiomEnterpriseEngine()
        self.assertEqual(engine.capabilities.get("tabular").level.value, "native")
        self.assertEqual(engine.capabilities.get("image").level.value, "adapter_required")
        with self.assertRaises(NotImplementedError):
            engine.require_generation_capability("video")

    def test_hard_release_gate_cannot_average_away_record_copying(self) -> None:
        evaluation = EvaluationReport(
            overall_score=0.99,
            similarity_score=0.99,
            correlation_score=0.99,
            privacy_score=0.99,
            missingness_score=1.0,
            range_score=1.0,
            membership_attack_score=1.0,
            holdout_similarity_gap=0.0,
            constraint_score=1.0,
            details={"privacy": {"exact_duplicate_rate": 0.2}},
        )
        compliance = ComplianceReport(["x"], ["x"])
        result = SyntheticReleaseGate().assess(
            evaluation=evaluation,
            compliance=compliance,
            policy=ReleasePolicy.for_tier(RiskTier.INTERNAL),
            holdout_independent=True,
        )
        self.assertEqual(result.decision, ReleaseDecision.BLOCKED)
        self.assertFalse(next(c for c in result.checks if c.name == "exact_duplicate_rate").passed)

    def test_invalid_release_policy_fails_closed(self) -> None:
        evaluation = EvaluationReport(
            0.99, 0.99, 0.99, 0.99,
            missingness_score=1.0,
            range_score=1.0,
            membership_attack_score=1.0,
            holdout_similarity_gap=0.0,
            constraint_score=1.0,
            details={"privacy": {"exact_duplicate_rate": 0.0}},
        )
        release = SyntheticReleaseGate().assess(
            evaluation=evaluation,
            compliance=ComplianceReport(["x"], ["x"]),
            policy=ReleasePolicy(min_privacy_score=-1.0),
            holdout_independent=True,
        )
        self.assertEqual(release.decision, ReleaseDecision.BLOCKED)
        self.assertFalse(next(c for c in release.checks if c.name == "release_policy_valid").passed)

    def test_failed_compliance_precheck_is_a_release_blocker(self) -> None:
        evaluation = EvaluationReport(
            0.99, 0.99, 0.99, 0.99,
            missingness_score=1.0,
            range_score=1.0,
            membership_attack_score=1.0,
            holdout_similarity_gap=0.0,
            constraint_score=1.0,
            details={"privacy": {"exact_duplicate_rate": 0.0}},
        )
        compliance = ComplianceReport(["x"], ["x"], warnings=["BLOCKER: source too small"])
        result = SyntheticReleaseGate().assess(
            evaluation=evaluation,
            compliance=compliance,
            policy=ReleasePolicy.for_tier("internal"),
            holdout_independent=True,
        )
        self.assertEqual(result.decision, ReleaseDecision.BLOCKED)
        self.assertFalse(next(c for c in result.checks if c.name == "compliance_precheck").passed)

    def test_formal_dp_requires_structured_evidence(self) -> None:
        invalid = DifferentialPrivacyEvidence(
            mechanism="DP-SGD",
            epsilon=0,
            delta=1e-6,
            accountant="RDP accountant",
            adjacency_definition="one row",
            clipping_or_sensitivity="L2 clip 1.0",
            composition_ledger_reference="ledger-1",
            verified_by="privacy-owner",
            verified_at="2026-08-13T00:00:00Z",
        )
        self.assertFalse(invalid.valid)
        valid = DifferentialPrivacyEvidence(
            mechanism="DP-SGD",
            epsilon=3.0,
            delta=1e-6,
            accountant="RDP accountant",
            adjacency_definition="one row",
            clipping_or_sensitivity="L2 clip 1.0",
            composition_ledger_reference="ledger-1",
            verified_by="privacy-owner",
            verified_at="2026-08-13T00:00:00Z",
        )
        self.assertTrue(valid.valid)

    def test_approvals_are_named_scoped_records_not_booleans(self) -> None:
        approval = ApprovalEvidence(
            role="domain_owner",
            approver="Dr Domain Owner",
            decision="approved",
            approved_at="2026-08-13T00:00:00Z",
            scope="scenario pump-cavitation-01, run abc",
            evidence_reference="LTTS-REVIEW-123",
        )
        self.assertTrue(approval.valid)

    def test_external_release_requires_a_named_recipient(self) -> None:
        df = pd.DataFrame({"x": np.linspace(0, 1, 100), "y": np.linspace(1, 3, 100)})
        result = GenuityAxiomEngine().synthesize(
            df,
            config=SynthesisConfig(
                n_samples=20,
                risk_tier="external",
                intended_use=IntendedUse(purpose="external model validation"),
            ),
        )
        check = next(c for c in result.release.checks if c.name == "intended_use_complete")
        self.assertFalse(check.passed)
        self.assertEqual(result.release.decision, ReleaseDecision.BLOCKED)

    def test_unavailable_membership_evidence_is_not_reported_as_perfect(self) -> None:
        train = pd.DataFrame({"state": ["a", "b"] * 10})
        holdout = pd.DataFrame({"state": ["a", "b"] * 5})
        synthetic = pd.DataFrame({"state": ["a", "b"] * 5})
        report = SyntheticEvaluator().evaluate(holdout, synthetic, train_data=train)
        self.assertIsNone(report.membership_attack_score)

    def test_wrong_modality_evidence_is_a_release_blocker(self) -> None:
        evaluation = EvaluationReport(
            0.99, 0.99, 0.99, 0.99,
            missingness_score=1.0,
            range_score=1.0,
            membership_attack_score=1.0,
            holdout_similarity_gap=0.0,
            constraint_score=1.0,
            details={"privacy": {"exact_duplicate_rate": 0.0}},
        )
        result = SyntheticReleaseGate().assess(
            evaluation=evaluation,
            compliance=ComplianceReport(["x"], ["x"]),
            policy=ReleasePolicy.for_tier("internal"),
            holdout_independent=True,
            modality_appropriate_evaluation=False,
        )
        self.assertEqual(result.decision, ReleaseDecision.BLOCKED)

    def test_warning_constraints_trigger_review_not_safety_block(self) -> None:
        constraints = EngineeringConstraintSet().add_expression(
            "expert_plausibility_review", "x < 0", severity="warning"
        )
        constraint_report = constraints.validate(pd.DataFrame({"x": [1, 2, 3]}))
        self.assertTrue(constraint_report.passed)
        self.assertEqual(constraint_report.warning_violations, 3)
        evaluation = EvaluationReport(
            0.99, 0.99, 0.99, 0.99,
            missingness_score=1.0,
            range_score=1.0,
            membership_attack_score=1.0,
            holdout_similarity_gap=0.0,
            constraint_score=1.0,
            details={"privacy": {"exact_duplicate_rate": 0.0}},
        )
        release = SyntheticReleaseGate().assess(
            evaluation=evaluation,
            compliance=ComplianceReport(["x"], ["x"]),
            policy=ReleasePolicy.for_tier("internal"),
            holdout_independent=True,
            constraint_warning_count=3,
        )
        self.assertEqual(release.decision, ReleaseDecision.REVIEW)

    def test_invalid_constraint_definitions_fail_at_authoring_time(self) -> None:
        with self.assertRaises(ValueError):
            EngineeringConstraintSet().add_bound("pressure", min_value=10, max_value=5)
        constraints = EngineeringConstraintSet().add_bound("pressure", min_value=0)
        with self.assertRaises(ValueError):
            constraints.add(Rule("pressure_ge_0", "pressure", "ge", 1))
        with self.assertRaises(ValueError):
            EngineeringConstraintSet().add_expression(
                "malicious", "__import__('os').system('whoami')"
            )

    def test_unstructured_replacement_and_leakage_audit(self) -> None:
        processor = UnstructuredPrivacyProcessor(secret="test")
        output, report = processor.transform_text("Contact a@example.com or +91 98765 43210")
        self.assertNotIn("a@example.com", output)
        self.assertTrue(report.passed)
        audit = processor.audit_pair(["confidential turbine incident report"], ["confidential turbine incident report"])
        self.assertEqual(audit.exact_document_overlap, 1)
        self.assertFalse(audit.passed)

    def test_temporal_baseline_preserves_monotonic_sequences(self) -> None:
        df = pd.DataFrame({
            "asset": ["A"] * 20,
            "time": pd.date_range("2026-01-01", periods=20, freq="h"),
            "temperature": np.linspace(40, 90, 20),
        })
        data, report = TimeSeriesBlockSynthesizer(block_length=4).synthesize(
            df, time_col="time", entity_col="asset", n_entities=2, rows_per_entity=12
        )
        self.assertEqual(len(data), 24)
        self.assertEqual(report.monotonic_entities, 2)
        self.assertEqual(report.duplicate_timestamps, 0)
        self.assertTrue(report.passed)

    def test_temporal_validation_reports_invalid_timestamps(self) -> None:
        report = TimeSeriesBlockSynthesizer().validate(
            pd.DataFrame({"time": ["2026-01-01", "not-a-time"]}),
            time_col="time",
        )
        self.assertEqual(report.invalid_timestamps, 1)
        self.assertFalse(report.passed)

    def test_relational_baseline_enforces_primary_and_foreign_keys(self) -> None:
        tables = {
            "customers": pd.DataFrame({"customer_id": [1, 2, 3], "segment": ["a", "b", "a"]}),
            "orders": pd.DataFrame({"order_id": [10, 11, 12, 13], "customer_id": [1, 1, 2, 3], "value": [5, 9, 3, 8]}),
        }
        keys = {"customers": "customer_id", "orders": "order_id"}
        rels = [Relationship("customers", "customer_id", "orders", "customer_id")]
        output, report = RelationalSynthesizer().synthesize(tables, primary_keys=keys, relationships=rels)
        self.assertTrue(report.passed)
        self.assertTrue(set(output["orders"]["customer_id"]).issubset(set(output["customers"]["customer_id"])))

    def test_relational_baseline_rejects_empty_source_tables(self) -> None:
        with self.assertRaises(ValueError):
            RelationalSynthesizer().synthesize(
                {"assets": pd.DataFrame({"asset_id": []})},
                primary_keys={"assets": "asset_id"},
                relationships=[],
            )

    def test_rare_event_generation_respects_conditions_and_constraints(self) -> None:
        df = pd.DataFrame({"temperature": np.linspace(0, 100, 101), "mode": ["normal"] * 101})
        constraints = EngineeringConstraintSet().add_bound("temperature", min_value=0, max_value=105)
        output, report = RareEventGenerator().generate(
            df,
            n_samples=10,
            spec=RareEventSpec("hot-boundary", {"temperature": {"ge": 80}}, ("temperature",), "high"),
            constraints=constraints,
        )
        self.assertEqual(len(output), 10)
        self.assertTrue((output["temperature"] >= 80).all())
        self.assertEqual(report.constraint_pass_rate, 1.0)

    def test_rare_event_novelty_threshold_is_enforced(self) -> None:
        df = pd.DataFrame({"value": np.linspace(0, 1, 50)})
        output, report = RareEventGenerator().generate(
            df,
            n_samples=5,
            spec=RareEventSpec(
                "unreachable-novelty",
                tail_columns=("value",),
                tail="high",
                min_novelty_distance=100.0,
            ),
        )
        self.assertTrue(output.empty)
        self.assertEqual(report.novelty_pass_rate, 0.0)

    def test_tabular_run_emits_manifest_and_release_assessment(self) -> None:
        rng = np.random.default_rng(7)
        df = pd.DataFrame({
            "temperature": rng.normal(60, 5, 100),
            "pressure": rng.normal(10, 1, 100),
            "state": rng.choice(["normal", "warning"], 100),
        })
        result = GenuityAxiomEngine().synthesize(
            df, config=SynthesisConfig(n_samples=50, risk_tier="internal", random_state=9)
        )
        self.assertIsNotNone(result.release)
        self.assertIsNotNone(result.manifest)
        self.assertEqual(result.manifest.output_rows, 50)
        self.assertEqual(result.manifest.configuration["risk_tier"], "internal")
        self.assertEqual(result.to_report()["manifest"]["run_id"], result.manifest.run_id)

    def test_conditions_are_enforced_and_unsupported_conditions_fail_closed(self) -> None:
        df = pd.DataFrame({
            "temperature": np.linspace(0, 100, 100),
            "state": ["normal"] * 80 + ["warning"] * 20,
        })
        result = GenuityAxiomEngine().synthesize(
            df,
            config=SynthesisConfig(
                n_samples=30,
                conditions={"temperature": {"ge": 80}, "state": "warning"},
                risk_tier="sandbox",
            ),
        )
        self.assertTrue((result.data["temperature"] >= 80).all())
        self.assertTrue((result.data["state"] == "warning").all())
        self.assertEqual(result.evaluation.details["condition_match_rate"], 1.0)
        with self.assertRaises(ValueError):
            GenuityAxiomEngine().synthesize(
                df,
                config=SynthesisConfig(conditions={"state": "impossible"}),
            )


if __name__ == "__main__":
    unittest.main()
