# Genuity Axiom Founder Continuation Guide

## How to navigate this guide during LTTS work

- For any new synthesis assignment, open `AXIOM_LTTS_SYNTHESIS_TASK_ROUTER.md` first.
- For copy-ready implementation patterns, use `AXIOM_LTTS_API_RECIPES.md`.
- For buyer qualification and pilot packaging, use `AXIOM_PRODUCT_AND_COMMERCIAL_PLAYBOOK.md`.
- For privacy/security diligence, use `AXIOM_ENTERPRISE_SECURITY_AND_COMPLIANCE.md`.
- For the four-month founder validation plan and mentor questions, use `AXIOM_LTTS_4_MONTH_USE_CASE_PLAYBOOK.md`.
- For runnable capability truth and code locations, use `../START_HERE.md`.
- For acceptance thresholds and claims discipline, use `AXIOM_EVALUATION_AND_RELEASE_STANDARD.md`.
- For competitor/product context, use `AXIOM_GLOBAL_MARKET_RESEARCH_2026.md`.

The LTTS router is deliberately practical and spans the current Mobility, Sustainability and Tech portfolio. It does not make Genuity dependent on LTTS; reusable scenario, adapter and evidence contracts must generalize to external design partners.

## 1. The decision made

Genuity should not present itself as a generic synthetic-data library, a consulting company that makes datasets on request, or a world-model company before validating a buyer and workflow. The coherent company is:

> **Genuity builds evidence-gated rare-scenario data infrastructure for industrial AI.** Axiom helps engineering teams define missing operating conditions, generate candidate data through the best approved model or simulator, verify privacy and physical validity, test downstream usefulness, and release an auditable scenario pack.

Synthetic data is the current technical mechanism. Rare-scenario coverage is the customer outcome. Industrial world-model infrastructure is a possible expansion, not the current product claim.

## 2. Why this direction is more defensible

“Synthetic data” is horizontal and crowded; buyers compare models and expect database, privacy and deployment depth. “World models” is large but premature without multimodal sequential data, causal validation, compute and a specific operational user. Rare-scenario coverage connects Genuity’s prior work—engineering POCs, constraint-aware generation, TSTR thinking and LTTS access—to a painful, measurable decision.

The wedge has four valuable properties:

- failures and boundaries are expensive or unsafe to collect;
- a model/test workflow creates measurable utility;
- domain constraints and evidence make industrial specialization matter;
- every deployment produces reusable scenario specifications, validators and connectors.

## 3. Product object

The unit of value is not “one synthetic dataset.” It is a **Synthetic Scenario Pack**:

1. intended-use and recipient contract;
2. source/schema/modality inventory;
3. scenario taxonomy and requested coverage;
4. generated artifacts with synchronized identifiers;
5. domain constraints and validation evidence;
6. downstream real-holdout results;
7. privacy/confidentiality tests;
8. run manifest and reproducibility hashes;
9. release decision, approvals, limitations and expiry.

This object can be sold as a paid pilot and later automated as software.

## 4. Product architecture

### Axiom Core — implemented foundation

- tabular profiling and generator routing;
- local statistical generators/fallbacks;
- conditioning and engineering constraints;
- fidelity, range, privacy, membership-inspired and utility evaluation;
- hard release gates and independent holdout requirement;
- manifest, fingerprints and data card;
- deterministic rare-event candidate generation;
- relational PK/FK and temporal block baselines;
- unstructured pattern replacement and verbatim-leakage checks;
- truthful modality and compliance evidence registries.

### Axiom Enterprise — next product work

- connectors to databases/object stores/time-series systems;
- VPC/on-prem private runner;
- SSO/RBAC, tenancy, encryption, secrets and immutable audit;
- job orchestration, queues, artifact registry and approvals UI;
- learned relational/sequence and formal-DP adapters;
- drift, expiry and revalidation;
- customer domain packs and SDK/API.

### Axiom Scenario OS — later expansion

- scenario-as-code across sensor, event, maintenance, document and visual data;
- domain simulator orchestration and calibration;
- coverage planning and active selection of the next most valuable scenario;
- multimodal industrial episode store;
- continuous model blind-spot monitoring;
- eventually learned predictive environments/world-model adapters where data and economics justify them.

## 5. Technical priorities

### Immediate (0–4 months)

1. One LTTS use case with independent holdout and economic baseline.
2. Temporal/entity-aware splitting and evaluation for the chosen workflow.
3. Scenario specification format and constraint pack co-authored with engineers.
4. Private runner design and one real connector.
5. Downstream comparison: real-only, synthetic-only, augmented.
6. Signed scenario/evidence bundle and human release workflow.
7. Standardized failure logging—invalid scenarios are product learning.

### Mid-term (4–12 months)

1. Two additional design partners in the same workflow.
2. Learned time-series/event adapter and multi-table event model.
3. Formal DP adapter only for buyers who require it, with budget ledger.
4. Production control plane, APIs, SDK, CI/CD hooks and monitoring.
5. Domain-pack marketplace/repository with versioned validators.
6. Benchmark suite using non-customer or permissioned datasets.

### Long-term (12–36 months)

1. Multimodal scenario bundle linking telemetry, images/video, commands, maintenance and outcomes.
2. Simulator connectors for major industrial workflows.
3. Coverage optimizer that proposes the next scenario by expected decision value.
4. Cross-customer learning only through permissioned, privacy-safe metadata/evidence—not raw customer data.
5. Predictive environment/world-model layer for a domain where Axiom has unique episodes and validation access.

## 6. Business model

### Land

Paid 8–12 week validation engagement, priced for a decision outcome rather than rows. Scope one model/workflow, scenario family and acceptance scorecard. Services are acceptable initially because they reveal product requirements, but every delivery must create a reusable connector, validator or pack.

### Expand

Annual platform license based on private runner/environment plus governed programs or scenario volume. Add-ons can cover advanced adapters, domain packs, formal privacy evaluation, multimodal simulation orchestration and enterprise support.

### Do not price by rows alone

Rows are easy to commoditize and poorly reflect value. Pricing should track validation programs, assets, protected environments, scenario families or engineering cycle value. Never promise outcomes beyond the acceptance contract.

## 7. Customer and buyer

Initial customer profile: engineering enterprise or industrial technology provider with an AI model/test workflow, scarce failures, a domain validation team and costly collection/simulation. Candidate sectors include predictive maintenance, manufacturing quality/inspection, energy operations, automotive/aerospace validation and engineering-service providers.

Users: data scientists, simulation engineers, reliability/validation teams. Champions: AI/data lead or engineering validation leader. Blockers: cybersecurity, privacy, IP/legal and safety. Economic buyer: business/program owner accountable for validation cost, model performance or time-to-deployment.

## 8. Moat

The code alone is not a moat. The defensible system is accumulated domain knowledge and workflow integration:

- scenario taxonomies tied to real failures;
- validated constraint and evaluator packs;
- connectors into expensive industrial workflows;
- evidence accepted by domain/privacy/safety reviewers;
- private-deployment and release infrastructure;
- outcome history showing which synthetic scenarios improve which decisions;
- eventually proprietary multimodal episodes and feedback loops, with permission.

Avoid claiming that customer data automatically trains a shared model. Enterprise trust requires explicit contracts and isolation.

## 9. Evidence hierarchy

Use this order in pitches and decisions:

1. paid/repeated production usage;
2. buyer-backed design partnership with access and acceptance criteria;
3. downstream result on independent real holdout;
4. replicated POC on a second configuration;
5. domain expert review and constraint evidence;
6. statistical similarity;
7. technical demo.

Programs, incubators, awards and grants are credibility context—not customer traction. POCs should name status accurately: completed, unpaid, internal, design partner, pilot, or production. Never blur them.

## 10. Investor narrative

Problem: industrial AI fails at the edges, while failure data is scarce, sensitive and expensive.

Current behavior: teams wait for events, run bespoke simulations, manually perturb data or ship models with unknown blind spots.

Solution: Axiom converts a missing-scenario specification into a validated, privacy-reviewed, auditable scenario pack integrated into the real training/test workflow.

Wedge: one telemetry/event use case validated with LTTS and repeated with external customers.

Expansion: scenario system of record across modalities and simulators, then continuous coverage and predictive environments.

Why now: increasing industrial AI deployment, private-compute expectations, physical-AI simulation investment and stronger governance demands make evidence as important as generation.

## 11. Claims discipline

Every externally stated number needs a source artifact. For the aerospace POC, preserve the dataset version, real/synthetic counts, split, TSTR metric definition, model, seeds, comparison baseline and screenshots/logs. Rephrase unverified “17× augmentation” as exactly what happened—for example, “expanded the training dataset from X to Y in a controlled POC”—and never imply 17× business improvement. Replace “TSTR = 1” with the named metric and uncertainty.

Do not claim current native support for modalities marked adapter-required. Do not claim compliance certification, anonymity, formal DP, physics accuracy, enterprise security or production customers without evidence.

## 12. Brutal risks

1. **Consulting trap:** every pilot is bespoke. Mitigation: select one repeated workflow and productize every engagement artifact.
2. **No buyer:** engineers like demos but budgets remain elsewhere. Mitigation: require economic owner and paid next step.
3. **Synthetic data adds no utility:** fidelity is high but the model does not improve. Mitigation: start with downstream acceptance and stop weak scenario families.
4. **Invalid rare events:** tails become impossible combinations. Mitigation: simulator/domain rejection, scenario provenance and hard gates.
5. **Privacy theatre:** synthetic outputs leak or the source pipeline is insecure. Mitigation: private runner, threat model, attacks and accountable review.
6. **Platform too early:** years spent building generic modality breadth. Mitigation: implement only what a validated workflow pulls.
7. **World-model distraction:** research scope outruns company evidence. Mitigation: keep it as an earned adapter/roadmap.
8. **Founder bandwidth:** cofounder departure leaves technical and commercial gaps. Mitigation: narrow scope, recruit a senior technical owner around the validated use case, and document decisions/ownership.

## 13. Weekly founder operating system

Track five numbers: customer interviews with economic owners, workflows scored, datasets/holdouts contractually accessible, experiments completed against baseline, and paid/design-partner commitments. Maintain a claim ledger and decision log. Every Friday ask:

- What customer decision became clearer?
- Which assumption died?
- What component became reusable?
- What evidence can an external reviewer reproduce?
- What should we stop building?

## 14. Next ten actions

1. Adopt the one-sentence positioning in this guide.
2. Choose three LTTS candidate workflows and score them within two weeks.
3. Get the first economic buyer interview with Dr. Madhusudan present.
4. Create a source/holdout/intended-use contract before touching data.
5. Quantify the current cost and failure of the customer’s workaround.
6. Implement only the connector, constraints and evaluator needed for that workflow.
7. Run real-only/synthetic-only/augmented comparisons.
8. Secure a paid next milestone or kill/narrow the use case.
9. Interview five external prospects with the same problem.
10. Recruit around observed gaps, not generic “AI/world model” titles.

## 15. Final standard

Axiom is ready to scale when a skeptical buyer can inspect a scenario pack and answer five questions: Why was it created? Which real blind spot does it cover? Is it physically/semantically credible? Is it safe for this recipient and use? Did it improve a real decision enough to justify payment? Until then, the founder’s job is validation—not narrative expansion.
