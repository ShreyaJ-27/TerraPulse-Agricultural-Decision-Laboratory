"""Synchronous science execution with the repository's injected C1/C3 models."""
from uuid import UUID

from .contracts import ScienceError, fail, stable_hash
from .crop_binding import CropBindingService, _run_bound_fao
from .repository_contracts import c3_states_from_run, fao_input_from_c1_v1


class ScientificRunService:
    """Configure once with the authoritative Pydantic models and crop binding.

    The application owns authorization, canonical crop confirmation, snapshot
    retrieval, and issuance of the persistent run UUID. Only trusted server
    values cross this boundary. One invocation executes at most one engine.
    """

    def __init__(self, *, crop_binding: CropBindingService, c1_model: type, c3_model: type):
        self._crop_binding = crop_binding
        self._c1_model = c1_model
        self._c3_model = c3_model

    def execute(self, *, snapshot, crop_id: UUID, farm_id: UUID, plot_id: UUID,
                branch_id: UUID, simulation_run_id: UUID, turmeric_mapping: str | None,
                area_m2: float, planting_date: str, root_depth_m: float,
                depletion_fraction: float, initial_depletion_mm: float,
                weather_realization_id: str, ensemble_member_id: str | None,
                weather_kind: str, fallow_kc: float | None = None,
                rainfed: bool = False, ledger: dict | None = None,
                schedule: dict | None = None, requested_outputs=(),
                environmental_warnings=()) -> dict:
        """Return completed C3 rows plus the full envelope, or a typed failure."""
        stage = "input"
        try:
            if not isinstance(snapshot, self._c1_model):
                fail("INVALID_C1_SNAPSHOT", "expected an authoritative C1 model from the server")
            identities = (farm_id, plot_id, branch_id, simulation_run_id)
            if not all(isinstance(value, UUID) for value in identities):
                fail("INVALID_CONTRACT_ID", "farm, plot, branch and simulation run must be server UUIDs")
            if snapshot.farm_id != farm_id:
                fail("SNAPSHOT_FARM_MISMATCH", "environmental snapshot belongs to another farm")
            if not isinstance(environmental_warnings, (list, tuple)) or not all(
                isinstance(warning, str) for warning in environmental_warnings
            ):
                fail("INVALID_ENVIRONMENTAL_WARNINGS", "expected server-supplied warning strings")
            binding = self._crop_binding.bind_canonical_fao(crop_id, turmeric_mapping=turmeric_mapping)
            try:
                c1 = snapshot.model_dump(mode="json", by_alias=True)
                self._c1_model.model_validate(c1)
            except (ValueError, TypeError) as exc:
                raise ScienceError("C1_VALIDATION_FAILED", "snapshot failed authoritative C1 validation") from exc
            try:
                inputs = fao_input_from_c1_v1(
                    c1, crop=binding.profile, plot_id=str(plot_id), branch_id=str(branch_id),
                    area_m2=area_m2, planting_date=planting_date, root_depth_m=root_depth_m,
                    depletion_fraction=depletion_fraction, initial_depletion_mm=initial_depletion_mm,
                    weather_realization_id=weather_realization_id, ensemble_member_id=ensemble_member_id,
                    weather_kind=weather_kind, fallow_kc=fallow_kc, rainfed=rainfed,
                    ledger=ledger, schedule=schedule,
                )
            except ScienceError:
                raise
            except (ValueError, TypeError) as exc:
                raise ScienceError("INVALID_SCIENCE_INPUT", "expected finite, JSON-compatible run inputs") from exc
            irrigation = {"mode":"rainfed"}
            if not rainfed:
                try:
                    schedule_hash = stable_hash(schedule)
                except (ValueError, TypeError) as exc:
                    raise ScienceError("INVALID_IRRIGATION_SCHEDULE", "schedule must be finite JSON") from exc
                irrigation = {"mode":"c8", "ledgerHash":schedule["ledgerHash"],
                              "scheduleHash":schedule_hash, "resourceId":schedule["resourceId"]}
            stage = "engine"
            envelope = _run_bound_fao(binding, inputs, requested_outputs=requested_outputs)
            stage = "output"
            rows = c3_states_from_run(envelope, farm_id=inputs.farm_id,
                simulation_run_id=str(simulation_run_id), provenance=inputs.provenance)
            try:
                for row in rows:
                    self._c3_model.model_validate(row)
            except ValueError as exc:
                raise ScienceError("C3_VALIDATION_FAILED", "scientific states failed authoritative C3 validation") from exc
        except ScienceError as error:
            return {"status":"failed", "error":{"code":error.code, "message":error.message, "stage":stage}}
        except ArithmeticError:
            return {"status":"failed", "error":{"code":"NUMERIC_FAILURE",
                "message":"scientific input or calculation exceeded numeric bounds", "stage":stage}}

        return {
            "status":"completed", "simulationRunId":str(simulation_run_id), "farmId":inputs.farm_id,
            "plotId":str(plot_id), "branchId":str(branch_id), "states":rows, "scienceEnvelope":envelope,
            "inputProvenance": {
                "environmentalSnapshotHash":inputs.request.input_snapshot_id,
                "sources":inputs.provenance, "weatherKind":weather_kind,
                "irrigation":irrigation,
            },
            "warnings":[*environmental_warnings, *envelope["warnings"]],
        }
