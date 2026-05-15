"""Unified enterprise facade for every capability shipped by Genuity Axiom.

The facade makes capability boundaries explicit.  Native and baseline modules
can run locally; validation-only and adapter-required modalities cannot be
silently represented as implemented generation features.
"""

from __future__ import annotations

from .adapters import AdapterRegistry
from .compliance_catalog import ComplianceControlCatalog
from .engine import GenuityAxiomEngine
from .drift import DriftMonitor
from .modalities import CapabilityRegistry, Modality
from .rare_events import RareEventGenerator
from .relational import RelationalSynthesizer
from .sequences import TimeSeriesBlockSynthesizer
from .unstructured import UnstructuredPrivacyProcessor


class AxiomEnterpriseEngine:
    """Single, honest entry point for the Axiom capability portfolio."""

    def __init__(self, *, random_state: int | None = 42) -> None:
        self.random_state = random_state
        self.tabular = GenuityAxiomEngine()
        self.time_series = TimeSeriesBlockSynthesizer(random_state=random_state)
        self.relational = RelationalSynthesizer(random_state=random_state)
        self.rare_events = RareEventGenerator(random_state=random_state)
        self.unstructured = UnstructuredPrivacyProcessor()
        self.capabilities = CapabilityRegistry()
        self.compliance = ComplianceControlCatalog()
        self.adapters = AdapterRegistry()
        self.drift = DriftMonitor()

    def require_generation_capability(self, modality: str | Modality) -> None:
        """Raise if Axiom cannot execute generation for a modality locally."""

        capability = self.capabilities.get(modality)
        if capability.level.value in {"validation_only", "adapter_required"}:
            raise NotImplementedError(
                f"{capability.modality.value} generation is {capability.level.value}; "
                f"configure an approved adapter. {'; '.join(capability.limitations)}"
            )


# Pramana remains an import-level compatibility name, not a second product.
PramanaEnterpriseEngine = AxiomEnterpriseEngine
