"""Genuity Axiom: engineering-first synthetic data generation.

The public API is intentionally small:

    from genuity_axiom import GenuityAxiomEngine
    result = GenuityAxiomEngine().synthesize(df, n_samples=1000)
"""

from .compliance import ComplianceGate, ComplianceReport, PrivacyPolicy
from .adapters import (
    AdapterDescriptor,
    AdapterPolicy,
    AdapterRegistry,
    AdapterRequest,
    AdapterResponse,
    DataBoundary,
)
from .approvals import ApprovalEvidence, has_approval
from .compliance_catalog import ComplianceControlCatalog, ControlAssessment, ControlRequirement
from .constraints import ConstraintReport, EngineeringConstraintSet, Rule
from .datacard import DataCard
from .engine import GenerationResult, GenuityAxiomEngine, PramanaEngine, SynthesisConfig
from .enterprise import AxiomEnterpriseEngine, PramanaEnterpriseEngine
from .evaluator import EvaluationReport
from .domain_packs import list_domain_packs, load_domain_pack, validate_domain_pack
from .drift import DatasetDriftReport, DriftMonitor, FeatureDrift
from .governance import IntendedUse, RunManifest
from .lifecycle import ReleaseLifecycleRecord, ReleaseState, RevalidationAssessment
from .modalities import CapabilityLevel, CapabilityRegistry, DataAsset, DataBundle, Modality
from .profile import DatasetProfile, EngineeringProfiler
from .preprocessing import TabularPreparationReport, find_nested_columns, prepare_messy_table
from .privacy_evidence import DifferentialPrivacyEvidence
from .rare_events import RareEventGenerator, RareEventReport, RareEventSpec
from .relational import Relationship, RelationalIntegrityReport, RelationalSynthesizer
from .release import ReleaseAssessment, ReleaseDecision, ReleasePolicy, RiskTier, SyntheticReleaseGate
from .router import GeneratorDecision, IndustrialModelRouter
from .scenarios import AcceptanceCriterion, ScenarioAssessment, ScenarioDefinition, assess_scenario
from .sequences import SequenceReport, TimeSeriesBlockSynthesizer
from .unstructured import TextSafetyReport, UnstructuredPrivacyProcessor

__all__ = [
    "ComplianceGate",
    "AdapterDescriptor",
    "AdapterPolicy",
    "AdapterRegistry",
    "AdapterRequest",
    "AdapterResponse",
    "DataBoundary",
    "ApprovalEvidence",
    "has_approval",
    "ComplianceControlCatalog",
    "ControlAssessment",
    "ControlRequirement",
    "ComplianceReport",
    "ConstraintReport",
    "DataCard",
    "DatasetProfile",
    "EngineeringConstraintSet",
    "EngineeringProfiler",
    "TabularPreparationReport",
    "find_nested_columns",
    "prepare_messy_table",
    "DifferentialPrivacyEvidence",
    "EvaluationReport",
    "list_domain_packs",
    "load_domain_pack",
    "validate_domain_pack",
    "DatasetDriftReport",
    "DriftMonitor",
    "FeatureDrift",
    "GenerationResult",
    "GeneratorDecision",
    "GenuityAxiomEngine",
    "AxiomEnterpriseEngine",
    "PramanaEnterpriseEngine",
    "IndustrialModelRouter",
    "AcceptanceCriterion",
    "ScenarioAssessment",
    "ScenarioDefinition",
    "assess_scenario",
    "IntendedUse",
    "RunManifest",
    "ReleaseLifecycleRecord",
    "ReleaseState",
    "RevalidationAssessment",
    "CapabilityLevel",
    "CapabilityRegistry",
    "DataAsset",
    "DataBundle",
    "Modality",
    "RareEventGenerator",
    "RareEventReport",
    "RareEventSpec",
    "Relationship",
    "RelationalIntegrityReport",
    "RelationalSynthesizer",
    "ReleaseAssessment",
    "ReleaseDecision",
    "ReleasePolicy",
    "RiskTier",
    "SyntheticReleaseGate",
    "SequenceReport",
    "TimeSeriesBlockSynthesizer",
    "TextSafetyReport",
    "UnstructuredPrivacyProcessor",
    "PramanaEngine",
    "PrivacyPolicy",
    "Rule",
    "SynthesisConfig",
]

__version__ = "0.3.0"
