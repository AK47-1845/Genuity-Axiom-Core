# Pramana to Genuity Axiom Migration

There is one product and one implementation: `genuity_axiom`. Pramana is a compatibility name retained so older imports and the `pramana` CLI entry point continue to work during migration.

## New code

```python
from genuity_axiom import AxiomEnterpriseEngine, GenuityAxiomEngine
```

## Existing code

```python
from pramana import GenuityAxiomEngine
```

The existing form re-exports Axiom, but should be migrated when convenient. Do not add new features under `pramana/`, publish a separate Pramana package, or maintain two roadmaps.

## Renamed concepts

| Legacy concept | Current Axiom concept |
|---|---|
| Pramana engine | `GenuityAxiomEngine` |
| “safe synthetic data” score | independent `SyntheticReleaseGate` checks |
| model fallback list | native local ladder plus policy-controlled adapters |
| generated dataset | scenario/data artifact plus data card and run manifest |
| planned modality modules | `CapabilityRegistry` with native/baseline/validation/adapter levels |
| DP-ready | preparation state only; formal DP requires verified accountant evidence |

## Compatibility boundary

Only established legacy modules are thin re-export wrappers. New enterprise modules—adapters, scenarios, domain packs, drift, lifecycle, modalities and release governance—live under `genuity_axiom`. This keeps the compatibility surface small and prevents Pramana from re-emerging as a second product.
