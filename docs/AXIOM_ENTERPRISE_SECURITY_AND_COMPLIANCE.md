# Axiom Enterprise Security and Compliance Guide

## Scope

This guide defines evidence and product requirements. The local Python library is not a certified hosted service and does not establish legal compliance.

## Threat model

Protect against source-data exposure, cross-tenant leakage, external-provider retention, malicious files, prompt/data exfiltration, exact memorization, linkage/re-identification, insider access, weak pseudonym keys, poisoned source data, invalid physics, unauthorized release, stale approvals and inability to revoke.

## Data boundary policy

Classify every run as local, customer environment, managed private or external service. Sensitive industrial, personal, export-controlled or critical-infrastructure data should default to customer-controlled execution. The adapter registry blocks boundaries, retention behavior and operations that do not match policy. A fallback may never silently cross a data boundary.

## Controls implemented in the package

- identifier/content-pattern screening for structured data;
- unstructured replacement/redaction baseline and overlap audit;
- source/output/configuration fingerprints;
- intended-use, recipient and prohibited-use record;
- exact duplicate, nearest-neighbour and membership-inspired diagnostics;
- constraints, holdout, modality and compliance release gates;
- adapter allowlist/data-boundary policy contract;
- expiry, drift revalidation and revocation records;
- framework evidence catalog.

## Controls required in a production deployment

- SSO/MFA/RBAC and periodic access review;
- tenant and project isolation;
- encryption in transit/at rest with customer/KMS key options;
- protected secret storage and rotation;
- malware/format validation and size/resource limits;
- immutable audit events and signed artifacts;
- network egress allowlists and private endpoints;
- software supply-chain controls, SBOM, scans and signed builds;
- job isolation, quotas and denial-of-service controls;
- regional storage/processing and subprocessor inventory;
- backup/restore, incident response and tested deletion;
- security/privacy review, penetration test and certification work appropriate to buyers.

These are not implemented merely because the architecture document lists them.

## Privacy evidence

Define the attacker, auxiliary information, recipient, linkable fields and release context. Run exact/near-match, membership and relevant attribute/linkage tests. Inspect unstructured text and media separately. A privacy score is dataset- and threat-model-specific; it is not an anonymity certificate.

Formal differential privacy requires a mechanism, clipping/sensitivity assumptions, epsilon, delta, accountant and composition ledger. Axiom’s `DifferentialPrivacyEvidence` records these items; it does not independently prove that the external mechanism ran correctly. Axiom’s `dp-ready` mode does not provide that proof, and the CLI will not accept a bare DP boolean.

## Framework mapping

`ComplianceControlCatalog` maps evidence requests across GDPR, India DPDP, HIPAA, PCI DSS, EU AI Act, NIST AI RMF, ISO 27001 and SOC 2. Mappings support diligence only. Applicability, lawful basis, de-identification standards, controller/processor roles and sector obligations require qualified legal/privacy owners.

Useful primary references:

- India DPDP Rules 2025: <https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa>
- EU AI Act Article 10: <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-10>
- NIST AI RMF: <https://www.nist.gov/itl/ai-risk-management-framework>
- HHS HIPAA de-identification: <https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html>

## Minimum external-release review

Data/domain owner, privacy/legal owner, security owner and model/decision owner must confirm intended use, recipient, constraints, privacy evidence, downstream validity, retention/expiry, limitations and incident/revocation path. Regulated or safety-relevant uses may require additional independent assessors.

The SDK represents signoff with `ApprovalEvidence`—role, approver, time, scope and evidence reference—rather than anonymous booleans. The SDK does not authenticate the approver; production identity, signature and separation-of-duty controls must be supplied by the enterprise control plane.
