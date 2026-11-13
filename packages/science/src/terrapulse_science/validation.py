"""Developer A output checks; does not change any shared wire contract."""
from .contracts import fail, real, iso_date, nonempty
from .capability import FAO_METRICS, AQUA_METRICS, OUTPUT_VERSION, ADAPTER_VERSION

METRIC_UNITS = {**FAO_METRICS, **AQUA_METRICS, "yieldTonnesPerHa":"tonnes/ha",
                "groundwaterDepthM":"m"}


def validate_metrics(metrics):
    if not isinstance(metrics, dict):
        fail("INVALID_METRICS", "state metrics must be an object")
    for name, metric in metrics.items():
        if not isinstance(metric, dict) or "value" not in metric:
            fail("INVALID_METRIC", f"{name} must be an object with an explicit value")
        if name not in METRIC_UNITS or metric.get("unit") != METRIC_UNITS[name]:
            fail("UNIT_MISMATCH", f"unexpected unit for {name}")
        status = metric.get("status")
        if status not in ("available", "unsupported", "inactive", "unavailable"):
            fail("INVALID_METRIC_STATUS", name)
        if status == "available":
            real(metric.get("value"), name, minimum=0,
                 maximum=1 if metric["unit"] in {"fraction", "m3/m3"} else None)
        elif metric.get("value") is not None:
            fail("UNAVAILABLE_HAS_VALUE", f"{name} must be null when {status}")


def validate_run(run):
    for key in ("runId", "branchId", "plotId", "engine", "modelVersion"):
        nonempty(run.get(key), key)
    if run.get("scientificOutputVersion") != OUTPUT_VERSION or run.get("adapterVersion") != ADAPTER_VERSION:
        fail("OUTPUT_VERSION_MISMATCH", "expected current Developer A scientific envelope")
    states = run.get("states")
    if not isinstance(states, list) or not states:
        fail("MISSING_STATES", "nonempty executed states required")
    seen = set()
    previous = None
    for state in states:
        day = iso_date(state.get("date"))
        if day in seen or (previous is not None and day <= previous):
            fail("DUPLICATE_OR_UNSORTED_DATE", "state dates must be unique and chronological")
        seen.add(day)
        previous = day
        if state.get("status") not in {"active", "inactive"}:
            fail("INVALID_STATE_STATUS", "unexecuted slots must not be published")
        validate_metrics(state.get("metrics", {}))
    return run
