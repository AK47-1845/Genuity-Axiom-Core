"""Policy-controlled contracts for external models, private runners, and simulators."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from .modalities import DataBundle, Modality


class DataBoundary(str, Enum):
    LOCAL = "local"
    CUSTOMER_ENVIRONMENT = "customer_environment"
    MANAGED_PRIVATE = "managed_private"
    EXTERNAL_SERVICE = "external_service"


@dataclass(frozen=True)
class AdapterDescriptor:
    name: str
    version: str
    modalities: tuple[Modality, ...]
    operations: tuple[str, ...]
    data_boundary: DataBoundary
    deterministic_seed: bool = False
    formal_dp: bool = False
    constraint_interface: bool = False
    provider_retains_input: bool | None = None
    license: str | None = None
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "modalities": [m.value for m in self.modalities],
            "operations": list(self.operations),
            "data_boundary": self.data_boundary.value,
            "deterministic_seed": self.deterministic_seed,
            "formal_dp": self.formal_dp,
            "constraint_interface": self.constraint_interface,
            "provider_retains_input": self.provider_retains_input,
            "license": self.license,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class AdapterRequest:
    operation: str
    n_samples: int | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    scenario_id: str | None = None
    sensitive: bool = True


@dataclass
class AdapterResponse:
    output: DataBundle
    adapter: AdapterDescriptor
    execution_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class AxiomAdapter(Protocol):
    descriptor: AdapterDescriptor

    def execute(self, source: DataBundle, request: AdapterRequest) -> AdapterResponse:
        ...


@dataclass(frozen=True)
class AdapterPolicy:
    allowed_boundaries: tuple[DataBoundary, ...] = (
        DataBoundary.LOCAL,
        DataBoundary.CUSTOMER_ENVIRONMENT,
    )
    allowed_names: tuple[str, ...] = ()
    prohibit_external_for_sensitive: bool = True
    require_no_provider_retention: bool = True
    require_deterministic_seed: bool = False
    require_constraint_interface: bool = False

    def violations(self, descriptor: AdapterDescriptor, request: AdapterRequest) -> list[str]:
        issues: list[str] = []
        if descriptor.data_boundary not in self.allowed_boundaries:
            issues.append("adapter data boundary is not permitted")
        if self.allowed_names and descriptor.name not in self.allowed_names:
            issues.append("adapter is not on the allowlist")
        if request.sensitive and self.prohibit_external_for_sensitive and descriptor.data_boundary == DataBoundary.EXTERNAL_SERVICE:
            issues.append("sensitive source data cannot be sent to an external service")
        if self.require_no_provider_retention and descriptor.provider_retains_input is not False:
            issues.append("provider input-retention behavior is not verified as false")
        if self.require_deterministic_seed and not descriptor.deterministic_seed:
            issues.append("deterministic seed support is required")
        if self.require_constraint_interface and not descriptor.constraint_interface:
            issues.append("a machine-enforced constraint interface is required")
        if request.operation not in descriptor.operations:
            issues.append(f"operation {request.operation!r} is unsupported")
        return issues


class AdapterRegistry:
    """Registers implementations and resolves them only through an explicit policy."""

    def __init__(self) -> None:
        self._adapters: dict[str, AxiomAdapter] = {}

    def register(self, adapter: AxiomAdapter) -> None:
        descriptor = adapter.descriptor
        if not descriptor.name or not descriptor.version:
            raise ValueError("adapter name and version are required")
        key = f"{descriptor.name}:{descriptor.version}"
        if key in self._adapters:
            raise ValueError(f"adapter already registered: {key}")
        self._adapters[key] = adapter

    def descriptors(self) -> list[dict[str, Any]]:
        return [adapter.descriptor.to_dict() for adapter in self._adapters.values()]

    def resolve(
        self,
        name: str,
        *,
        modality: str | Modality,
        request: AdapterRequest,
        policy: AdapterPolicy,
        version: str | None = None,
    ) -> AxiomAdapter:
        target = modality if isinstance(modality, Modality) else Modality(str(modality))
        matches = [
            adapter for key, adapter in self._adapters.items()
            if adapter.descriptor.name == name
            and (version is None or adapter.descriptor.version == version)
            and target in adapter.descriptor.modalities
        ]
        if not matches:
            raise LookupError(f"no registered adapter matches {name!r}, {target.value!r}, version={version!r}")
        if version is None and len(matches) > 1:
            raise LookupError("multiple adapter versions match; pin a version for reproducibility")
        adapter = matches[0]
        violations = policy.violations(adapter.descriptor, request)
        if violations:
            raise PermissionError("adapter policy rejected execution: " + "; ".join(violations))
        return adapter
