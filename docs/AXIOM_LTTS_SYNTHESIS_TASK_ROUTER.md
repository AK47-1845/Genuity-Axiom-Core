# Axiom at LTTS — Synthetic-Data Task Router

## Purpose

Use this document when an LTTS mentor, practice lead, engineer or client gives you any data-synthesis request. It converts a vague request into the correct Axiom workflow, blocks unsafe overpromising, and records what can become reusable product IP.

LTTS’ current strategy spans Mobility, Sustainability and Tech and its six stated bets include Software Defined Mobility, Plant Buildout and Modernization, Energy and Industrial Automation, Next Gen Compute and AI Infrastructure, Software Platforms/Engineering Intelligence, and Medical Technology. Its official material also describes automotive/aerospace/rail/off-highway, industrial products, medical devices, telecom/hi-tech, embedded testing, digital manufacturing, digital twins and AI across the engineering lifecycle. Sources: <https://www.ltts.com/about-us>, <https://www.ltts.com/press-release/unveils-europe-first-EI-center>, <https://www.ltts.com/services/digital-engineering>, <https://www.ltts.com/services/embedded-systems>.

## The 10-minute intake

Before generating anything, ask:

1. What decision or test will use the output?
2. Who owns that decision and who can validate the data?
3. Is the missing item volume, privacy-safe access, a rare class, a boundary condition, a full database, or a synchronized multimodal episode?
4. What real holdout or calibrated simulator can judge success?
5. Which fields/modalities exist, at what entity/time granularity?
6. Which rules are hard physics/business rules versus soft correlations?
7. Where may data be processed—laptop, LTTS network, client VPC, air gap, external service?
8. What would make the customer reject the artifact?
9. Which metric and baseline decide whether this work has value?
10. Can the connector, scenario definition or validator repeat for another client?

If there is no named decision, validator or evaluation truth, do discovery—not generation.

## Task-to-pipeline router

| Request received | Axiom path | Output | Must not promise |
|---|---|---|---|
| “Augment this engineering table” | native tabular engine + constraints + real holdout | dataset, TSTR/augmentation comparison, release manifest | that fidelity alone improves the model |
| “Create rare failures from telemetry” | temporal baseline/approved sequence adapter + scenario-as-code + domain constraints | rare episode pack, lead-time/coverage metrics | causal/physical realism without simulator/domain evidence |
| “Give developers a safe test DB” | relational baseline/approved multi-table adapter + PII scan + PK/FK checks | provisionable schema-consistent DB and test report | anonymity/compliance from masking alone |
| “Generate maintenance notes/documents” | unstructured privacy processor + approved NER/LLM adapter + overlap audit | de-identified/synthetic document set | contextual identifier removal from regex alone |
| “Generate defect/ADAS/medical images” | image/simulator adapter through adapter policy + annotation contract | image/label/scenario pack and domain-gap evaluation | native Axiom pixel generation or clinical/safety validity |
| “Use CAD/CAE/digital twin output” | simulator orchestration contract + parameter manifest + calibration evidence | simulation scenario pack | Axiom is the physics solver |
| “Stress-test edge/embedded software” | enterprise test-data pack + scenario definitions + CI export | boundary inputs, state/event sequences, coverage results | product certification from generated tests |
| “Build a world model” | decompose into prediction decision, episode schema, modality adapters and holdout | dataset/evaluator first; model only after evidence | general industrial world understanding in four months |

## LTTS opportunity packs

### 1. Software-defined mobility and embedded validation

Data: CAN/Ethernet telemetry, diagnostics, software states, road/weather context, test cases and outcomes. High-value scenarios: sensor dropout, message timing, state-machine boundaries, rare diagnostic codes, EV battery/thermal limits, ADAS perception corner cases. Axiom owns scenario definitions, synchronization, privacy/IP controls and evidence. Vehicle dynamics, sensor rendering and closed-loop autonomy require validated simulators.

### 2. Aerospace/rail/off-highway engineering

Data: material/structural results, loads, environmental conditions, maintenance events, fleet telemetry and inspection. High-value scenarios: boundary load/environment combinations, sparse damage/fatigue states, sensor degradation, maintenance transitions. Axiom’s native tabular constraints are usable now; physics claims require CAE/digital-twin calibration and engineering signoff.

### 3. Plant modernization and industrial automation

Data: PLC/SCADA/historian events, process values, alarms, recipes, quality and maintenance. High-value scenarios: startup/shutdown, control/sensor failures, compound drift, quality escape, rare process upset. Use private execution, topology/event integrity and never inject unapproved data into live control.

### 4. Medical technology

Data: device telemetry, alarms, test protocols, connected-care events, clinical documents/images. High-value scenarios: alarm boundary, device fault, connectivity loss, rare workflow and subgroup coverage. Treat this as regulated evidence work: clinical/domain, privacy, security and model-risk approvals are external requirements; Axiom is not a clinical validator.

### 5. Telecom, semiconductor and next-gen compute

Data: network counters/events, traces, logs, device/firmware states, chip verification vectors and test results. High-value scenarios: congestion, handover failure, packet/timing boundary, rare log signatures, configuration combinations and hardware/software faults. Use event/sequence plus unstructured controls; protocol/conformance simulators remain authoritative.

### 6. Software platforms and Engineering Intelligence

Data: enterprise databases, API events, documents, code/test artifacts and AI-agent traces. High-value scenarios: privacy-safe development databases, mock APIs, agent failure/evaluation cases, load/performance states and data-quality regressions. This is the fastest commercialization path when industrial physics evidence is unavailable.

## Day-one workflow for any assignment

1. Create a `ScenarioDefinition` with buyer decision, operational definition, outcome, severity, validators and blocker metrics.
2. Load the nearest JSON domain pack and adapt—not overwrite—it for the client.
3. Classify modalities through `CapabilityRegistry`.
4. For native/baseline paths, run locally. For other modalities, write an `AdapterDescriptor` and pass it through `AdapterPolicy` before data access.
5. Separate train and independent holdout by entity/time.
6. Author constraints with the domain owner; label rule source and confidence.
7. Generate candidates; reject invalid/duplicate/non-novel scenarios.
8. Test against the client’s actual model, software or simulator.
9. Package run manifest, evidence, release decision, approvals and expiry.
10. Add the reusable connector/validator/scenario family to Axiom only after removing client IP.

## File/API navigation

- Start: `../START_HERE.md`
- Main tabular pipeline: `genuity_axiom/engine.py`
- Rare scenarios: `genuity_axiom/rare_events.py`, `genuity_axiom/scenarios.py`
- Time series: `genuity_axiom/sequences.py`
- Relational/test DB: `genuity_axiom/relational.py`
- Text/log privacy: `genuity_axiom/unstructured.py`
- External simulator/model control: `genuity_axiom/adapters.py`
- Release and evidence: `genuity_axiom/release.py`, `genuity_axiom/governance.py`
- Reusable starting contracts: `domain_packs/*.json`
- Four-month validation program: `AXIOM_LTTS_4_MONTH_USE_CASE_PLAYBOOK.md`

## What to show Dr. Madhusudan each week

- one problem/economic baseline update;
- one scenario taxonomy with rejected assumptions;
- one reproducible run and failed-gate report, not only best outputs;
- downstream real-holdout comparison;
- domain reviewer feedback;
- component made reusable;
- buyer/next-phase commitment;
- clear request for access, decision or introduction.

## Product-IP rule

Client raw data, names, proprietary constraints and outputs remain segregated according to contract. Product IP should be generic code, schemas, evidence formats, adapter interfaces, public/permissioned benchmark logic and anonymized domain patterns. Never copy client material into a shared domain pack without explicit authorization.
