# Axiom v0.3 Changelog and Engineering Handoff

## Product consolidation

- One implementation under `genuity_axiom`.
- `pramana` retained as a compatibility shim and CLI alias only.
- Legacy CTO documentation marked as design history, not executable capability.

## New executable controls

- non-compensating sandbox/internal/external/regulated release policies;
- minimum fitness, missingness, privacy, range, constraints, condition match and membership evidence;
- independent holdout and modality-appropriate evaluation checks;
- task-utility gate when a target column defines the use;
- named/scoped `ApprovalEvidence` and structured `DifferentialPrivacyEvidence`;
- reproducible JSON-safe configuration, fingerprints, intended use and run manifest;
- approved-only CLI export with explicit sandbox override;
- release expiry, drift revalidation and revocation records.

## New data capabilities

- constraint-aware rare-event/tail candidates with novelty threshold;
- temporal block baseline and ordering validation;
- relational PK/FK validation and baseline synthesis;
- recursive unstructured identifier transforms and verbatim overlap audit;
- privacy-aware nested-cell preparation;
- modality/data-bundle contracts and truthful capability registry;
- policy-controlled external model/simulator adapter registry;
- scenario-as-code business acceptance;
- validated JSON domain-pack loader.

## LTTS/product assets

- task router for Mobility, Sustainability and Tech workflows;
- runnable LTTS recipes;
- four-month validation/mentor playbook;
- 10 Axiom packs spanning aerospace, SDV/embedded, predictive maintenance, manufacturing, SCADA, test data, finance, healthcare/medtech and telecom;
- founder, market, commercial, architecture, evaluation and security guides.

## Bugs eliminated during adversarial review

- decimal measurements falsely classified as phone numbers;
- broad privacy keywords dropping legitimate business fields;
- unsupported conditions silently falling back to unconditioned data;
- missing privacy dependencies returning perfect privacy scores;
- warning constraints treated as hard safety errors;
- missing compliance and modality checks in release decisions;
- novelty threshold exposed but not enforced;
- nested values failing deep inside profiling;
- configuration hash without reproducible configuration content;
- `review` artifacts exported before approval;
- high-memory three-dimensional distance allocations.

## Verification status at handoff

- standard-library enterprise suite: 27 tests passing at last v0.3 source pass, including expression-safety assertions;
- original Axiom and Pramana regression functions passing;
- `compileall` passing;
- wheel build and isolated installation passing;
- 10 Axiom packs discoverable from installed wheel;
- real internal target-based CLI correctly fail-closed when utility evidence unavailable;
- real external CLI reached review and did not export without approvals.

Final wheel: `genuity_axiom/release/genuity_axiom-0.3.0-py3-none-any.whl`  
SHA-256: `5EB4C0DD87BDA403161BBEB11084E9F55135BDBBFB877066E2EFC61AAE506F5B`  

The final wheel was rebuilt after product-folder consolidation. It contains Axiom, its local domain packs and the Pramana compatibility alias only; the Genuity 2.0 reconciler and templates are deliberately excluded.
The wheel was installed into an isolated target and verified for Axiom/Pramana version parity, 68 public exports and all 10 current discoverable Axiom packs. Its archive contains 11 pack files because one is a retained compatibility pack. It contains no `genuity_reconcile` package.

Re-run all checks after any further edit; this document records a point in time, not a permanent certification.

## Highest-priority next engineering work

1. Entity/time-aware holdout split and production sequence evaluator for the selected LTTS use case.
2. Private runner/control plane with identity, signing, RBAC, audit and artifact registry.
3. One production connector and one domain pack pulled by a paid workflow.
4. Learned sequence/multi-table adapter selected through measured value.
5. Formal privacy integration only when a customer requirement justifies it.
6. Continuous benchmark and end-to-end test fixtures using public/permissioned data.

Do not expand native modality claims before the corresponding evaluator, release policy and customer evidence exist.
