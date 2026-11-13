from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from app.contracts import (
    C1EnvironmentalInput,
    C2FarmDefinition,
    C3ScientificState,
    C5Comparison,
    C7ModelCapability,
    Provenance,
    SimulationPeriod,
)
from app.models import (
    DecisionBranch,
    EnvironmentalSnapshot,
    ScientificState,
    SimulationComparison,
    SimulationRun,
)
from app.services.analysis.models import AnalysisRequest, EvidenceBundle
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


class AnalysisEvidenceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class EvidenceBundleBuilder:
    """Build analysis evidence from farm records and persisted scientific artifacts."""

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
        missing_evidence: list[str] = []
        provenance_list: list[Provenance] = []

        farm_resp = await self.onboarding_service.get_farm(request.farm_id)
        if farm_resp is None:
            raise KeyError(f"Farm with ID '{request.farm_id}' was not found.")
        farm_contract = farm_resp.to_c2_definition()

        plot_resp = await self.onboarding_service.get_plot(request.farm_id, request.plot_id)
        if plot_resp is None:
            raise KeyError(
                f"Plot with ID '{request.plot_id}' was not found under farm '{request.farm_id}'."
            )
        plot_contract = plot_resp.to_contract_plot()

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

        selected_branch_id = request.branch_id
        selected_branch: DecisionBranch | None = None
        if self.session is None and request.simulation_run_id is not None:
            raise AnalysisEvidenceError(
                "PERSISTED_EVIDENCE_UNAVAILABLE",
                "A selected simulation run cannot be retrieved without the database.",
                503,
            )
        if selected_branch_id is not None and self.session is not None:
            selected_branch = await self.session.get(DecisionBranch, selected_branch_id)
            if (
                selected_branch is None
                or selected_branch.farm_id != farm_contract.farm_id
                or selected_branch.plot_id != plot_contract.plot_id
            ):
                raise AnalysisEvidenceError(
                    "BRANCH_SCOPE_MISMATCH",
                    "The selected branch does not belong to this farm and plot.",
                    404,
                )

        actual_c5_comparison: C5Comparison | None = c5_comparison
        comparison_metadata: dict[str, Any] | None = None
        comparison_requested = request.comparison_id is not None or (
            request.branch_id is not None and request.comparison_branch_id is not None
        )
        if c5_comparison is not None:
            provenance_list.extend(c5_comparison.provenance)
            comparison_metadata = {
                "status": "provided",
                "matchedInputs": c5_comparison.matched_inputs,
                "branchA": c5_comparison.branch_a,
                "branchB": c5_comparison.branch_b,
            }
        elif request.include_comparison and comparison_requested:
            actual_c5_comparison, comparison_metadata = await self._load_comparison(request)
            if actual_c5_comparison is not None:
                provenance_list.extend(actual_c5_comparison.provenance)
            elif comparison_metadata and comparison_metadata.get("status") != "not_comparable":
                missing_evidence.append("c5_comparison")

        selected_run: SimulationRun | None = None
        simulation_metadata: dict[str, Any] | None = None
        if self.session is not None and (
            request.include_simulation or request.simulation_run_id is not None
        ):
            run_request = request
            comparison_run_id = (comparison_metadata or {}).get("runA")
            if request.simulation_run_id is None and comparison_run_id is not None:
                run_request = request.model_copy(
                    update={"simulation_run_id": comparison_run_id}
                )
            selected_run = await self._select_run(
                request=run_request,
                farm_id=farm_contract.farm_id,
                plot_id=plot_contract.plot_id,
            )
            if selected_run is not None:
                if request.branch_id is not None and selected_run.branch_id != request.branch_id:
                    raise AnalysisEvidenceError(
                        "RUN_BRANCH_MISMATCH",
                        "The selected simulation run does not belong to the requested branch.",
                    )
                selected_branch_id = selected_run.branch_id
                if selected_branch is None:
                    selected_branch = await self.session.get(
                        DecisionBranch, selected_run.branch_id
                    )
                if (
                    selected_branch is None
                    or selected_branch.farm_id != farm_contract.farm_id
                    or selected_branch.plot_id != plot_contract.plot_id
                ):
                    raise AnalysisEvidenceError(
                        "RUN_BRANCH_SCOPE_MISMATCH",
                        "The selected simulation run's branch does not belong to this farm and plot.",
                    )
                simulation_metadata = self._run_metadata(selected_run)
            elif request.simulation_run_id is not None:
                raise AnalysisEvidenceError(
                    "SIMULATION_RUN_NOT_FOUND",
                    "The selected simulation run was not found for this farm and plot.",
                    404,
                )
            else:
                missing_evidence.append("completed_simulation_run")

        if request.branch_id is not None and self.session is None:
            missing_evidence.append("selected_branch")

        actual_c3_states: list[C3ScientificState] = []
        if c3_states is not None:
            actual_c3_states = list(c3_states)
        elif request.include_simulation:
            actual_c3_states = await self._load_states(
                selected_run=selected_run,
                farm_id=farm_contract.farm_id,
                plot_id=plot_contract.plot_id,
            )
        if not actual_c3_states:
            missing_evidence.append("c3_simulation_states")
        for state in actual_c3_states:
            provenance_list.extend(state.provenance)

        c1_input: C1EnvironmentalInput | None = None
        environmental_metadata: dict[str, Any] = {
            "source": "not_retrieved",
            "snapshotId": None,
            "inputHash": None,
            "retrievedAt": None,
        }
        selected_run_is_authoritative = selected_run is not None
        if selected_run_is_authoritative:
            environmental_metadata.update(
                {
                    "source": "simulation_snapshot",
                    "snapshotId": selected_run.environmental_snapshot_id,
                    "inputHash": selected_run.input_hash,
                }
            )
            if selected_run.environmental_snapshot_id is None:
                missing_evidence.append("simulation_environmental_snapshot")
            else:
                c1_input, snapshot_metadata = await self._load_run_snapshot(
                    selected_run, farm_contract
                )
                environmental_metadata.update(snapshot_metadata)
                if c1_input is None:
                    missing_evidence.append("c1_simulation_snapshot")
        elif c1_override is not None:
            c1_input = c1_override
            environmental_metadata.update(
                {
                    "source": "trusted_override",
                    "inputHash": None,
                    "retrievedAt": c1_override.retrieved_at,
                }
            )
            provenance_list.extend(c1_override.provenance)
        elif request.include_weather or request.include_soil:
            start_date = plot_contract.planting_date or (date.today() - timedelta(days=7))
            period = SimulationPeriod(startDate=start_date, endDate=start_date + timedelta(days=14))
            member_id = selected_branch.weather_member_id if selected_branch is not None else None
            env_request = EnvironmentalInputRequest(
                farmId=farm_contract.farm_id,
                plotId=plot_contract.plot_id,
                location=farm_contract.location,
                timezone=farm_contract.timezone,
                simulationPeriod=period,
                cropId=plot_contract.crop_id,
                weatherMemberId=member_id,
                includeEnsemble=False,
                requireQuantitativeSimulation=(
                    crop_capability.selected_engine != "identity/ecology-only"
                ),
                forceRefresh=request.force_refresh,
            )
            try:
                env_result = await self.environmental_service.prepare_environmental_input(
                    env_request
                )
                if env_result.c1_input is not None:
                    c1_input = env_result.c1_input
                    environmental_metadata.update(
                        {
                            "source": "new_or_cached_environmental_preparation",
                            "inputHash": env_result.input_hash,
                            "retrievedAt": env_result.retrieved_at or c1_input.retrieved_at,
                            "weatherMemberId": member_id,
                        }
                    )
                    provenance_list.extend(c1_input.provenance)
                else:
                    missing_evidence.append("c1_environmental_input")
                    missing_evidence.extend(
                        f"environmental_error:{item}" for item in env_result.errors
                    )
            except EnvironmentalServiceError as exc:
                logger.warning("Environmental input preparation failed: %s", exc)
                missing_evidence.append("c1_environmental_service_error")
            except (TypeError, ValueError) as exc:
                logger.warning("Environmental input could not be validated: %s", exc)
                missing_evidence.append("c1_environmental_input_invalid")
        else:
            missing_evidence.append("c1_environmental_input_omitted")

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
            simulationMetadata=simulation_metadata,
            environmentalMetadata=environmental_metadata,
            comparisonMetadata=comparison_metadata,
        )

    async def _select_run(
        self, request: AnalysisRequest, farm_id: UUID, plot_id: UUID
    ) -> SimulationRun | None:
        assert self.session is not None
        if request.simulation_run_id is not None:
            run = await self.session.get(SimulationRun, request.simulation_run_id)
            if run is None or run.farm_id != farm_id or run.plot_id != plot_id:
                raise AnalysisEvidenceError(
                    "SIMULATION_RUN_SCOPE_MISMATCH",
                    "The selected simulation run does not belong to this farm and plot.",
                    404,
                )
            return run

        statement = select(SimulationRun).where(
            SimulationRun.farm_id == farm_id,
            SimulationRun.plot_id == plot_id,
            SimulationRun.status == "completed",
            SimulationRun.completed_at.is_not(None),
        )
        if request.branch_id is not None:
            statement = statement.where(SimulationRun.branch_id == request.branch_id)
        statement = statement.order_by(
            SimulationRun.completed_at.desc(),
            SimulationRun.requested_at.desc(),
            SimulationRun.id.desc(),
        ).limit(1)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def _load_states(
        self, selected_run: SimulationRun | None, farm_id: UUID, plot_id: UUID
    ) -> list[C3ScientificState]:
        if selected_run is None or selected_run.status != "completed":
            return []
        assert self.session is not None
        result = await self.session.execute(
            select(ScientificState)
            .where(
                ScientificState.simulation_run_id == selected_run.id,
                ScientificState.plot_id == plot_id,
                ScientificState.branch_id == selected_run.branch_id,
            )
            .order_by(ScientificState.state_date.asc(), ScientificState.id.asc())
        )
        states: list[C3ScientificState] = []
        for record in result.scalars().all():
            try:
                state = C3ScientificState.model_validate(record.payload)
            except Exception as exc:
                raise AnalysisEvidenceError(
                    "INVALID_SCIENTIFIC_STATE",
                    "A persisted scientific state does not match the C3 contract.",
                ) from exc
            if (
                state.farm_id != farm_id
                or state.plot_id != plot_id
                or state.branch_id != selected_run.branch_id
                or state.simulation_run_id != selected_run.id
                or record.state_date != state.date
                or record.availability != state.availability.status.value
            ):
                raise AnalysisEvidenceError(
                    "SCIENTIFIC_STATE_SCOPE_MISMATCH",
                    "A persisted scientific state does not match its run, plot, branch, or date.",
                )
            states.append(state)
        return states

    async def _load_run_snapshot(
        self, run: SimulationRun, farm: C2FarmDefinition
    ) -> tuple[C1EnvironmentalInput | None, dict[str, Any]]:
        assert self.session is not None
        snapshot = await self.session.get(EnvironmentalSnapshot, run.environmental_snapshot_id)
        if (
            snapshot is None
            or snapshot.farm_id != run.farm_id
            or snapshot.plot_id != run.plot_id
        ):
            raise AnalysisEvidenceError(
                "SNAPSHOT_SCOPE_MISMATCH",
                "The simulation run's environmental snapshot does not match its farm and plot.",
            )
        if snapshot.input_hash != run.input_hash:
            raise AnalysisEvidenceError(
                "SNAPSHOT_HASH_MISMATCH",
                "The simulation run and environmental snapshot have different input hashes.",
            )
        raw_c1 = snapshot.payload.get("c1Input")
        if not isinstance(raw_c1, dict):
            raise AnalysisEvidenceError(
                "SNAPSHOT_C1_MISSING",
                "The selected simulation snapshot does not contain a C1 environmental input.",
            )
        try:
            c1_input = C1EnvironmentalInput.model_validate(raw_c1)
        except Exception as exc:
            raise AnalysisEvidenceError(
                "INVALID_C1_SNAPSHOT", "The persisted environmental input does not match C1."
            ) from exc
        if c1_input.farm_id != run.farm_id or farm.farm_id != run.farm_id:
            raise AnalysisEvidenceError(
                "SNAPSHOT_FARM_MISMATCH",
                "The persisted C1 farm identity does not match the requested farm.",
            )

        members = {row.ensemble_member_id for row in c1_input.daily_weather if row.ensemble_member_id}
        if run.weather_member_id:
            if members and run.weather_member_id not in members:
                raise AnalysisEvidenceError(
                    "WEATHER_MEMBER_MISMATCH",
                    "The run's weather member is absent from its C1 snapshot.",
                )
            c1_input.daily_weather = [
                row
                for row in c1_input.daily_weather
                if row.ensemble_member_id in (None, run.weather_member_id)
            ]
        elif len(members) > 1:
            raise AnalysisEvidenceError(
                "WEATHER_MEMBER_AMBIGUOUS",
                "The run does not identify one weather member for its multi-member snapshot.",
            )
        elif members:
            run_member = next(iter(members))
            c1_input.daily_weather = [
                row for row in c1_input.daily_weather if row.ensemble_member_id == run_member
            ]

        return c1_input, {
            "snapshotId": snapshot.id,
            "inputHash": snapshot.input_hash,
            "retrievedAt": c1_input.retrieved_at,
            "snapshotCreatedAt": snapshot.created_at,
            "weatherMemberId": run.weather_member_id,
            "availability": snapshot.availability,
            "provenance": [item.model_dump(by_alias=True, mode="json") for item in c1_input.provenance],
        }

    @staticmethod
    def _run_metadata(run: SimulationRun) -> dict[str, Any]:
        return {
            "simulationRunId": run.id,
            "farmId": run.farm_id,
            "plotId": run.plot_id,
            "branchId": run.branch_id,
            "environmentalSnapshotId": run.environmental_snapshot_id,
            "engine": run.engine_name,
            "engineVersion": run.engine_version,
            "parameterVersion": run.parameter_version,
            "status": run.status,
            "requestedAt": run.requested_at,
            "startedAt": run.started_at,
            "completedAt": run.completed_at,
            "inputHash": run.input_hash,
            "weatherRealizationId": run.weather_realization_id,
            "weatherMemberId": run.weather_member_id,
            "warnings": run.warnings or [],
            "scienceEnvelope": run.science_envelope,
            "inputProvenance": run.input_provenance,
        }

    async def _load_comparison(
        self, request: AnalysisRequest
    ) -> tuple[C5Comparison | None, dict[str, Any]]:
        if self.session is None:
            return None, {"status": "missing"}
        comparison: SimulationComparison | None
        if request.comparison_id is not None:
            comparison = await self.session.get(SimulationComparison, request.comparison_id)
            if (
                comparison is None
                or comparison.farm_id != request.farm_id
                or comparison.plot_id != request.plot_id
            ):
                raise AnalysisEvidenceError(
                    "COMPARISON_SCOPE_MISMATCH",
                    "The selected comparison was not found for this farm and plot.",
                    404,
                )
        else:
            result = await self.session.execute(
                select(SimulationComparison)
                .where(
                    SimulationComparison.farm_id == request.farm_id,
                    SimulationComparison.plot_id == request.plot_id,
                    SimulationComparison.branch_a_id == request.branch_id,
                    SimulationComparison.branch_b_id == request.comparison_branch_id,
                )
                .order_by(
                    SimulationComparison.comparison_date.desc(),
                    SimulationComparison.id.desc(),
                )
                .limit(1)
            )
            comparison = result.scalar_one_or_none()
            if comparison is None:
                return None, {"status": "missing"}

        pair = (comparison.branch_a_id, comparison.branch_b_id)
        if request.branch_id is not None and pair[0] != request.branch_id:
            raise AnalysisEvidenceError(
                "COMPARISON_BRANCH_MISMATCH",
                "The comparison baseline does not match the requested branch.",
            )
        if request.comparison_branch_id is not None and pair[1] != request.comparison_branch_id:
            raise AnalysisEvidenceError(
                "COMPARISON_BRANCH_MISMATCH",
                "The comparison alternative does not match the requested comparison branch.",
            )
        for branch_id in pair:
            branch = await self.session.get(DecisionBranch, branch_id)
            if (
                branch is None
                or branch.farm_id != comparison.farm_id
                or branch.plot_id != comparison.plot_id
            ):
                raise AnalysisEvidenceError(
                    "COMPARISON_BRANCH_SCOPE_MISMATCH",
                    "A comparison branch does not belong to its recorded farm and plot.",
                )

        run_a = await self._comparison_run(comparison.run_a_id, comparison, comparison.branch_a_id)
        run_b = await self._comparison_run(comparison.run_b_id, comparison, comparison.branch_b_id)
        if request.simulation_run_id is not None:
            if request.branch_id == comparison.branch_a_id:
                run_matches = request.simulation_run_id == run_a.id
            elif request.branch_id == comparison.branch_b_id:
                run_matches = request.simulation_run_id == run_b.id
            else:
                run_matches = request.simulation_run_id in (run_a.id, run_b.id)
            if not run_matches:
                raise AnalysisEvidenceError(
                    "COMPARISON_RUN_MISMATCH",
                    "The selected simulation run is not the run associated with the requested comparison branch.",
                )
        payload = comparison.payload or {}
        self._validate_comparison_provenance(payload.get("provenance"), run_a, run_b)
        result_payload = payload.get("result") or {}
        c5_payload = result_payload.get("c5")
        reasons = list(comparison.non_comparable_reasons or result_payload.get("reasons") or [])
        metadata = {
            "comparisonId": comparison.id,
            "farmId": comparison.farm_id,
            "plotId": comparison.plot_id,
            "branchA": comparison.branch_a_id,
            "branchB": comparison.branch_b_id,
            "runA": comparison.run_a_id,
            "runB": comparison.run_b_id,
            "comparisonDate": comparison.comparison_date,
            "createdAt": payload.get("createdAt") or comparison.created_at,
            "status": comparison.status,
            "matchedInputs": comparison.matched_inputs,
            "reasons": reasons,
            "provenance": payload.get("provenance"),
        }
        if (
            comparison.status != "comparable"
            or not comparison.matched_inputs
            or result_payload.get("status") != "comparable"
            or not isinstance(c5_payload, dict)
        ):
            metadata["status"] = "not_comparable"
            return None, metadata

        try:
            c5 = C5Comparison.model_validate(c5_payload)
        except Exception as exc:
            raise AnalysisEvidenceError(
                "INVALID_C5_COMPARISON", "The persisted comparison does not match C5."
            ) from exc
        if (
            c5.branch_a != comparison.branch_a_id
            or c5.branch_b != comparison.branch_b_id
            or c5.comparison_date != comparison.comparison_date
            or not c5.matched_inputs
            or c5.availability.status.value != "available"
        ):
            raise AnalysisEvidenceError(
                "C5_COMPARISON_SCOPE_MISMATCH",
                "The persisted C5 branch pair, date, or availability does not match its comparison.",
            )
        expected_sources = {
            run_a.id: run_a,
            run_b.id: run_b,
        }
        verified_sources: set[UUID] = set()
        for source in c5.provenance:
            try:
                run_id = UUID(source.source_id.removeprefix("simulation:"))
            except ValueError as exc:
                raise AnalysisEvidenceError(
                    "C5_PROVENANCE_MISMATCH",
                    "A C5 provenance entry does not identify a comparison run.",
                ) from exc
            run = expected_sources.get(run_id)
            if (
                run is None
                or source.source_version != run.engine_version
                or source.reference != run.input_hash
                or source.retrieved_at != (run.completed_at or run.requested_at)
            ):
                raise AnalysisEvidenceError(
                    "C5_PROVENANCE_MISMATCH",
                    "C5 input provenance does not match the recorded simulation runs.",
                )
            verified_sources.add(run_id)
        if verified_sources != set(expected_sources):
            raise AnalysisEvidenceError(
                "C5_PROVENANCE_MISMATCH",
                "C5 provenance must identify both compared simulation runs.",
            )
        return c5, metadata

    async def _comparison_run(
        self,
        run_id: UUID,
        comparison: SimulationComparison,
        branch_id: UUID,
    ) -> SimulationRun:
        assert self.session is not None
        run = await self.session.get(SimulationRun, run_id)
        if (
            run is None
            or run.farm_id != comparison.farm_id
            or run.plot_id != comparison.plot_id
            or run.branch_id != branch_id
            or run.status != "completed"
        ):
            raise AnalysisEvidenceError(
                "COMPARISON_RUN_SCOPE_MISMATCH",
                "A comparison run is missing, incomplete, or does not match its farm, plot, and branch.",
            )
        return run

    @staticmethod
    def _validate_comparison_provenance(
        provenance: dict[str, Any] | None, run_a: SimulationRun, run_b: SimulationRun
    ) -> None:
        if not isinstance(provenance, dict):
            raise AnalysisEvidenceError(
                "COMPARISON_PROVENANCE_MISSING", "Persisted comparison provenance is missing."
            )
        for key, run in (("baseline", run_a), ("alternative", run_b)):
            source = provenance.get(key)
            if not isinstance(source, dict) or any(
                source.get(field) != expected
                for field, expected in {
                    "simulationRunId": str(run.id),
                    "farmId": str(run.farm_id),
                    "plotId": str(run.plot_id),
                    "branchId": str(run.branch_id),
                    "inputHash": run.input_hash,
                    "environmentalSnapshotId": (
                        str(run.environmental_snapshot_id) if run.environmental_snapshot_id else None
                    ),
                    "engine": run.engine_name,
                    "engineVersion": run.engine_version,
                    "parameterVersion": run.parameter_version,
                    "weatherRealizationId": run.weather_realization_id,
                    "weatherMemberId": run.weather_member_id,
                    "scienceInputHash": (run.science_envelope or {}).get("inputHash"),
                    "inputProvenance": run.input_provenance,
                }.items()
            ):
                raise AnalysisEvidenceError(
                    "COMPARISON_PROVENANCE_MISMATCH",
                    "Persisted comparison provenance does not match its simulation runs.",
                )
