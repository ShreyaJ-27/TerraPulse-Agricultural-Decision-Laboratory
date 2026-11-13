"""Developer A boundary for the repository's C1/C3/C8 version 1.0 JSON."""
from dataclasses import dataclass
from datetime import datetime
import math
from uuid import UUID

from .c1_c8 import LEDGER_TOL_L
from .contracts import CropKc, FaoRequest, Soil, WeatherDay, fail, iso_date, nonempty, real, stable_hash
from .validation import validate_run


def _object(value, field):
    if not isinstance(value, dict):
        fail("INVALID_CONTRACT_OBJECT", f"{field} must be an object")
    return value


def _array(value, field):
    if not isinstance(value, list):
        fail("INVALID_CONTRACT_ARRAY", f"{field} must be an array")
    return value


def _contract(payload, name):
    payload = _object(payload, name)
    if payload.get("contractVersion") != "1.0":
        fail("CONTRACT_VERSION_MISMATCH", f"expected {name} 1.0")
    return payload


def _uuid(value, field):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        fail("INVALID_CONTRACT_ID", f"{field} must be a UUID string")


def _measurement(value, unit, field, *, minimum=0):
    value = _object(value, field)
    if value.get("unit") != unit:
        fail("UNIT_MISMATCH", f"{field} requires {unit}")
    if _object(value.get("availability"), field + ".availability").get("status") != "available":
        fail("MEASUREMENT_UNAVAILABLE", f"{field} must be available")
    return real(value.get("value"), field, minimum=minimum)


def _timestamp(value, field):
    value = nonempty(value, field)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        fail("INVALID_PROVENANCE", f"{field} must be an ISO timestamp")
    if parsed.utcoffset() is None:
        fail("INVALID_PROVENANCE", f"{field} requires a timezone")
    return value


def _provenance(value):
    items = _array(value, "provenance")
    if not items:
        fail("MISSING_PROVENANCE", "at least one source record is required")
    records = []
    for entry in items:
        entry = _object(entry, "provenance record")
        record = {
            "sourceId": nonempty(entry.get("sourceId"), "provenance.sourceId"),
            "retrievedAt": _timestamp(entry.get("retrievedAt"), "provenance.retrievedAt"),
        }
        for key in ("sourceVersion", "reference"):
            if entry.get(key) is not None:
                record[key] = nonempty(entry[key], "provenance." + key)
        records.append(record)
    return records


def irrigation_from_c8_v1(ledger, *, farm_id, branch_id, plot_id, area_m2,
                         start_date, end_date, schedule):
    """Validate the branch aggregate and reconcile Developer D's dated litres."""
    ledger = _contract(ledger, "C8")
    if (_uuid(ledger.get("farmId"), "C8.farmId") != _uuid(farm_id, "farmId")
        or _uuid(ledger.get("branchId"), "C8.branchId") != _uuid(branch_id, "branchId")):
        fail("LEDGER_IDENTITY_MISMATCH", "C8 farm and branch must match the run")
    plot_id = _uuid(plot_id, "plotId")
    resource = _uuid(ledger.get("resourceId"), "C8.resourceId")
    if ledger.get("unit") != "litre":
        fail("UNIT_MISMATCH", "C8 requires litre")
    check = _object(ledger.get("accountingValidation"), "C8.accountingValidation")
    if check.get("isValid") is not True or _array(ledger.get("errors"), "C8.errors"):
        fail("INVALID_LEDGER", "C8 reports accounting errors")
    difference = _measurement(check.get("difference"), "litre", "C8.difference", minimum=None)
    opening, losses, closing = (
        _measurement(ledger.get(key), "litre", f"C8.{key}")
        for key in ("openingVolume", "losses", "closingVolume")
    )
    allocations = {}
    withdrawals = []
    allocation_losses = []
    for row in _array(ledger.get("plotAllocations"), "C8.plotAllocations"):
        row = _object(row, "C8 plot allocation")
        allocated_plot = _uuid(row.get("plotId"), "C8 allocation.plotId")
        if allocated_plot in allocations:
            fail("DUPLICATE_ALLOCATION", "C8 requires one aggregate per plot")
        requested, withdrawn, effective = (
            _measurement(row.get(key), "litre", f"C8.{key}")
            for key in ("requestedAmount", "withdrawnAmount", "effectiveAmount")
        )
        if effective > withdrawn + LEDGER_TOL_L or withdrawn > requested + LEDGER_TOL_L:
            fail("LEDGER_CONSERVATION", "require effective <= withdrawn <= requested")
        allocations[allocated_plot] = effective
        withdrawals.append(withdrawn)
        allocation_losses.append(withdrawn - effective)
    if any(abs(residual) > LEDGER_TOL_L for residual in (
        difference, opening - closing - math.fsum(withdrawals),
        losses - math.fsum(allocation_losses),
    )):
        fail("LEDGER_CONSERVATION", "C8 balances or aggregate losses do not reconcile")
    area = real(area_m2, "areaM2", minimum=0)
    if area == 0:
        fail("INVALID_AREA", "plot area must be positive")
    if schedule is None:
        fail("IRRIGATION_SCHEDULE_REQUIRED", "C8 aggregates contain no dates; provide the explicit schedule")
    schedule = _object(schedule, "dated irrigation schedule")
    if (schedule.get("ledgerHash") != stable_hash(ledger)
        or _uuid(schedule.get("resourceId"), "schedule.resourceId") != resource
        or _uuid(schedule.get("plotId"), "schedule.plotId") != plot_id):
        fail("LEDGER_IDENTITY_MISMATCH", "schedule must identify the exact C8 ledger, resource and plot")
    start, end = iso_date(start_date), iso_date(end_date)
    if end < start:
        fail("INVALID_WINDOW", "simulation end precedes start")
    daily = {}
    for row in _array(schedule.get("days"), "schedule.days"):
        row = _object(row, "scheduled day")
        day = iso_date(row.get("date"))
        if day in daily:
            fail("DUPLICATE_ALLOCATION", "schedule requires at most one entry per day")
        if not start <= day <= end:
            fail("LEDGER_WINDOW", "scheduled irrigation lies outside the run")
        daily[day] = real(row.get("effectiveLitres"), "effectiveLitres", minimum=0)
    if abs(math.fsum(daily.values()) - allocations.get(plot_id, 0)) > LEDGER_TOL_L:
        fail("LEDGER_SCHEDULE_MISMATCH", "dated effective litres do not reconcile to the C8 plot total")
    return {day.isoformat(): litres / area for day, litres in sorted(daily.items())}


@dataclass(frozen=True)
class RepositoryFaoInput:
    request: FaoRequest
    farm_id: str
    provenance: list[dict]


def fao_input_from_c1_v1(c1, *, plot_id, branch_id, area_m2, planting_date,
                         crop: CropKc, root_depth_m, depletion_fraction,
                         initial_depletion_mm, weather_realization_id,
                         ensemble_member_id, weather_kind, fallow_kc=None,
                         ledger=None, schedule=None, rainfed=False):
    """Consume C1 JSON (e.g. model_dump(mode='json', by_alias=True))."""
    c1 = _contract(c1, "C1")
    if _object(c1.get("availability"), "C1.availability").get("status") != "available":
        fail("MEASUREMENT_UNAVAILABLE", "C1 snapshot must be available")
    farm_id = _uuid(c1.get("farmId"), "farmId")
    plot_id, branch_id = _uuid(plot_id, "plotId"), _uuid(branch_id, "branchId")
    sources = _provenance(c1.get("provenance"))
    source_ids = _array(c1.get("dataSourceIds"), "C1.dataSourceIds")
    if not source_ids:
        fail("MISSING_PROVENANCE", "C1 requires source IDs")
    for source in source_ids:
        nonempty(source, "C1.dataSourceIds entry")
    acquired = _timestamp(c1.get("retrievedAt"), "C1.retrievedAt")
    if weather_kind not in ("observation", "model-estimate", "forecast", "assumption"):
        fail("INVALID_PROVENANCE", "declare the weather source kind explicitly")
    period = _object(c1.get("simulationPeriod"), "C1.simulationPeriod")
    start, end = iso_date(period.get("startDate")).isoformat(), iso_date(period.get("endDate")).isoformat()
    raw_soil = _object(c1.get("soil"), "C1.soil")
    depth_cm = _measurement(raw_soil.get("depthCm"), "cm", "soil.depthCm")
    root_depth_m = real(root_depth_m, "root_depth_m", minimum=0)
    if root_depth_m * 100 > depth_cm + 1e-8:
        fail("SOIL_DEPTH_COVERAGE", "C1 soil depth does not cover the fixed root zone")
    soil = Soil(root_depth_m,
        _measurement(raw_soil.get("fieldCapacity"), "m3/m3", "soil.fieldCapacity"),
        _measurement(raw_soil.get("wiltingPoint"), "m3/m3", "soil.wiltingPoint"),
        depletion_fraction, "C1 snapshot sources: " + ", ".join(source_ids), stable_hash(sources))
    snapshot = stable_hash(c1)
    provenance = {"provider": ", ".join(source_ids), "kind": weather_kind,
                  "reference": "C1 SHA-256 " + snapshot, "acquiredAt": acquired, "sources": sources}
    weather = []
    for item in _array(c1.get("dailyWeather"), "C1.dailyWeather"):
        item = _object(item, "daily weather")
        if item.get("ensembleMemberId") != ensemble_member_id:
            continue
        et0 = item.get("referenceEvapotranspirationMm")
        if et0 is None:
            fail("MEASUREMENT_UNAVAILABLE", f"referenceEvapotranspirationMm is required on {item.get('date')}")
        weather.append(WeatherDay(
            date=iso_date(item.get("date")).isoformat(),
            rainfall_mm=_measurement(item.get("rainfallMm"), "mm", "rainfallMm"),
            reference_et_mm=_measurement(et0, "mm", "referenceEvapotranspirationMm"),
            min_temp_c=_measurement(item.get("temperatureMinC"), "degC", "temperatureMinC", minimum=None),
            max_temp_c=_measurement(item.get("temperatureMaxC"), "degC", "temperatureMaxC", minimum=None),
            member_id=ensemble_member_id, provenance=provenance,
        ))
    if rainfed is True and ledger is None and schedule is None:
        irrigation, irrigation_source = {}, "explicit-fixture"
    elif rainfed is False and ledger is not None:
        irrigation = irrigation_from_c8_v1(ledger, farm_id=farm_id, branch_id=branch_id,
            plot_id=plot_id, area_m2=area_m2, start_date=start, end_date=end, schedule=schedule)
        irrigation_source = "c8-ledger"
    else:
        fail("IRRIGATION_SOURCE_REQUIRED", "declare rainfed operation or supply a C8 ledger and dated schedule")
    request = FaoRequest(plot_id=plot_id, branch_id=branch_id, area_m2=area_m2,
        planting_date=planting_date, start_date=start, end_date=end,
        weather_realization_id=weather_realization_id, input_snapshot_id=snapshot,
        initial_depletion_mm=initial_depletion_mm, soil=soil, crop=crop,
        weather=tuple(sorted(weather, key=lambda day: day.date)), irrigation_mm_by_date=irrigation,
        irrigation_source=irrigation_source, fallow_kc=fallow_kc)
    request.validate()
    return RepositoryFaoInput(request, farm_id, sources)


def c3_states_from_run(run, *, farm_id, simulation_run_id, provenance):
    """Project executed scientific states into repository C3 JSON.

    The caller supplies the persisted run UUID and source records. The full
    science envelope retains model-specific metrics, input hashes and versions.
    """
    validate_run(run)
    farm_id = _uuid(farm_id, "farmId")
    run_uuid = _uuid(simulation_run_id, "simulationRunId")
    plot_id = _uuid(run["plotId"], "plotId")
    branch_id = _uuid(run["branchId"], "branchId")
    sources = _provenance(provenance)
    is_fao = run["engine"] == "fao56" and run.get("status") == "completed"
    is_aqua = run["engine"] == "aquacrop" and run.get("status") == "completed-output-parse"
    if not (is_fao or is_aqua):
        fail("UNSUPPORTED_ENGINE", "C3 projection requires a completed supported science run")

    def measurement(unit, value=None, *, status="missing", reason="not exported by this run"):
        if value is not None:
            return {"unit":unit, "value":real(value, "C3 measurement", minimum=0),
                    "availability":{"status":"available"}}
        return {"unit":unit, "availability":{"status":status, "reason":reason}}

    def metric(state, key, unit, transform=lambda value: value):
        item = state["metrics"].get(key)
        if item is None:
            return measurement(unit)
        if item["status"] == "available":
            return measurement(unit, transform(item["value"]))
        status = "unsupported" if item["status"] == "unsupported" else "missing"
        return measurement(unit, status=status, reason=item["definition"])

    rows = []
    for state in run["states"]:
        legacy = state.get("v01C3") or {}
        if is_fao:
            depth_mm = 1000 * real(run["soil"]["root_depth_m"], "FAO root depth", minimum=0)
            storage = metric(state, "soilThetaM3M3", "mm", lambda theta: theta * depth_mm)
            stress = metric(state, "waterStressKs", "ratio", lambda ks: 1 - ks)
        else:
            storage = metric(state, "rootWaterStorageMm", "mm")
            stress = measurement("ratio", status="unsupported", reason="no comparable Ks exported")
        rows.append({
            "contractVersion":"1.0", "farmId":farm_id, "plotId":plot_id, "branchId":branch_id,
            "simulationRunId":run_uuid, "date":state["date"],
            "engine":{"name":"FAO-56" if is_fao else "AquaCrop", "version":run["modelVersion"]},
            "soilWater":storage,
            "rootZone":measurement("mm", status="unsupported",
                reason="root-zone semantics require a shared mapping; see the science envelope"),
            "cropWaterDemand":metric(state, "potentialEtMm", "mm"),
            "actualEvapotranspiration":metric(state, "actualEtMm", "mm"),
            "waterStress":stress,
            "irrigation":measurement("mm", legacy.get("effectiveIrrigationMm")),
            "rainfall":measurement("mm", legacy.get("rainfallMm")),
            "drainage":metric(state, "drainageMm", "mm"),
            "runoff":measurement("mm", reason="daily runoff is not exported by the science envelope"),
            "yield":measurement("kg", status="unsupported",
                reason="daily yield is unsupported; see completed seasonal results when available"),
            "availability":{"status":"available"}, "provenance":sources,
        })
    return rows
