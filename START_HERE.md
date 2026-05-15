# Genuity Axiom — Start Here

Founder/business navigation begins at [`FOUNDERS.md`](FOUNDERS.md).

For Genuity's immediate LTTS wedge, first-meeting demo and four-month validation plan, use [Genuity 2.0 Use Case 1](<../Genuity2.0 usecase1/README.md>). Axiom is its synthetic, rare-edge, privacy and robustness layer—not a competing company direction. Company-wide navigation begins at [`../START_HERE_GENUITY_IO.md`](../START_HERE_GENUITY_IO.md).

## The product in one sentence

Genuity Axiom converts scarce, sensitive, or incomplete operational data into **evidence-gated synthetic datasets and rare operating scenarios** for industrial AI development, testing, and validation.

The product is **Axiom**. `pramana` exists only as a backward-compatible Python/CLI alias.

## What it is—and what it is not

Axiom is a data-provisioning and assurance layer. It profiles source data, detects sensitive fields, selects a suitable generation baseline, enforces domain constraints, evaluates utility and disclosure risk, and produces an auditable release decision. It can also preserve basic sequence order and PK/FK integrity, transform unstructured identifiers, and generate constraint-aware boundary scenarios.

Axiom is not currently a universal world model, physics solver, formal privacy proof, or native image/video generator. Those capabilities require validated adapters. The library records that boundary explicitly instead of implying unsupported functionality.

## Fastest executable path

Use `pip install -e ".[ml]"` for target-based TSTR/utility evaluation. The core `numpy`/`pandas` install can generate baselines, but a release policy requiring task utility will block when the evaluator is unavailable.

```python
from genuity_axiom import GenuityAxiomEngine, IntendedUse, SynthesisConfig

config = SynthesisConfig(
    n_samples=10_000,
    target_col="failure_mode",
    privacy_level="strict",
    risk_tier="internal",
    intended_use=IntendedUse(
        purpose="predictive-maintenance model development",
        users=["reliability engineering", "data science"],
        prohibited_uses=["automatic shutdown decisions without real-data validation"],
        retention_days=90,
    ),
)

result = GenuityAxiomEngine().synthesize(real_df, config=config)
print(result.release.decision.value)
print(result.manifest.run_id)
```

Use `result.data` only according to `result.release`. A high composite score never overrides a failed privacy, physical-validity, lineage, or approval gate.

## Enterprise capability surface

```python
from genuity_axiom import AxiomEnterpriseEngine

axiom = AxiomEnterpriseEngine(random_state=42)
axiom.tabular       # native local synthesis and evaluation
axiom.time_series   # deterministic temporal baseline
axiom.relational    # PK/FK-preserving baseline
axiom.rare_events   # constrained tail/boundary candidate generation
axiom.unstructured  # identifier replacement and leakage audit
axiom.capabilities  # exact implemented/adapted capability matrix
axiom.compliance    # evidence catalog, not compliance certification
```

## Repository map

- `engine.py` — tabular workflow and release integration.
- `release.py` — non-compensating safety/privacy gates.
- `governance.py` — run lineage, hashes, intended use.
- `rare_events.py` — constrained edge-case candidates.
- `sequences.py` — time-series block baseline.
- `relational.py` — relational integrity baseline.
- `unstructured.py` — text/document privacy baseline.
- `modalities.py` — modality contracts and capability truth.
- `compliance_catalog.py` — control/evidence mapping.
- `adapters.py` — policy-controlled external model/simulator contract.
- `scenarios.py` — scenario-as-code acceptance.
- `drift.py`, `lifecycle.py` — revalidation, expiry and revocation.
- `preprocessing.py` — privacy-aware messy/nested table preparation.
- `docs/AXIOM_ENTERPRISE_ARCHITECTURE.md` — system and buyer architecture.
- `docs/AXIOM_EVALUATION_AND_RELEASE_STANDARD.md` — acceptance protocol.
- `docs/AXIOM_FOUNDER_CONTINUATION_GUIDE.md` — business and technical direction.
- `docs/AXIOM_GLOBAL_MARKET_RESEARCH_2026.md` — competitor/use-case research.
- `docs/AXIOM_LTTS_4_MONTH_USE_CASE_PLAYBOOK.md` — validation plan with LTTS.
- `docs/AXIOM_LTTS_SYNTHESIS_TASK_ROUTER.md` — route any LTTS synthesis assignment to the right pipeline.
- `docs/AXIOM_LTTS_API_RECIPES.md` — copy-ready code for common LTTS tasks.
- `docs/AXIOM_ENTERPRISE_SECURITY_AND_COMPLIANCE.md` — threat model and deployment controls.
- `docs/AXIOM_PRODUCT_AND_COMMERCIAL_PLAYBOOK.md` — qualification, pilot and pricing logic.
- `docs/PRAMANA_TO_AXIOM_MIGRATION.md` — one-product migration and compatibility boundary.
- `docs/AXIOM_BRUTAL_REVIEW_LOG.md` — resolved defects, remaining gaps and kill criteria.

## The immediate wedge

Do not sell “all synthetic data” or “world models.” Sell one measurable workflow:

> Axiom helps industrial AI teams test failure modes they cannot safely or economically collect, while proving each generated scenario is useful, physically valid, non-duplicative, and approved for its intended use.

The first deployment should target a buyer with an existing model or test workflow, a known rare-event coverage gap, and a measurable cost of simulation/collection. Axiom’s output is a scenario pack, evidence report, and release manifest—not merely a CSV.

## Safety rule

Synthetic does not automatically mean anonymous, compliant, physically valid, or fit for production. Every claim is conditional on the source, generator, threat model, constraints, holdout, recipient, and intended use. External and regulated releases require accountable human approval and, where applicable, formal legal/privacy expertise.
