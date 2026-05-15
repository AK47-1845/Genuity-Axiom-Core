# Axiom Evaluation and Release Standard

## Principle

Generation is successful only when the output passes the acceptance criteria of a named operational use. “Looks statistically similar” is insufficient. Axiom separates **model-selection scores** from **release authority**.

## Required evaluation families

1. **Structure:** schema, types, nullability, allowed categories, uniqueness, PK/FK integrity, ordering and cross-asset links.
2. **Fidelity:** marginals, quantiles, correlations/dependencies, missingness and segment distributions. Fidelity is diagnostic; it is not proof of value.
3. **Coverage:** named failure modes, tails, boundaries, combinations, operating envelopes and novelty against the source set.
4. **Task utility:** TSTR against a real holdout, comparison with real-only and augmented baselines, confidence intervals and subgroup results.
5. **Privacy/confidentiality:** exact duplicate rate, distance-to-closest-record, train/holdout similarity gap, membership and attribute attacks where meaningful, text overlap, residual identifiers and recipient-specific linkage risk.
6. **Physical/semantic validity:** hard rules, simulator/domain checks, conservation relationships, monotonicity, safe envelopes and expert review.
7. **Operational value:** collection/simulation hours avoided, test cases unlocked, detection recall at fixed false-positive rate, model robustness, time-to-data and manual rework.

## Holdout protocol

- Split before fitting, generator selection, condition tuning, or threshold selection.
- Preserve entity/time boundaries to prevent leakage; random row splits are not valid for many industrial sequences.
- Record the holdout fingerprint and prohibit generator access.
- Small datasets without a meaningful independent holdout cannot receive an internal-or-higher automated approval. Use cross-validation, simulation truth, external evidence, or human review, and label uncertainty.
- Never describe training data reused as a holdout as independent evidence.

## Non-compensating release gates

The local engine implements policies for sandbox, internal, external and regulated contexts. Blockers include minimum tabular fitness, missingness behavior, privacy score, physical constraints, range validity, membership signal, exact record reuse, train/holdout gap, condition match, modality-appropriate evaluation, independent holdout, and residual identifiers. When a target column defines a task, the engine also requires task utility. External/regulated policies additionally require named domain and privacy approvals. Formal DP, when required by a custom policy, must have recorded mechanism, epsilon, delta and composition—not a `dp-ready` label.

A release result is:

- **approved:** every configured blocker and review requirement passed;
- **review:** technical blockers passed but accountable approval is incomplete;
- **blocked:** one or more independent safety/privacy/evidence requirements failed.

## Rare-edge-case acceptance

For each scenario family record:

- precise operational definition and why it is rare;
- source support and simulator assumptions;
- parameters varied and prohibited combinations;
- expected causal/physical response;
- coverage target and novelty target;
- domain validation method;
- downstream test and success threshold;
- unsafe misuse and escalation path.

A rare row is not automatically a useful edge case. It must be plausible, relevant to a failure or decision, distinguishable from noise, and capable of improving a defined test or model metric.

## Modality-specific extensions

- **Relational:** zero orphan keys, zero duplicate PKs, cardinality distributions, join-path coverage and transaction consistency.
- **Time series:** monotonic/valid timestamps, cadence and gap patterns, autocorrelation/spectral behavior, event duration, transition legality and entity leakage.
- **Text/documents:** identifiers, proprietary entities, verbatim span leakage, semantic task utility, hallucination and layout/field consistency.
- **Images/video:** annotation correctness, scenario diversity, sensor/camera realism, identity/biometric risk, domain gap and downstream perception performance.
- **Simulation:** parameter provenance, solver/version, convergence, calibration against observed data, uncertainty and sim-to-real gap.

## Claims that Axiom must not make from current evidence

- “anonymous” or “GDPR/HIPAA/DPDP compliant” solely because data is synthetic;
- “differentially private” without a valid mechanism and accountant;
- “physically accurate” from column-range checks alone;
- “world-model ready” without sequential/multimodal causal validation;
- “17× better” unless the denominator, split, task, baseline and repeatable evidence are shown;
- “TSTR = 1” without the exact metric, test set and confidence interval.

## Release artifact minimum

Dataset/scenario pack, schema, data card, run manifest, hashes, intended use, recipient, generator/configuration, evidence report, release decision, exceptions, approvals, expiry/revalidation trigger, contact owner and revocation instructions.
