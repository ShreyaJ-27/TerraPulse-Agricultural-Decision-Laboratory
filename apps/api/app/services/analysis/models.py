from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from app.contracts import (
    C1EnvironmentalInput,
    C2FarmDefinition,
    C3ScientificState,
    C5Comparison,
    C7ModelCapability,
    PlotDefinition,
    Provenance,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

ClaimCategory = Literal[
    "observation",
    "gridded_modelled",
    "simulation_state",
    "comparison_derived",
    "assumption",
]


class GroundedClaim(BaseModel):
    """A single quantitative or categorical claim strictly grounded in evidence."""

    claim_id: str = Field(alias="claimId", description="Unique claim identifier")
    metric: str = Field(description="Name of the parameter or metric")
    value: float = Field(description="The numeric value asserted")
    unit: str = Field(description="Measurement unit")
    source_field: str = Field(alias="sourceField", description="Evidence bundle dot-path source field")
    source_id: str = Field(alias="sourceId", description="Originating provider or model identifier")
    category: ClaimCategory = Field(description="Scientific classification of the asserted claim")
    is_stale: bool = Field(default=False, alias="isStale", description="Whether data exceeds freshness window")
    qualifications: list[str] = Field(
        default_factory=list,
        description="Scientific limitations or assumptions attached to this claim",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class StalenessAssessment(BaseModel):
    """Freshness analysis of an input or simulation artifact."""

    source_id: str = Field(alias="sourceId")
    data_type: str = Field(alias="dataType")
    is_stale: bool = Field(alias="isStale")
    age_hours: float | None = Field(default=None, alias="ageHours")
    freshness_label: str = Field(alias="freshnessLabel")
    warning: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class ScientificLimitation(BaseModel):
    """Explicit declaration of what the underlying biophysical models cannot evaluate."""

    category: str
    code: str
    description: str
    implications: str

    model_config = ConfigDict(populate_by_name=True)


class EscalationNotice(BaseModel):
    """Actionable handover when a query falls outside scientific simulation capabilities."""

    category: str
    reason: str
    recommended_action: str = Field(alias="recommendedAction")
    recommended_authority: str = Field(alias="recommendedAuthority")

    model_config = ConfigDict(populate_by_name=True)


class AnalysisSection(BaseModel):
    """Structured thematic section of the generated evidence-grounded explanation."""

    key: str
    title: str
    content: str
    claims: list[GroundedClaim] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class EvidenceSummary(BaseModel):
    """Metadata summary of evidence retrieved for this analysis."""

    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID = Field(alias="plotId")
    crop_canonical_name: str = Field(alias="cropCanonicalName")
    crop_scientific_name: str | None = Field(default=None, alias="cropScientificName")
    crop_engine: str = Field(alias="cropEngine")
    crop_engine_version: str = Field(alias="cropEngineVersion")
    c1_available: bool = Field(alias="c1Available")
    weather_days_count: int = Field(alias="weatherDaysCount")
    soil_available: bool = Field(alias="soilAvailable")
    c3_states_count: int = Field(alias="c3StatesCount")
    c5_comparison_available: bool = Field(alias="c5ComparisonAvailable")
    missing_fields: list[str] = Field(default_factory=list, alias="missingFields")
    branch_id: UUID | None = Field(default=None, alias="branchId")
    simulation_run_id: UUID | None = Field(default=None, alias="simulationRunId")
    simulation_status: str | None = Field(default=None, alias="simulationStatus")
    simulation_completed_at: datetime | None = Field(default=None, alias="simulationCompletedAt")
    simulation_engine: str | None = Field(default=None, alias="simulationEngine")
    simulation_engine_version: str | None = Field(default=None, alias="simulationEngineVersion")
    parameter_version: str | None = Field(default=None, alias="parameterVersion")
    simulation_warnings: list[str] = Field(default_factory=list, alias="simulationWarnings")
    environmental_snapshot_id: UUID | None = Field(default=None, alias="environmentalSnapshotId")
    environmental_input_hash: str | None = Field(default=None, alias="environmentalInputHash")
    environmental_source: str | None = Field(default=None, alias="environmentalSource")
    weather_member_id: str | None = Field(default=None, alias="weatherMemberId")
    comparison_id: UUID | None = Field(default=None, alias="comparisonId")
    comparison_status: str | None = Field(default=None, alias="comparisonStatus")
    comparison_matched_inputs: bool | None = Field(default=None, alias="comparisonMatchedInputs")
    comparison_baseline_branch_id: UUID | None = Field(default=None, alias="comparisonBaselineBranchId")
    comparison_alternative_branch_id: UUID | None = Field(default=None, alias="comparisonAlternativeBranchId")
    comparison_baseline_run_id: UUID | None = Field(default=None, alias="comparisonBaselineRunId")
    comparison_alternative_run_id: UUID | None = Field(default=None, alias="comparisonAlternativeRunId")
    comparison_date: date | None = Field(default=None, alias="comparisonDate")
    comparison_assumptions: list[str] = Field(default_factory=list, alias="comparisonAssumptions")
    comparison_provenance: list[Provenance] = Field(default_factory=list, alias="comparisonProvenance")
    comparison_reasons: list[str] = Field(default_factory=list, alias="comparisonReasons")
    crop_supported_outputs: list[str] = Field(default_factory=list, alias="cropSupportedOutputs")
    crop_parameter_versions: list[str] = Field(default_factory=list, alias="cropParameterVersions")
    crop_parameter_sources: list[Provenance] = Field(default_factory=list, alias="cropParameterSources")
    crop_limitations: list[str] = Field(default_factory=list, alias="cropLimitations")

    model_config = ConfigDict(populate_by_name=True)


class GuardrailStatus(BaseModel):
    """Record of scientific domain checks, topic filtering, and safety escalations."""

    passed: bool
    flags: list[str] = Field(default_factory=list)
    restricted_topics: list[str] = Field(default_factory=list, alias="restrictedTopics")
    escalation_required: bool = Field(default=False, alias="escalationRequired")

    model_config = ConfigDict(populate_by_name=True)


class AnalysisRequest(BaseModel):
    """Request payload for evidence-grounded AI analysis."""

    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID = Field(alias="plotId")
    branch_id: UUID | None = Field(default=None, alias="branchId")
    comparison_branch_id: UUID | None = Field(default=None, alias="comparisonBranchId")
    comparison_id: UUID | None = Field(default=None, alias="comparisonId")
    simulation_run_id: UUID | None = Field(default=None, alias="simulationRunId")
    question: str | None = None
    language: Literal["en", "kn", "hi"] = "en"
    include_weather: bool = Field(default=True, alias="includeWeather")
    include_soil: bool = Field(default=True, alias="includeSoil")
    include_crop: bool = Field(default=True, alias="includeCrop")
    include_simulation: bool = Field(default=True, alias="includeSimulation")
    include_comparison: bool = Field(default=True, alias="includeComparison")
    force_refresh: bool = Field(default=False, alias="forceRefresh")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def comparison_pair_is_complete(self) -> AnalysisRequest:
        if self.comparison_branch_id is not None and self.branch_id is None:
            raise ValueError("comparisonBranchId requires branchId to identify the comparison pair.")
        return self


class AnalysisResponseData(BaseModel):
    """Data payload inside ApiResponse for evidence-grounded AI analysis."""

    analysis_id: UUID = Field(alias="analysisId")
    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID = Field(alias="plotId")
    language: Literal["en", "kn", "hi"]
    summary: str
    sections: list[AnalysisSection]
    claims: list[GroundedClaim]
    evidence_summary: EvidenceSummary = Field(alias="evidenceSummary")
    data_freshness: list[StalenessAssessment] = Field(alias="dataFreshness")
    scientific_limitations: list[ScientificLimitation] = Field(alias="scientificLimitations")
    escalations: list[EscalationNotice] = Field(default_factory=list)
    guardrail_status: GuardrailStatus = Field(alias="guardrailStatus")
    generation_mode: Literal["deterministic", "llm", "deterministic_fallback"] = Field(alias="generationMode")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class EvidenceBundle(BaseModel):
    """Internal consolidated bundle of authoritative backend evidence."""

    farm: C2FarmDefinition
    plot: PlotDefinition
    crop_canonical_name: str = Field(alias="cropCanonicalName")
    crop_scientific_name: str | None = Field(default=None, alias="cropScientificName")
    crop_capability: C7ModelCapability = Field(alias="cropCapability")
    c1_input: C1EnvironmentalInput | None = Field(default=None, alias="c1Input")
    c3_states: list[C3ScientificState] = Field(default_factory=list, alias="c3States")
    c5_comparison: C5Comparison | None = Field(default=None, alias="c5Comparison")
    provenance: list[Provenance] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list, alias="missingEvidence")
    simulation_metadata: dict[str, Any] | None = Field(default=None, alias="simulationMetadata")
    environmental_metadata: dict[str, Any] = Field(
        default_factory=dict, alias="environmentalMetadata"
    )
    comparison_metadata: dict[str, Any] | None = Field(default=None, alias="comparisonMetadata")

    model_config = ConfigDict(populate_by_name=True)
