from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.contracts import C1EnvironmentalInput
from app.models import (
    BranchDecision,
    DecisionBranch,
    EnvironmentalSnapshot,
    Plot,
    ScientificState,
    SimulationRun,
    TimelineEvent,
)
from app.services.crop_lens.registry import get_crop_by_id
from app.services.resources import ResourceService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def farm_execution_blocker(crop_id: UUID, mapping: str | None = "A") -> tuple[str, str] | None:
    science_path = Path(__file__).parents[5] / "packages" / "science" / "src"
    if str(science_path) not in sys.path:
        sys.path.insert(0, str(science_path))
    from app.services.crop_lens.resolver import CropLensResolver
    from terrapulse_science.contracts import ScienceError
    from terrapulse_science.crop_binding import CropBindingService

    binding = CropBindingService(resolve=CropLensResolver().resolve, get_crop_by_id=get_crop_by_id)
    try:
        binding.bind_canonical_fao(crop_id, turmeric_mapping=mapping)
    except ScienceError as exc:
        return exc.code, exc.message
    return None


class SimulationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_run(self, run_id: UUID) -> SimulationRun | None:
        return await self.session.get(SimulationRun, run_id)

    async def list_runs(self, farm_id: UUID, plot_id: UUID) -> list[SimulationRun]:
        result = await self.session.execute(
            select(SimulationRun)
            .where(SimulationRun.farm_id == farm_id, SimulationRun.plot_id == plot_id)
            .order_by(SimulationRun.requested_at.desc())
        )
        return list(result.scalars())

    async def submit(self, payload) -> SimulationRun:
        plot = await self.session.get(Plot, payload.plot_id)
        if plot is None or plot.farm_id != payload.farm_id:
            raise ValueError("PLOT_FARM_MISMATCH")
        snapshot = await self.session.get(EnvironmentalSnapshot, payload.environmental_snapshot_id)
        if (
            snapshot is None
            or snapshot.farm_id != payload.farm_id
            or snapshot.plot_id != payload.plot_id
        ):
            raise ValueError("SNAPSHOT_OWNERSHIP_MISMATCH")
        if payload.irrigation_mode not in ("rainfed", "irrigated"):
            raise ValueError("INVALID_IRRIGATION_MODE")
        if payload.irrigation_mode == "irrigated" and payload.resource_id is None:
            raise ValueError("C8_LEDGER_REQUIRED")
        crop = get_crop_by_id(plot.crop_id) if plot.crop_id else None
        if crop is None:
            raise ValueError("CROP_IDENTITY_UNRESOLVED")
        capability = crop.to_c7_capability()
        if capability.selected_engine == "identity/ecology-only":
            raise ValueError("CROP_IDENTITY_ONLY")
        if str(plot.crop_id) == "00000000-0000-0000-0000-000000000003" and payload.turmeric_mapping not in ("A", "B", "C"):
            raise ValueError("CROP_MAPPING_REQUIRED")
        blocker = farm_execution_blocker(plot.crop_id, payload.turmeric_mapping)
        if blocker:
            raise ValueError(blocker[0], blocker[1])
        if snapshot.payload.get("isValid") is False:
            raise ValueError("ENVIRONMENT_INVALID", "Prepare valid environmental evidence before running a simulation.")
        branch_id = payload.branch_id
        planting_date = plot.planting_date
        if branch_id is None:
            if "planting" in snapshot.payload:
                certainty = (plot.management or {}).get("plantingDateCertainty")
                if planting_date is None or certainty in {"estimated", "unconfirmed"}:
                    raise ValueError("PLANTING_DATE_REQUIRED", "Confirm the planting date on the plot first.")
                if snapshot.payload["planting"]["date"] != planting_date.isoformat():
                    raise ValueError("PLANTING_DATE_CHANGED", "Prepare evidence again after changing the planting date.")
            branch_id = uuid4()
            period_start = (
                snapshot.payload.get("c1Input", {})
                .get("simulationPeriod", {})
                .get("startDate")
            )
            self.session.add(
                DecisionBranch(
                    id=branch_id,
                    farm_id=payload.farm_id,
                    plot_id=payload.plot_id,
                    base_snapshot_hash=snapshot.input_hash,
                    effective_date=date.fromisoformat(period_start) if period_start else date.today(),
                    weather_member_id=self._weather_member(snapshot.payload),
                    model_version=capability.engine_version,
                    input_hashes=[snapshot.input_hash],
                    decision_type="baseline",
                    decision_diff={},
                )
            )
            await self.session.flush()
            self.session.add(BranchDecision(id=uuid4(), branch_id=branch_id, decision_type="baseline", payload={}))
            self.session.add(
                TimelineEvent(
                    id=uuid4(),
                    farm_id=payload.farm_id,
                    plot_id=payload.plot_id,
                    branch_id=branch_id,
                    event_type="baseline_created",
                    event_date=date.fromisoformat(period_start) if period_start else date.today(),
                    description="Created baseline branch from the environmental snapshot.",
                    payload={"snapshotId": str(snapshot.id)},
                )
            )
        else:
            branch = await self.session.get(DecisionBranch, branch_id)
            if branch is None or branch.farm_id != payload.farm_id or branch.plot_id != payload.plot_id:
                raise ValueError("INVALID_BRANCH")
            if branch.base_snapshot_hash != snapshot.input_hash:
                raise ValueError("BRANCH_SNAPSHOT_MISMATCH")
            if branch.decision_type == "planting_date":
                planting_date = date.fromisoformat(branch.decision_diff["plantingDate"])
        await self.session.flush()
        if payload.irrigation_mode == "irrigated":
            resource_service = ResourceService(self.session)
            await resource_service.get_resource(payload.farm_id, payload.resource_id)
            await resource_service.get_ledger(payload.farm_id, payload.resource_id, branch_id)
        run = SimulationRun(
            id=uuid4(),
            farm_id=payload.farm_id,
            plot_id=payload.plot_id,
            branch_id=branch_id,
            environmental_snapshot_id=snapshot.id,
            engine_name=capability.selected_engine,
            engine_version=capability.engine_version,
            parameter_version=capability.parameter_versions[0]
            if capability.parameter_versions
            else None,
            status="queued",
            input_hash=snapshot.input_hash,
            requested_at=datetime.now(UTC),
            warnings=[],
            weather_realization_id=self._weather_id(snapshot.payload),
            weather_member_id=self._weather_member(snapshot.payload),
            input_provenance={
                "turmericMapping": payload.turmeric_mapping,
                "plantingDate": planting_date.isoformat() if planting_date else None,
                "fallowKc": payload.fallow_kc,
                "irrigationMode": payload.irrigation_mode,
                "resourceId": str(payload.resource_id) if payload.resource_id else None,
            },
        )
        self.session.add(run)
        await self.session.commit()
        return run

    @staticmethod
    def _weather_id(payload: dict) -> str | None:
        return payload.get("c1Input", payload).get("inputSnapshotId") or _hash(payload)

    @staticmethod
    def _weather_member(payload: dict) -> str | None:
        weather = payload.get("c1Input", payload).get("dailyWeather", [])
        return next(
            (row.get("ensembleMemberId") for row in weather if row.get("ensembleMemberId")), None
        )

    async def execute_background(self, run_id: UUID, session_factory) -> None:
        async with session_factory() as session:
            run = await session.get(SimulationRun, run_id)
            if run is None:
                return
            run.status = "running"
            run.started_at = datetime.now(UTC)
            await session.commit()
            snapshot = await session.get(EnvironmentalSnapshot, run.environmental_snapshot_id)
            plot = await session.get(Plot, run.plot_id)
            try:
                ledger = schedule = None
                if (run.input_provenance or {}).get("irrigationMode") == "irrigated":
                    resource_id = UUID(run.input_provenance["resourceId"])
                    c1_period = snapshot.payload.get("c1Input", snapshot.payload)["simulationPeriod"]
                    ledger, schedule = await ResourceService(session).build_scientific_inputs(
                        run.farm_id,
                        resource_id,
                        run.branch_id,
                        run.plot_id,
                        area_m2=plot.area_m2,
                        start_date=date.fromisoformat(c1_period["startDate"]),
                        end_date=date.fromisoformat(c1_period["endDate"]),
                    )
                    run.input_provenance = {
                        **(run.input_provenance or {}),
                        "c8Ledger": {
                            "ledgerHash": schedule["ledgerHash"],
                            "scheduleHash": _hash(schedule),
                            "resourceId": schedule["resourceId"],
                            "openingVolume": ledger["openingVolume"],
                            "closingVolume": ledger["closingVolume"],
                            "losses": ledger["losses"],
                        },
                    }
                result = await asyncio.to_thread(
                    self._execute_science, run, snapshot, plot, ledger, schedule
                )
                if result.get("status") != "completed":
                    error = result["error"]
                    run.status, run.error_code, run.error_message = (
                        "failed",
                        error["code"],
                        error["message"],
                    )
                    run.warnings = result.get("warnings", [])
                else:
                    for row in result["states"]:
                        session.add(
                            ScientificState(
                                simulation_run_id=run.id,
                                plot_id=run.plot_id,
                                branch_id=run.branch_id,
                                state_date=row["date"],
                                payload=row,
                                availability=row["availability"]["status"],
                            )
                        )
                    run.status = "completed"
                    run.science_envelope = result["scienceEnvelope"]
                    run.engine_version = result["scienceEnvelope"]["modelVersion"]
                    run.parameter_version = result["scienceEnvelope"]["cropBinding"]["parameterVersion"]
                    run.input_provenance = {
                        **(run.input_provenance or {}),
                        **result["inputProvenance"],
                    }
                    run.warnings = result.get("warnings", [])
                run.completed_at = datetime.now(UTC)
                await session.commit()
            except (ArithmeticError, ImportError, KeyError, RuntimeError, TypeError, ValueError) as exc:
                run.status, run.error_code, run.error_message = (
                    "failed",
                    "SCIENCE_EXECUTION_FAILED",
                    str(exc),
                )
                run.completed_at = datetime.now(UTC)
                await session.commit()

    @staticmethod
    def _execute_science(run, snapshot, plot, ledger=None, schedule=None) -> dict:
        if snapshot is None or plot is None:
            return {
                "status": "failed",
                "error": {
                    "code": "SNAPSHOT_NOT_FOUND",
                    "message": "Inputs disappeared",
                    "stage": "input",
                },
            }
        from app.services.crop_lens.registry import get_crop_by_id as lookup
        from app.services.crop_lens.resolver import CropLensResolver
        from terrapulse_science.crop_binding import CropBindingService
        from terrapulse_science.orchestration import ScientificRunService

        c1 = C1EnvironmentalInput.model_validate(snapshot.payload.get("c1Input", snapshot.payload))
        binding = CropBindingService(resolve=CropLensResolver().resolve, get_crop_by_id=lookup)
        service = ScientificRunService(
            crop_binding=binding,
            c1_model=C1EnvironmentalInput,
            c3_model=__import__("app.contracts", fromlist=["C3ScientificState"]).C3ScientificState,
        )
        period = c1.simulation_period
        provenance = run.input_provenance or {}
        planting_date = provenance.get("plantingDate") if "plantingDate" in provenance else plot.planting_date
        weather_kind = (
            "forecast" if any(source.startswith("open-meteo:") for source in c1.data_source_ids)
            else "model-estimate"
        )
        return service.execute(
            snapshot=c1,
            crop_id=plot.crop_id,
            farm_id=run.farm_id,
            plot_id=run.plot_id,
            branch_id=run.branch_id,
            simulation_run_id=run.id,
            turmeric_mapping=(run.input_provenance or {}).get("turmericMapping"),
            area_m2=float(plot.area_m2),
            planting_date=str(planting_date or period.start_date),
            root_depth_m=0.3,
            depletion_fraction=0.5,
            initial_depletion_mm=0.0,
            weather_realization_id=run.weather_realization_id or _hash(c1.model_dump(mode="json")),
            ensemble_member_id=run.weather_member_id,
            weather_kind=weather_kind,
            fallow_kc=(run.input_provenance or {}).get("fallowKc"),
            rainfed=ledger is None,
            ledger=ledger,
            schedule=schedule,
            environmental_warnings=[
                "Fixed 0.30 m root depth, 0.5 depletion fraction and zero initial depletion are model assumptions.",
            ],
        )
