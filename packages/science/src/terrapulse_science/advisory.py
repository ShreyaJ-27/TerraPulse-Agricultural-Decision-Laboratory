"""Decision-support signals derived from completed science envelopes."""

from copy import deepcopy

from .compare import compare_runs
from .contracts import BALANCE_TOL_MM, Soil, fail, iso_date, real
from .validation import validate_run

_VERSION = "1.0"
_METRICS = {
    "rootZoneDepletionMm": "mm",
    "waterStressKs": "fraction",
    "potentialEtMm": "mm/day",
}


def _context(run, simulation_run_id, input_provenance):
    identity = {key: run[key] for key in ("plotId", "branchId", "runId")}
    if simulation_run_id is not None:
        identity["simulationRunId"] = str(simulation_run_id)
    provenance = {key: run[key] for key in (
        "engine", "modelVersion", "scientificOutputVersion", "inputSnapshotId", "inputHash",
        "weatherRealizationId", "weatherMemberId", "weatherHash", "evidenceKind",
        "capability", "crop", "cropBinding", "soil", "irrigationSource",
    ) if key in run}
    if input_provenance is not None:
        provenance["inputs"] = input_provenance
    confidence = {
        "basis": "model-derived",
        "limitations": [
            "Confidence depends on the input data and parameter provenance. No field verification is inferred.",
            *run.get("warnings", []),
        ],
    }
    return deepcopy({"identity": identity, "provenance": provenance, "confidence": confidence})


def _signal(context, date, category, metric, unit, condition, values):
    return {
        **context, "date": date, "decisionCategory": category, "metric": metric,
        "unit": unit, "triggerCondition": condition, "supportingValues": values,
    }


def _raw_mm(run):
    soil = Soil(**run["soil"])
    soil.validate()
    return real(soil.taw_mm * soil.depletion_fraction, "readily available water", minimum=0)


def evaluate_advisory_signals(run, *, date, simulation_run_id=None, input_provenance=None):
    """Evaluate one explicitly requested absolute date from a trusted science envelope."""
    iso_date(date)
    result = {"version": _VERSION, "date": date, "metrics": {}, "signals": []}
    if run is None or run.get("status") not in {"completed", "completed-output-parse"}:
        return {**result, "status": "unavailable", "reason": "completed science run required"}
    fao = (run.get("engine"), run.get("status")) == ("fao56", "completed")
    aqua = (run.get("engine"), run.get("status")) == ("aquacrop", "completed-output-parse")
    if not (fao or aqua):
        return {**result, "status": "unsupported", "reason": "engine has no advisory mapping"}

    validate_run(run)
    context = _context(run, simulation_run_id, input_provenance)
    state = next((state for state in run["states"] if state["date"] == date), None)
    if state is None:
        return {**result, **context, "status": "unavailable", "reason": "date outside executed states"}

    metrics = result["metrics"]
    for name, unit in _METRICS.items():
        if aqua and name != "potentialEtMm":
            metrics[name] = {
                "status": "unsupported", "value": None, "unit": unit,
                "definition": "AquaCrop exports no comparable FAO-56 depletion or Ks",
            }
        else:
            missing = {"status": "unavailable", "value": None, "unit": unit,
                       "definition": "metric absent from the science envelope"}
            if name == "potentialEtMm" and state["status"] == "inactive":
                missing.update(status="inactive", definition="no active crop")
            metrics[name] = deepcopy(state["metrics"].get(name, missing))

    if state["status"] == "inactive":
        return {**result, **context, "status": "inactive"}

    depletion, ks, demand = (metrics[name]["value"] for name in _METRICS)
    signals = result["signals"]
    if demand is not None:
        signals.append(_signal(context, date, "crop-water-demand", "potentialEtMm", "mm/day",
                               "active crop with available modeled potential crop ET",
                               {"potentialCropEtMmPerDay": demand}))
    if fao:
        raw = _raw_mm(run)
        if ks is not None and ks < 1:
            signals.append(_signal(context, date, "irrigation-review", "waterStressKs", "fraction",
                                   "modeled Ks < 1 after same-day wetting and before ET",
                                   {"ks": ks, "stressIndex": 1 - ks, "readilyAvailableWaterMm": raw}))
        if depletion is not None:
            values = {"endOfDayDepletionMm": depletion, "readilyAvailableWaterMm": raw,
                      "headroomMm": raw - depletion}
            if depletion > raw + BALANCE_TOL_MM:
                signals.append(_signal(context, date, "irrigation-review", "rootZoneDepletionMm", "mm",
                                       "end-of-day depletion exceeds modeled readily available water", values))
            elif demand is not None and demand > 0 and raw - depletion <= demand:
                signals.append(_signal(context, date, "monitor-depletion", "rootZoneDepletionMm", "mm",
                                       "end-of-day headroom is within one day at today's potential crop ET",
                                       {**values, "potentialCropEtMmPerDay": demand}))
    statuses = {metric["status"] for metric in metrics.values()}
    if "available" in statuses:
        status = "available"
    elif statuses <= {"unsupported", "inactive"} and "unsupported" in statuses:
        status = "unsupported"
    else:
        status = "unavailable"
    return {**result, **context, "status": status}


def compare_advisory_signals(baseline, alternative, *, date, fork_date,
                             baseline_simulation_run_id=None, alternative_simulation_run_id=None,
                             baseline_input_provenance=None, alternative_input_provenance=None):
    """Surface modeled threshold crossings on a comparable active date."""
    day = iso_date(date)
    fork = iso_date(fork_date, "fork_date")
    result = {"version": _VERSION, "date": date, "signals": []}
    if day < fork:
        return {**result, "status": "unavailable", "reason": "date precedes management fork"}
    if any(run is None or run.get("status") not in {"completed", "completed-output-parse"}
           for run in (baseline, alternative)):
        return {**result, "status": "unavailable", "reason": "two completed science runs required"}
    if any(run.get("engine") != "fao56" for run in (baseline, alternative)):
        return {**result, "status": "unsupported", "reason": "threshold comparison requires FAO-56"}

    comparison = compare_runs(baseline, alternative, fork_date=fork_date)
    if comparison["status"] != "comparable":
        return {**result, "status": comparison["status"], "reasons": comparison["reasons"]}
    matched = next((row for row in comparison["daily"] if row["date"] == date), None)
    if matched is None:
        states = [state for run in (baseline, alternative) for state in run["states"]
                  if state["date"] == date]
        status = "inactive" if any(state["status"] == "inactive" for state in states) else "unavailable"
        return {**result, "status": status, "reason": "no paired active crop metrics on date"}

    thresholds = {"rootZoneDepletionMm": (_raw_mm(baseline), "above"),
                  "waterStressKs": (1.0, "below")}
    context = _context(alternative, alternative_simulation_run_id, alternative_input_provenance)
    context["baseline"] = _context(baseline, baseline_simulation_run_id, baseline_input_provenance)
    available = False
    for metric in matched["metrics"]:
        name = metric["name"]
        if name not in thresholds:
            continue
        available = True
        threshold, direction = thresholds[name]
        a, b = metric["branchA"], metric["branchB"]
        if direction == "above":
            crosses = (a > threshold + BALANCE_TOL_MM) != (b > threshold + BALANCE_TOL_MM)
        else:
            crosses = (a < threshold) != (b < threshold)
        if crosses:
            result["signals"].append(_signal(
                context, date, "compare-management", name, metric["unit"],
                f"one branch is {direction} the modeled threshold",
                {"baseline": a, "alternative": b, "differenceAlternativeMinusBaseline": b - a,
                 "threshold": threshold},
            ))
    return {**result, "status": "available" if available else "unavailable"}
