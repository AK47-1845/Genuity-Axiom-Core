# Axiom LTTS API Recipes

These recipes are starting points, not automatic approval. Replace example thresholds with client/domain-owner values and keep client data out of shared packs.

## 1. Tabular engineering augmentation

For JSON/list-valued cells, first run `prepare_messy_table` with a project-specific `UnstructuredPrivacyProcessor`; the tabular engine rejects nested objects rather than silently misprocessing them.

```python
from genuity_axiom import UnstructuredPrivacyProcessor, prepare_messy_table

source_df, preparation = prepare_messy_table(
    raw_df,
    privacy_processor=UnstructuredPrivacyProcessor(secret=project_secret),
)
```

```python
from genuity_axiom import EngineeringConstraintSet, GenuityAxiomEngine, IntendedUse, SynthesisConfig

constraints = (
    EngineeringConstraintSet()
    .add_bound("pressure_bar", min_value=0, max_value=250)
    .add_bound("temperature_c", min_value=-40, max_value=180)
    .add_expression("approved_envelope", "pressure_bar <= 220 - 0.2 * temperature_c")
)

result = GenuityAxiomEngine().synthesize(
    source_df,
    config=SynthesisConfig(
        n_samples=5_000,
        target_col="failure_mode",
        constraints=constraints,
        privacy_level="strict",
        quality_mode="max",
        risk_tier="internal",
        intended_use=IntendedUse(
            purpose="offline failure-model development",
            users=["LTTS data science", "client reliability engineering"],
            recipient="approved client project environment",
            prohibited_uses=["live control", "automatic safety actuation"],
            retention_days=90,
        ),
    ),
)

if result.release.passed:
    synthetic_df = result.data
else:
    print(result.release.to_dict())
```

For a sequence, relational database or document collection, do not treat a tabular approval as modality-appropriate. Axiom now blocks that mistake explicitly.

## 2. Constraint-aware rare boundary cases

```python
from genuity_axiom import RareEventGenerator, RareEventSpec

spec = RareEventSpec(
    name="high-temperature-high-load",
    conditions={"load_pct": {"ge": 85}},
    tail_columns=("temperature_c", "vibration_rms"),
    tail="high",
    quantile=0.95,
    min_novelty_distance=0.10,
    oversample_factor=20,
)

cases, report = RareEventGenerator(random_state=42).generate(
    source_df,
    n_samples=200,
    spec=spec,
    constraints=constraints,
)
print(report.to_dict())
```

Then test the cases in the actual model/simulator and use a `ScenarioDefinition` for business acceptance.

## 3. Scenario-as-code

```python
from genuity_axiom import AcceptanceCriterion, ScenarioDefinition, assess_scenario

scenario = ScenarioDefinition(
    scenario_id="pump-cavitation-01",
    name="Incipient cavitation under high demand",
    buyer_decision="Validate warning lead time before deployment",
    operational_definition="Approved low-inlet-pressure and high-flow combination",
    expected_outcome="Warning at least 120 seconds before trip boundary",
    severity="high",
    required_validators=("process_owner", "model_owner"),
    acceptance=(
        AcceptanceCriterion("constraint_pass_rate", "ge", 1.0),
        AcceptanceCriterion("recall_at_governed_fpr", "ge", 0.85),
        AcceptanceCriterion("median_lead_time_seconds", "ge", 120),
    ),
    prohibited_uses=("live actuator testing",),
)

assessment = assess_scenario(
    scenario,
    metrics={
        "constraint_pass_rate": 1.0,
        "recall_at_governed_fpr": 0.88,
        "median_lead_time_seconds": 145,
    },
    validator_approvals={"process_owner": True, "model_owner": True},
)
```

## 4. Time-series baseline

```python
from genuity_axiom import TimeSeriesBlockSynthesizer

episodes, temporal_report = TimeSeriesBlockSynthesizer(
    block_length=48,
    random_state=42,
).synthesize(
    telemetry_df,
    time_col="timestamp",
    entity_col="asset_id",
    n_entities=100,
    rows_per_entity=1_000,
)
```

This preserves short local blocks and rebuilds monotonic timestamps. It does not prove long-range dynamics, control response or causal physics. Use an approved sequence/simulator adapter when those matter.

## 5. Relational/test-database baseline

```python
from genuity_axiom import Relationship, RelationalSynthesizer

relationships = [
    Relationship("assets", "asset_id", "work_orders", "asset_id"),
    Relationship("work_orders", "work_order_id", "events", "work_order_id"),
]

synthetic_tables, integrity = RelationalSynthesizer(random_state=42).synthesize(
    {"assets": assets, "work_orders": work_orders, "events": events},
    primary_keys={
        "assets": "asset_id",
        "work_orders": "work_order_id",
        "events": "event_id",
    },
    relationships=relationships,
    scale=2.0,
)
assert integrity.passed
```

The baseline preserves integrity but not full cross-table statistical dependence.

## 6. Logs and documents

```python
from genuity_axiom import UnstructuredPrivacyProcessor

processor = UnstructuredPrivacyProcessor(
    secret=project_secret_from_approved_secret_manager,
    strategy="replace",
)
clean_documents, privacy_report = processor.transform(document_payload)
leakage = processor.audit_pair(source_texts, generated_texts, max_ngram=12)
```

Use NER/OCR/layout adapters for names, proprietary entities, drawings and scanned documents. Never hard-code a production pseudonymization secret.

## 7. Gate an external model or simulator

```python
from genuity_axiom import AdapterPolicy, AdapterRequest, DataBoundary

request = AdapterRequest(
    operation="generate",
    n_samples=1_000,
    scenario_id="adas-rain-night-01",
    sensitive=True,
    seed=42,
)

adapter = axiom.adapters.resolve(
    "approved-customer-vpc-simulator",
    modality="simulation",
    version="2026.08",
    request=request,
    policy=AdapterPolicy(
        allowed_boundaries=(DataBoundary.CUSTOMER_ENVIRONMENT,),
        allowed_names=("approved-customer-vpc-simulator",),
        require_no_provider_retention=True,
        require_deterministic_seed=True,
        require_constraint_interface=True,
    ),
)
```

Registration requires an implementation conforming to `AxiomAdapter`; Axiom ships the policy contract, not third-party credentials or hidden network calls.

## 8. Drift, expiry and revocation

```python
from genuity_axiom import DriftMonitor, ReleaseLifecycleRecord

drift = DriftMonitor().compare(release_reference_df, current_source_df)
lifecycle = ReleaseLifecycleRecord.from_manifest(result.manifest, validity_days=90)
status = lifecycle.assess(
    drift_requires_revalidation=drift.requires_revalidation,
    recipient="approved client project environment",
    purpose="offline failure-model development",
)

if incident_confirmed:
    lifecycle.revoke("privacy incident PROJECT-1234")
```

## 9. Select a built-in starting pack

```python
from genuity_axiom import list_domain_packs, load_domain_pack

print(list_domain_packs())
pack = load_domain_pack("software_defined_mobility_embedded")
```

Treat packs as review checklists. They do not contain client-specific thresholds or certify a system.
