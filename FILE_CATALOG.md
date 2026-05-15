# Genuity Axiom file catalog

## Start here

- `START_HERE.md` — product boundary and code map.
- `README.md` — installation, API, capability levels and limitations.
- `FOUNDERS.md` — founder entry point and four-month LTTS operating rule.
- `FILE_CATALOG.md` — this ownership map.
- `PRAMANA_COMPATIBILITY.md` — compatibility-only naming boundary.

## Runtime source

All Python modules directly under this folder belong to the `genuity_axiom` package. `domain_packs.py` discovers the bundled policies in `domain_packs/`. `pyproject.toml` makes this folder an independently buildable project. The local `pramana/` package preserves the public `import pramana` namespace; every module is a thin Axiom re-export, not a second product.

## Product assets

- `domain_packs/` — 10 current sector/use-case packs plus one legacy material-packet compatibility pack.
- `tests/` — enterprise, industrial regression and Pramana compatibility tests.
- `release/` — current Axiom wheel and SHA-256 checksums.
- `archive/` — non-authoritative historical build/install caches retained instead of deleting them.

## Research and operating documents

- `docs/AXIOM_FOUNDER_CONTINUATION_GUIDE.md` — detailed business/technical handoff.
- `docs/AXIOM_LTTS_4_MONTH_USE_CASE_PLAYBOOK.md` — four-month plan and mentor questions.
- `docs/AXIOM_LTTS_SYNTHESIS_TASK_ROUTER.md` — task-to-pipeline routing.
- `docs/AXIOM_LTTS_API_RECIPES.md` — runnable implementation recipes.
- `docs/AXIOM_ENTERPRISE_ARCHITECTURE.md` — system architecture.
- `docs/AXIOM_EVALUATION_AND_RELEASE_STANDARD.md` — acceptance and claims protocol.
- `docs/AXIOM_ENTERPRISE_SECURITY_AND_COMPLIANCE.md` — threat/deployment controls.
- `docs/AXIOM_GLOBAL_MARKET_RESEARCH_2026.md` — global product/competitor research.
- `docs/AXIOM_PRODUCT_AND_COMMERCIAL_PLAYBOOK.md` — pilot and commercial logic.
- `docs/AXIOM_BRUTAL_REVIEW_LOG.md` — resolved defects and remaining gaps.
- `docs/AXIOM_V0_3_CHANGELOG_AND_HANDOFF.md` — version evidence and wheel hash.
- `docs/PRAMANA_TO_AXIOM_MIGRATION.md` — one-product migration path.
- `docs/LEGACY_*.md` — clearly marked design history, not current API truth.

Company-wide pitch/history stays at the workspace root and is indexed by `../START_HERE_GENUITY_IO.md`. Genuity 2.0 Use Case 1 remains fully independent in `../Genuity2.0 usecase1/`.
