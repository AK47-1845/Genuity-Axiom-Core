# Axiom Enterprise Architecture

## Product thesis

Industrial teams rarely suffer from a generic lack of rows. They lack **decision-relevant coverage**: failures, boundary conditions, privacy-safe customer states, complete test databases, synchronized modalities, and evidence that generated data can be trusted. Axiom therefore treats generation as one stage in a controlled data-product lifecycle.

## Lifecycle

1. **Contract** — record buyer, decision, modality, schema, target event, jurisdiction, recipient, prohibited uses, retention, and acceptance criteria.
2. **Ingest** — fingerprint source assets, detect identifiers, inspect schema and distributions, and isolate train/holdout evidence.
3. **Plan** — choose native generator, deterministic baseline, domain simulator, or approved external adapter. No silent modality fallback.
4. **Generate** — create candidates with seeds, conditions, constraints, and adapter/version lineage.
5. **Reconcile** — enforce schema, keys, timestamps, allowed states, physical rules, and cross-asset relationships.
6. **Evaluate** — measure fidelity, task utility, coverage, exact reuse, nearest-neighbour exposure, membership signal, constraints, and operational acceptance.
7. **Gate** — apply independent blockers. Quality cannot compensate for privacy or safety failure.
8. **Package** — emit dataset/scenario artifacts, manifest, data card, test evidence, limitations, approvals, expiry, and revocation handle.
9. **Monitor** — revalidate on source drift, schema change, generator change, policy change, new recipient, or expiry.

## Execution layers

### Control plane

- intended-use and recipient registry;
- modality/capability registry;
- generator/adapter policy;
- run orchestration and deterministic seeds;
- evidence and approval workflow;
- release policy, expiry, and revocation;
- tenant, identity, secrets, and audit integration in a deployed service.

### Data plane

- local/private-network processing by default for sensitive industrial data;
- tabular native baselines;
- relational and temporal baselines;
- unstructured privacy transforms;
- domain simulator and foundation-model adapters;
- isolated artifact storage with immutable hashes.

### Evidence plane

- source/output/configuration fingerprints;
- independent holdout identity;
- model and adapter versions;
- privacy attack results and assumptions;
- domain constraints and scenario coverage;
- downstream TSTR/TRTS/task metrics;
- human approvals, exceptions, and known limitations.

## Capability truth matrix

| Modality | Local status | What works now | Required for production depth |
|---|---|---|---|
| Tabular | Native | profiling, routing, generation, constraints, evaluation, release | stronger neural/DP adapters, scale and MLOps |
| Relational | Baseline | schema and PK/FK validation, key-safe sampling | learned multi-table dependence, database connectors |
| Time series/events | Baseline | block synthesis, monotonic time, entity remap | long-range/control-response models, irregular sampling |
| Text/documents | Baseline | pattern replacement, recursive transform, overlap audit | NER/OCR/layout and approved language-model adapter |
| Graph/simulation | Validation-only | contracts, integrity and parameter evidence | graph generator or physics/simulation engine |
| Image/audio/video | Adapter-required | metadata/annotation/privacy contracts | native generators and modality-specific evaluators |
| Multimodal | Validation-only | asset bundle and cross-asset release manifest | capable adapters plus synchronization tests |

## Deployment profiles

- **Developer sandbox:** local package, synthetic/non-sensitive inputs, no external release.
- **Enterprise private runner:** control plane manages policy; generation occurs inside the customer VPC/on-prem environment; only evidence and permitted aggregates leave.
- **Air-gapped/regulated:** offline artifacts, signed releases, customer-controlled keys, no unapproved external model calls.
- **Managed service:** only for data and jurisdictions accepted by policy; encrypted tenant isolation and regional processing are mandatory implementation work.

## Adapter contract

Every generator or simulator adapter must declare:

- supported modality, schema, scale, conditioning, and constraints;
- where source data and prompts are processed;
- training/data-retention behavior of the provider;
- determinism and seed support;
- model/version/container digest;
- privacy mechanism and verifiable accountant, if DP is claimed;
- resource estimate and failure modes;
- evaluator bundle appropriate to the modality;
- license and downstream artifact rights;
- explicit fallback policy. An adapter failure must never downgrade to a riskier service without authorization.

## Security work required before enterprise production

The Python library supplies data controls, not a completed secure SaaS. Production deployment still requires SSO/RBAC, tenant isolation, secrets management, encryption/KMS, immutable audit logging, malware/file scanning, egress policy, signed builds, SBOM/vulnerability management, backup/restore, incident response, retention deletion, and independent security review. These items are roadmap gates, not current claims.
