from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.contracts import (
    C1EnvironmentalInput,
    C3ScientificState,
    C5Comparison,
)
from app.services.analysis.deterministic_explainer import DeterministicExplainer
from app.services.analysis.evidence_builder import EvidenceBundleBuilder
from app.services.analysis.guardrails import GuardrailEvaluator
from app.services.analysis.llm_client import AnalysisLlmClient
from app.services.analysis.models import (
    AnalysisRequest,
    AnalysisResponseData,
    AnalysisSection,
    EvidenceSummary,
    GroundedClaim,
)
from app.services.analysis.staleness import StalenessEvaluator
from app.services.analysis.validator import QuantitativeClaimValidator
from app.services.crop_lens.resolver import CropLensResolver
from app.services.environmental import EnvironmentalInputService
from app.services.onboarding import OnboardingService

logger = logging.getLogger("terrapulse.analysis.service")


class EvidenceGroundedAnalysisService:
    """End-to-end orchestration service providing evidence-grounded agro-ecological analysis

    with strict zero-hallucination guarantees, domain guardrails, staleness flagging, and
    deterministic multi-lingual fallbacks.
    """

    def __init__(
        self,
        onboarding_service: OnboardingService,
        crop_resolver: CropLensResolver,
        environmental_service: EnvironmentalInputService,
        llm_client: AnalysisLlmClient | None = None,
        evidence_builder: EvidenceBundleBuilder | None = None,
    ) -> None:
        self.onboarding_service = onboarding_service
        self.crop_resolver = crop_resolver
        self.environmental_service = environmental_service
        self.llm_client = llm_client or AnalysisLlmClient()
        self.evidence_builder = evidence_builder or EvidenceBundleBuilder(
            onboarding_service=onboarding_service,
            crop_resolver=crop_resolver,
            environmental_service=environmental_service,
        )

    async def analyze(
        self,
        request: AnalysisRequest,
        c3_states: list[C3ScientificState] | None = None,
        c5_comparison: C5Comparison | None = None,
        c1_override: C1EnvironmentalInput | None = None,
    ) -> AnalysisResponseData:
        """Executes the complete 7-stage evidence-grounded analysis pipeline."""
        analysis_id = uuid4()
        created_at = datetime.now(UTC)

        # 1. Retrieve and assemble authoritative evidence bundle
        bundle = await self.evidence_builder.build(
            request=request,
            c3_states=c3_states,
            c5_comparison=c5_comparison,
            c1_override=c1_override,
        )

        # 2. Guardrails and escalation assessment
        guardrail_status, limitations, escalations = GuardrailEvaluator.evaluate(
            question=request.question,
            bundle=bundle,
            language=request.language,
        )

        # 3. Staleness and data quality checks
        staleness_assessments = StalenessEvaluator.evaluate(
            bundle=bundle,
            now=created_at,
            language=request.language,
        )

        # 4. Construct evidence summary
        weather_days_count = len(bundle.c1_input.daily_weather) if bundle.c1_input else 0
        soil_avail = (bundle.c1_input is not None and bundle.c1_input.soil is not None)
        evidence_summary = EvidenceSummary(
            farmId=bundle.farm.farm_id,
            plotId=bundle.plot.plot_id,
            cropCanonicalName=bundle.crop_canonical_name,
            cropScientificName=bundle.crop_scientific_name,
            cropEngine=bundle.crop_capability.selected_engine,
            cropEngineVersion=bundle.crop_capability.engine_version,
            c1Available=bundle.c1_input is not None,
            weatherDaysCount=weather_days_count,
            soilAvailable=soil_avail,
            c3StatesCount=len(bundle.c3_states),
            c5ComparisonAvailable=bundle.c5_comparison is not None,
            missingFields=list(bundle.missing_evidence),
            branchId=(bundle.simulation_metadata or {}).get("branchId"),
            simulationRunId=(bundle.simulation_metadata or {}).get("simulationRunId"),
            simulationStatus=(bundle.simulation_metadata or {}).get("status"),
            simulationCompletedAt=(bundle.simulation_metadata or {}).get("completedAt"),
            simulationEngine=(bundle.simulation_metadata or {}).get("engine"),
            simulationEngineVersion=(bundle.simulation_metadata or {}).get("engineVersion"),
            parameterVersion=(bundle.simulation_metadata or {}).get("parameterVersion"),
            simulationWarnings=(bundle.simulation_metadata or {}).get("warnings", []),
            environmentalSnapshotId=bundle.environmental_metadata.get("snapshotId"),
            environmentalInputHash=bundle.environmental_metadata.get("inputHash"),
            environmentalSource=bundle.environmental_metadata.get("source"),
            weatherMemberId=(bundle.simulation_metadata or {}).get("weatherMemberId")
            or bundle.environmental_metadata.get("weatherMemberId"),
            comparisonId=(bundle.comparison_metadata or {}).get("comparisonId"),
            comparisonStatus=(bundle.comparison_metadata or {}).get("status"),
            comparisonMatchedInputs=(bundle.comparison_metadata or {}).get("matchedInputs"),
            comparisonBaselineBranchId=(bundle.comparison_metadata or {}).get("branchA"),
            comparisonAlternativeBranchId=(bundle.comparison_metadata or {}).get("branchB"),
            comparisonBaselineRunId=(bundle.comparison_metadata or {}).get("runA"),
            comparisonAlternativeRunId=(bundle.comparison_metadata or {}).get("runB"),
            comparisonDate=(bundle.comparison_metadata or {}).get("comparisonDate"),
            comparisonAssumptions=(
                bundle.c5_comparison.assumptions if bundle.c5_comparison is not None else []
            ),
            comparisonProvenance=(
                bundle.c5_comparison.provenance if bundle.c5_comparison is not None else []
            ),
            comparisonReasons=(bundle.comparison_metadata or {}).get("reasons", []),
            cropSupportedOutputs=bundle.crop_capability.supported_outputs,
            cropParameterVersions=bundle.crop_capability.parameter_versions,
            cropParameterSources=bundle.crop_capability.parameter_sources,
            cropLimitations=bundle.crop_capability.known_limitations,
        )

        # 5. Explanation Generation & Mode Selection
        summary: str
        sections: list[AnalysisSection]
        claims: list[GroundedClaim]
        generation_mode: str

        if not guardrail_status.passed or guardrail_status.escalation_required:
            # Short-circuit: do NOT invoke LLM when guardrails fail or escalation is required
            generation_mode = "deterministic"
            summary, sections, claims = DeterministicExplainer.generate(
                bundle=bundle,
                staleness=staleness_assessments,
                limitations=limitations,
                escalations=escalations,
                language=request.language,
            )
        else:
            llm_result = None
            if self.llm_client.is_configured and request.question:
                llm_result = await self.llm_client.generate_explanation(
                    bundle=bundle,
                    question=request.question,
                    language=request.language,
                )

            if llm_result is not None:
                summary, sections, claims = llm_result
                generation_mode = "llm"
            else:
                generation_mode = "deterministic_fallback" if self.llm_client.is_configured else "deterministic"
                summary, sections, claims = DeterministicExplainer.generate(
                    bundle=bundle,
                    staleness=staleness_assessments,
                    limitations=limitations,
                    escalations=escalations,
                    language=request.language,
                )

        # 6. Verify Claims Grounding
        is_valid, validation_errors = QuantitativeClaimValidator.validate_claims(claims, bundle)
        if not is_valid:
            logger.error("Validation error in generated claims: %s", validation_errors)
            # Re-generate safely via deterministic engine if claims were tainted
            summary, sections, claims = DeterministicExplainer.generate(
                bundle=bundle,
                staleness=staleness_assessments,
                limitations=limitations,
                escalations=escalations,
                language=request.language,
            )
            generation_mode = "deterministic_fallback"

        # 7. Assemble final AnalysisResponseData
        return AnalysisResponseData(
            analysisId=analysis_id,
            farmId=request.farm_id,
            plotId=request.plot_id,
            language=request.language,
            summary=summary,
            sections=sections,
            claims=claims,
            evidenceSummary=evidence_summary,
            dataFreshness=staleness_assessments,
            scientificLimitations=limitations,
            escalations=escalations,
            guardrailStatus=guardrail_status,
            generationMode=generation_mode,  # type: ignore[arg-type]
            createdAt=created_at,
        )
