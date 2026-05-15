# Genuity Axiom Architecture

> **Superseded v0.2 architecture note.** Retained for design history. The current v0.3 architecture, hard release policy, adapters, lifecycle controls and implementation boundaries are documented in `AXIOM_ENTERPRISE_ARCHITECTURE.md` and `../START_HERE.md`.

## Objective

Build a Genuity IO synthetic data engine optimized for engineering teams building industrial AI, engineering world models, and large mechanical models. The engine should be independent, auditable, privacy-aware, and constraint-first.

## Architecture

1. Compliance Gate
   - Detects direct PII, quasi-identifiers, IDs, serials, UUIDs, names, email, phone, account-like fields.
   - Applies drop, mask, or flag policy before model training.

2. Engineering Profiler
   - Detects modality, domain, type mix, text/time/entity columns, imbalance, high missingness, heavy tails, physical-positive fields, and high-dimensional risk.

3. Industrial Model Router
   - Produces both a current executable ladder and a frontier planned ladder.
   - Records reasons and warnings for model choice.

4. Holdout Split
   - Keeps a holdout slice out of generator training when enough rows exist.
   - Prevents quality reporting from accidentally rewarding memorization.

5. Fallback Synthesizer
   - Current executable ladder: GMM, KDE, Gaussian Copula, Stratified Bootstrap, Bootstrap.
   - In max mode, scores multiple candidates and selects the best.

6. Constraint Engine
   - Bounds, comparisons, allowed values, non-null checks, and dataframe expressions.
   - Repairs simple bound/category violations.

7. Evaluator
   - Fidelity: distribution, correlation, missingness, range.
   - Utility: train-on-synthetic, test-on-real when target is supplied.
   - Privacy: exact duplicates, nearest-neighbor score, membership-style train-vs-holdout proximity.
   - Detectability: classifier can/cannot separate real vs synthetic.
   - Constraint compliance.

8. Data Card
   - Summarizes generator, domain, scores, risks, and next actions.

## Engineering-Specific Differentiators

- Constraints are first-class, not afterthought postprocessing.
- Model selection depends on engineering domain, modality, and target imbalance.
- Holdout-aware QA reduces the risk of "high quality" being memorization.
- The product can plug in heavy neural adapters while retaining a deterministic statistical backbone.
- Designed for world-model data where boundary conditions and control-response coherence matter.

## Local Genuity IO Artifact Backtracking

Workspace artifacts reviewed:

- `LEGACY_CTO_DOCUMENTATION.md`: Genuity v2.0 API and generator benchmark documentation.
- `CONSOLE_GUIDE.md`: engineering demo workflows across tabular, time series, multi-table, and text.
- `Vulpix system_documentation (1).txt`: microservice, fallback, PII, orchestration, and codebox safety architecture.
- `aero/comprehensive_experiment_report.txt`: 72-run aerospace synthesis methodology.
- `aero/final/experiments/*.csv`: final experiment registries.
- `aero/deliverables_LnT/reports/*`: model comparison, IO coherence, similarity/innovation, and executive reports.
- `POC_Report.pdf`: world-model rare-event and imagined-control POC framing.

Backtracked product requirements:

- The old aerospace POC treated KDE as the recommended model for the 300-row aerospace structural dataset, with high composite score, low MMD, near-random discriminator AUC, TSTR accuracy, full schema compliance, and zero out-of-range values.
- The POC reports used more engineering-specific evidence than generic synthetic-data reports: physics rules, SHAP/feature-importance alignment, input-output coherence, counterfactual correction, edge-case realism, class balance, and bootstrap confidence intervals.
- Axiom therefore promotes `quality_mode="max"` holdout selection, data cards, semantic engineering roles, and frontier IO/causal/physics checks rather than defaulting to CTGAN or any one neural model.

## Next Frontier

- Native time-series sequence generators.
- Multi-table PK/FK generator and relational graph constraints.
- Physics residual checks: stress, strain, thermal, vibration, conservation-style constraints.
- Scenario and edge-case generator for rare but valid operating regimes.
- Formal DP adapters: MST, AIM, DP-TVAE, PATE-GAN.
- Tapas-style adversarial privacy audits.
- HTML/PDF quality report generation.
