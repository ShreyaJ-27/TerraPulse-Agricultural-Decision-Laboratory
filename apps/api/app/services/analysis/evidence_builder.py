from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import ClassVar
from uuid import UUID

from app.contracts import (
    C1EnvironmentalInput,
    C3ScientificState,
    C5Comparison,
    C7ModelCapability,
    Provenance,
    SimulationPeriod,
)
from app.models import ScientificState, SimulationRun
from app.services.analysis.models import (
    AnalysisRequest,
    EvidenceBundle,
)
from app.services.crop_lens.registry import get_crop_by_id
from app.services.crop_lens.resolver import CropLensResolver
from app.services.environmental import (
    EnvironmentalInputRequest,
    EnvironmentalInputService,
    EnvironmentalServiceError,
)
from app.services.onboarding import OnboardingService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("terrapulse.analysis.evidence_builder")


class EvidenceBundleBuilder:
    """Retrieves and consolidates authoritative backend evidence across Onboarding, CropLens,

    Environmental (C1), Scientific (C3), and Comparison (C5) services.
    """

    _in_memory_simulation_states: ClassVar[dict[UUID, list[C3ScientificState]]] = {}
    _in_memory_comparisons: ClassVar[dict[UUID, C5Comparison]] = {}

    def __init__(
        self,
        onboarding_service: OnboardingService,
        crop_resolver: CropLensResolver,
        environmental_service: EnvironmentalInputService,
        session: AsyncSession | None = None,
    ) -> None:
        self.onboarding_service = onboarding_service
        self.crop_resolver = crop_resolver
        self.environmental_service = environmental_service
        self.session = session or getattr(onboarding_service, "session", None)

    async def build(
        self,
        request: AnalysisRequest,
        c3_states: list[C3ScientificState] | None = None,
        c5_comparison: C5Comparison | None = None,
        c1_override: C1EnvironmentalInput | None = None,
    ) -> EvidenceBundle:
        """Assembles a consolidated EvidenceBundle for the requested farm and plot."""
        missing_evidence: list[str] = []
        provenance_list: list[Provenance] = []

        # 1. Retrieve Farm
        farm_resp = await self.onboarding_service.get_farm(request.farm_id)
        if farm_resp is None:
            raise KeyError(f"Farm with ID '{request.farm_id}' was not found.")
        farm_contract = farm_resp.to_c2_definition()

        # 2. Retrieve Plot (ownership check enforced: plot must belong to requested farm)
        plot_resp = await self.onboarding_service.get_plot(request.farm_id, request.plot_id)
        if plot_resp is None:
            raise KeyError(f"Plot with ID '{request.plot_id}' was not found under farm '{request.farm_id}'.")
        plot_contract = plot_resp.to_contract_plot()

        # 3. Resolve Crop & Capability
        crop_record = get_crop_by_id(plot_contract.crop_id) if plot_contract.crop_id else None
        if crop_record is not None:
            crop_canonical_name = crop_record.canonical_name
            crop_scientific_name = crop_record.scientific_name
            crop_capability = crop_record.to_c7_capability()
        else:
            crop_canonical_name = "Unknown Crop"
            crop_scientific_name = None
            crop_capability = C7ModelCapability(
                contractVersion="1.0",
                cropId=plot_contract.crop_id or request.plot_id,
                acceptedCropNames=["unknown"],
                scientificName=None,
                selectedEngine="identity/ecology-only",
                engineVersion="1.0",
                supportedOutputs=[],
                modelParameters={},
                parameterSources=[],
                parameterVersions=[],
                knownLimitations=["Unregistered crop identity"],
                provenanceReferences=[],
            )
            missing_evidence.append("crop_capability")

        provenance_list.append(
            Provenance(
                sourceId=f"terrapulse-onboarding-c2-{farm_contract.farm_id}",
                sourceVersion="1.0",
                retrievedAt=datetime.now(UTC),
                reference=f"farm:{farm_contract.farm_id}/plot:{plot_contract.plot_id}",
            )
        )

        # 4. Prepare C1 Environmental Input
        c1_input: C1EnvironmentalInput | None = c1_override
        if c1_input is None and (request.include_weather or request.include_soil):
            start_d = plot_contract.planting_date or (date.today() - timedelta(days=7))
            end_d = start_d + timedelta(days=14)
            sim_period = SimulationPeriod(startDate=start_d, endDate=end_d)

            req = EnvironmentalInputRequest(
                farmId=farm_contract.farm_id,
                plotId=plot_contract.plot_id,
                location=farm_contract.location,
                timezone=farm_contract.timezone,
                simulationPeriod=sim_period,
                cropId=plot_contract.crop_id,
                weatherMemberId=request.branch_id and str(request.branch_id),
                requireQuantitativeSimulation=crop_capability.selected_engine != "identity/ecology-only",
                forceRefresh=request.force_refresh,
            )

            try:
                env_result = await self.environmental_service.prepare_environmental_input(req)
                if env_result.c1_input is not None:
                    c1_input = env_result.c1_input
                    provenance_list.extend(c1_input.provenance)
                else:
                    missing_evidence.append("c1_environmental_input")
                    if env_result.errors:
                        missing_evidence.extend([f"environmental_error: {e}" for e in env_result.errors])
            except EnvironmentalServiceError as exc:
                logger.warning("Environmental input preparation failed: %s", exc)
                missing_evidence.append(f"c1_environmental_service_error: {exc}")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unexpected error during environmental input preparation: %s", exc)
                missing_evidence.append(f"c1_unexpected_error: {exc}")
        elif c1_input is not None:
            provenance_list.extend(c1_input.provenance)
        else:
            missing_evidence.append("c1_environmental_input_omitted")

        # 5. Scientific States (C3): retrieve from memory, persistence, or record missing
        actual_c3_states: list[C3ScientificState] = []
        if request.include_simulation:
            if c3_states:
                actual_c3_states = list(c3_states)
                for s in actual_c3_states:
                    provenance_list.extend(s.provenance)
            elif request.simulation_run_id is not None:
                # Attempt retrieval from SQL persistence if session is configured
                if self.session is not None:
                    try:
                        run_stmt = select(SimulationRun).where(
                            SimulationRun.id == request.simulation_run_id,
                            SimulationRun.farm_id == farm_contract.farm_id,
                            SimulationRun.plot_id == plot_contract.plot_id,
                        )
                        run_res = await self.session.execute(run_stmt)
                        db_run = run_res.scalar_one_or_none()
                        if db_run is not None:
                            state_stmt = (
                                select(ScientificState)
                                .where(
                                    ScientificState.simulation_run_id == request.simulation_run_id,
                                    ScientificState.plot_id == plot_contract.plot_id,
                                )
                                .order_by(ScientificState.state_date)
                            )
                            state_res = await self.session.execute(state_stmt)
                            db_states = state_res.scalars().all()
                            for st in db_states:
                                c3_obj = C3ScientificState.model_validate(st.payload)
                                actual_c3_states.append(c3_obj)
                                provenance_list.extend(c3_obj.provenance)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Failed to query persisted simulation states: %s", exc)
                # Check in-memory simulation store (used for unit/integration tests)
                elif request.simulation_run_id in self._in_memory_simulation_states:
                    actual_c3_states = list(self._in_memory_simulation_states[request.simulation_run_id])
                    for s in actual_c3_states:
                        provenance_list.extend(s.provenance)

            if not actual_c3_states:
                missing_evidence.append("c3_simulation_states")

        # 6. Comparison (C5): retrieve from memory, store, or record missing
        actual_c5_comparison: C5Comparison | None = None
        if request.include_comparison:
            if c5_comparison:
                actual_c5_comparison = c5_comparison
                provenance_list.extend(c5_comparison.provenance)
            elif (
                request.comparison_branch_id is not None
                and request.comparison_branch_id in self._in_memory_comparisons
            ):
                actual_c5_comparison = self._in_memory_comparisons[request.comparison_branch_id]
                provenance_list.extend(actual_c5_comparison.provenance)

            if actual_c5_comparison is None:
                missing_evidence.append("c5_comparison")

        return EvidenceBundle(
            farm=farm_contract,
            plot=plot_contract,
            cropCanonicalName=crop_canonical_name,
            cropScientificName=crop_scientific_name,
            cropCapability=crop_capability,
            c1Input=c1_input,
            c3States=actual_c3_states,
            c5Comparison=actual_c5_comparison,
            provenance=provenance_list,
            missingEvidence=missing_evidence,
        )
