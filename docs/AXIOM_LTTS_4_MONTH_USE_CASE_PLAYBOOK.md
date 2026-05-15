# LTTS Four-Month Validation Playbook

## Objective

Use access to LTTS and Dr. Madhusudan Singh to identify and validate one repeatable industrial buying problem. Do not spend four months trying to “build a world model.” The target outcome is a buyer-backed use case, measurable baseline, validated scenario pack, design-partner commitment, and product requirements that can generalize beyond one project.

## Recommended use case

**Rare operating-condition coverage for industrial AI validation**, beginning with one telemetry/engineering workflow where failures are costly and real observations are scarce.

Ideal pilot characteristics:

- a deployed or planned model whose failure has economic/safety consequences;
- a named engineering owner and budget owner;
- historical telemetry plus event/maintenance labels or a simulator;
- fewer failure examples than the team needs;
- a current manual collection/simulation workflow with measurable cost or delay;
- acceptance metric such as recall at fixed false-alarm rate, scenario coverage, simulation hours or validation-cycle time.

Avoid a pilot that has no real holdout, no downstream task, no domain reviewer, or no path to a second customer.

## Four workstreams

### Weeks 1–4 — Problem and evidence contract

- Interview 12–20 stakeholders across AI, domain engineering, validation, privacy/security and business ownership.
- Inventory 3–5 candidate workflows and score pain, urgency, data access, measurability, sponsor and repeatability.
- Select one use case and write the scenario taxonomy: normal, known rare, boundary, compound, unknown/unsupported.
- Define the real-data holdout and prevent generator access.
- Quantify today’s cost: engineer-hours, simulator time, lab/fleet cost, model misses, delay and rework.
- Sign a one-page acceptance contract with baseline, target, constraints, permitted use and release authority.

Deliverables: buyer map, problem scorecard, source contract, holdout fingerprint, scenario specification, baseline report, economic baseline.

### Weeks 5–8 — Thin end-to-end product

- Ingest and profile one approved dataset.
- Encode domain constraints with engineers; identify which require a simulator rather than data-only validation.
- Run native Axiom tabular/temporal baselines and at most one approved advanced adapter.
- Generate three scenario packs: control, known rare event and boundary/compound event.
- Emit manifests, privacy report, physical-validity report and release status.
- Put outputs into the customer’s actual training/test workflow.

Deliverables: reproducible pipeline, three versioned scenario packs, evidence bundle, first TSTR/augmentation comparison, documented failures.

### Weeks 9–12 — Prove value and repeatability

- Compare real-only, synthetic-only and real-plus-synthetic under the same holdout.
- Report confidence intervals and per-scenario/subgroup performance, not one headline number.
- Measure scenario coverage and novelty; have domain owners inspect a blinded sample.
- Compare time/cost against current collection or simulation.
- Repeat on a second asset/configuration without rewriting the product from scratch.
- Run privacy/security and deployment reviews for private/VPC/on-prem operation.

Deliverables: validated scorecard, cost/time result, second-configuration replication, deployment requirements, referenceable case study draft.

### Weeks 13–16 — Productize and secure commitment

- Convert bespoke code into a reusable domain pack, connector and acceptance template.
- Add revalidation triggers, expiry and approval workflow.
- Obtain a design-partner LOI or paid pilot with named next milestone and economic owner.
- Identify 5 external prospects with the same workflow and conduct discovery before expanding scope.
- Decide using evidence: proceed, narrow, change use case, or stop.

Deliverables: v1 product requirements, reusable pack, commercial proposal, design-partner evidence, external discovery log, board/founder decision memo.

## Questions for Dr. Madhusudan Singh

### Pain and buyer

1. Which three AI programs are blocked by missing failure/boundary data today—not theoretically?
2. Who experiences the pain, who signs off technically, who controls data access, and who owns budget?
3. What does the team currently do: collect, simulate, copy production data, manually perturb, or accept blind spots?
4. What was spent in the last project and what delay or model failure did it cause?
5. Which workflow repeats across LTTS customers strongly enough to become a product?

### Data and validation

6. Which data and labels exist, and which failure modes are genuinely absent?
7. Can a real holdout be isolated before development?
8. Which physical rules are hard blockers, which are approximate, and who can approve them?
9. Which simulator/test bench is regarded as ground truth, and how is it calibrated?
10. What downstream metric changes a launch/validation decision?

### Security and procurement

11. Must data remain on-prem/VPC/India/EU, and are external model calls prohibited?
12. Which privacy, IP, export-control, customer-contract or safety constraints apply?
13. Who can authorize a release and what evidence do they need?
14. What procurement path exists for a startup pilot and then production license?

### Commercialization

15. Would customers buy software, a managed outcome, or engineering services first?
16. What unit makes pricing legible: scenario family, data volume, asset/program, runner, or annual platform?
17. What result would justify a paid second phase?
18. Can LTTS introduce two customers with the same problem and permit a sanitized case study?

## Success metrics and kill criteria

Proceed only if all are true by month four:

- one named economic buyer recognizes the problem as urgent;
- an independent real holdout or credible simulator truth exists;
- Axiom improves a task/coverage/cycle-time metric over the current method;
- domain and privacy owners accept the evidence process;
- the workflow repeats on a second configuration/customer candidate;
- a paid next step or concrete design-partner commitment exists.

Kill or change direction if the “rare data” is easy to collect, the buyer will not pay, there is no measurable decision, synthetic outputs cannot be validated, bespoke simulation dominates all reusable software, or four months produce only compliments and no access/commitment.

## Relationship to world models

World models belong in the long-term roadmap only after Axiom owns valuable industrial episodes and evaluation loops. The near-term product supplies validated scenarios and evidence. The mid-term product synchronizes telemetry, events, documents and visual/simulation assets. A learned predictive environment may later become one adapter or proprietary model—but it must be earned by a repeated customer problem, not used as the opening pitch.
