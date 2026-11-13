"""C5 Future Fold comparisons: independent runs and matched baseline identity."""
from __future__ import annotations
import math
from .contracts import fail, iso_date, real
from .capability import WEATHER_SHA256
from .validation import validate_run

SUPPORTED_DAILY={
    "actualEtMm": "mm/day",
    "potentialEtMm": "mm/day",
    "rootZoneDepletionMm": "mm",
    "waterStressKs": "fraction",
}

def compare_runs(a:dict,b:dict,*,fork_date:str|None=None) -> dict:
    if a.get("runId")==b.get("runId") or a.get("branchId")==b.get("branchId"):
        fail("NOT_INDEPENDENT", "comparison requires two separately executed branch runs")
    if a.get("status")!="completed" or b.get("status")!="completed":
        fail("RUN_INCOMPLETE", "both independent runs must have completed")
    validate_run(a)
    validate_run(b)
    reasons=[]
    if a.get("engine") != "fao56" or b.get("engine") != "fao56":
        reasons.append("FAO-56 comparisons require two FAO-56 runs")
    if any(not isinstance(r.get("weatherHash"),str) or len(r["weatherHash"]) != 64 for r in (a,b)):
        reasons.append("weather content identity missing")
    fork = iso_date(fork_date,"fork_date") if fork_date is not None else None
    if a.get("plantingDate") != b.get("plantingDate"):
        if fork_date is None:
            fail("FORK_DATE_REQUIRED", "planting-date comparisons require Developer D fork date before earliest sowing")
        first=min(iso_date(a["plantingDate"]),iso_date(b["plantingDate"]))
        if fork >= first:
            reasons.append("forkDate must precede earliest planting decision")
    for key in ("engine","modelVersion","plotId","areaM2","startDate","endDate",
                "weatherRealizationId","weatherMemberId","weatherHash","soil","initialDepletionMm",
                "inputSnapshotId","fallowKc"):
        if a.get(key)!=b.get(key):
            reasons.append(f"{key} differs")
    ca,cb=a.get("crop",{}),b.get("crop",{})
    for k in ("scientific_name","parameter_version","parameter_source","kc_initial","kc_mid","kc_end","stage_lengths_days","mapping_status"):
        if ca.get(k)!=cb.get(k):reasons.append(f"crop.{k} differs")
    if a.get("capability") != b.get("capability"):
        reasons.append("capability provenance differs")
    if a.get("irrigationSource") != b.get("irrigationSource"):
        reasons.append("irrigationSource differs")
    if fork is not None:
        def prior_irrigation(run):
            return {s["date"]:s["v01C3"]["effectiveIrrigationMm"] for s in run["states"] if s["date"] < fork_date}
        if prior_irrigation(a) != prior_irrigation(b):
            reasons.append("effective irrigation differs before forkDate")
    if reasons:
        return {"status":"not-comparable","reasons":reasons,"branchAId":a.get("branchId"),
                "branchBId":b.get("branchId"),"metrics":[],"matchedWeatherRealization":
                    not any(reason.startswith("weather") for reason in reasons)}
    ia={x["date"]:x for x in a.get("states",[])}
    ib={x["date"]:x for x in b.get("states",[])}
    if set(ia)!=set(ib):
        fail("DATE_ALIGNMENT", "branches lack matched absolute-date states")
    comparisons=[]
    skipped=[]
    for day in sorted(ia):
        x,y=ia[day],ib[day]
        metrics=[]
        # Distinct crop-active periods are not paired as crop outcomes.
        # The individual source runs retain dated fallow-soil water accounting.
        if not x.get("cropActive") or not y.get("cropActive"):
            skipped.append({"date":day,"reason":"crop inactive in one or both branches"})
            continue
        for metric,unit in SUPPORTED_DAILY.items():
            mx,my=x["metrics"].get(metric),y["metrics"].get(metric)
            if not mx or not my or mx.get("status")!="available" or my.get("status")!="available":
                continue
            vx,vy=mx["value"],my["value"]
            if vx is None or vy is None:continue
            metrics.append({"name":metric,"unit":unit,"branchA":vx,"branchB":vy,
                            "differenceBMinusA":vy-vx})
        if metrics:
            comparisons.append({"date":day,"metrics":metrics})
        else:
            skipped.append({"date":day,"reason":"no mutually available crop metrics"})
    # Seasonal ET can be compared across DIFFERENT growing calendars as long
    # as BOTH complete seasons were covered by the shared input horizon.
    seasonal=[]
    if a.get("summary",{}).get("cropSeasonComplete") and b.get("summary",{}).get("cropSeasonComplete"):
        va,vb=(real(r["summary"]["activeActualEtMm"],"seasonal ET",minimum=0) for r in (a,b))
        seasonal.append({"name":"seasonalActualEtMm","unit":"mm","branchA":va,"branchB":vb,
                         "differenceBMinusA":vb-va,
                         "explanation":"complete model seasons; planting calendar differs; not yield or irrigation requirement"})
    return {"status":"comparable","branchAId":a["branchId"],"branchBId":b["branchId"],
            "runAId":a["runId"],"runBId":b["runId"],"matchedWeatherRealization":True,
            "metrics":seasonal,"daily":comparisons,"skippedDates":skipped,
            "warnings":["management scenarios are comparisons under declared model assumptions, not farm forecasts",
                        "non-overlap or inactive crop days are not compared as zero"]}


def compare_aquacrop_runs(a:dict,b:dict,*,fork_date:str) -> dict:
    """Compare the two published Tunis wheat example branches by absolute date.

    Historical seasonal yields are paired by season index; unsupported or
    post-harvest daily slots are excluded, never zero-filled. This is NOT a
    generalized AquaCrop crop/model comparison contract.
    """
    if a.get("runId")==b.get("runId") or a.get("branchId")==b.get("branchId"):
        fail("NOT_INDEPENDENT", "independent AquaCrop branch runs required")
    if a.get("status")!="completed-output-parse" or b.get("status")!="completed-output-parse":
        fail("RUN_INCOMPLETE", "both AquaCrop outputs must be parsed and complete")
    validate_run(a)
    validate_run(b)
    reasons=[]
    for key in ("engine","modelVersion","plotId","inputSnapshotId",
                "weatherRealizationId","weatherHash","parameterVersion","startDate","endDate",
                "soilType","cropName","capability","evidenceKind"):
        if a.get(key)!=b.get(key):reasons.append(f"{key} differs")
    if a.get("engine")!="aquacrop" or a.get("modelVersion")!="aquacrop-ospy-3.1.0":
        reasons.append("unverified AquaCrop engine version")
    if any(r.get("weatherHash") != WEATHER_SHA256 or r.get("evidenceKind") not in {
        "historical-fixture","executed-aquacrop"} for r in (a,b)):
        reasons.append("verified AquaCrop weather and provenance required")
    fork=iso_date(fork_date,"fork_date")
    first_dates=[iso_date(d["firstPlantingDate"]) for d in (a,b) if d.get("firstPlantingDate")]
    if len(first_dates)<2 or fork>=min(first_dates):
        reasons.append("forkDate must precede earliest planting")
    if reasons:
        return {"status":"not-comparable","reasons":reasons,"metrics":[],
          "branchAId":a.get("branchId"),"branchBId":b.get("branchId")}
    x={r["date"]:r for r in a["states"]}
    y={r["date"]:r for r in b["states"]}
    daily=[]
    skipped=[]
    for day in sorted(set(x)|set(y)):
        ra,rb=x.get(day),y.get(day)
        if not ra or not rb or ra["status"]!="active" or rb["status"]!="active":
            skipped.append(day)
            continue
        common=[]
        for metric in ("actualEtMm","potentialEtMm","rootWaterStorageMm",
                       "rootDepthM","canopyCoverFraction","biomassTonnesPerHa"):
            ma,mb=ra["metrics"].get(metric),rb["metrics"].get(metric)
            if not ma or not mb or ma["status"]!="available" or mb["status"]!="available":
                continue
            va,vb=ma["value"],mb["value"]
            common.append({"name":metric,"unit":ma["unit"],"branchA":va,"branchB":vb,
                           "differenceBMinusA":vb-va})
        if common:daily.append({"date":day,"metrics":common})
        else:skipped.append(day)
    ha={v["season"]:v for v in a["harvests"]}
    hb={v["season"]:v for v in b["harvests"]}
    if set(ha)!=set(hb) or len(ha)!=6 or len(a["harvests"])!=6 or len(b["harvests"])!=6:
        fail("UNMATCHED_SEASONS", "six unique paired harvest seasons are required")
    harvests=[]
    for season in sorted(ha):
        va=real(ha[season]["dryYieldTonnesPerHa"],"dry yield A",minimum=0)
        vb=real(hb[season]["dryYieldTonnesPerHa"],"dry yield B",minimum=0)
        harvests.append({"season":season,"unit":"tonnes/ha", "dateA":ha[season]["harvestDate"],
                         "dateB":hb[season]["harvestDate"], "dryYieldA":va,"dryYieldB":vb,
                         "differenceBMinusA":vb-va})
    return {"status":"comparable","branchAId":a["branchId"],"branchBId":b["branchId"],
       "matchedWeatherRealization":True,"daily":daily,"skippedDates":skipped,
       "seasonalDryYield":harvests,
       "meanDryYieldA":math.fsum(v["dryYieldA"] for v in harvests)/len(harvests),
       "meanDryYieldB":math.fsum(v["dryYieldB"] for v in harvests)/len(harvests),
       "warnings":["Only published Tunis/Wheat/SandyLoam 3.1.0 example is supported.",
                   "Season index links historical years; dates vary by planting choice.",
                   "Unexecuted and inactive daily slots excluded; no zero-filled outputs or invented local predictions."]}
