"""FAO-56 single-Kc root-zone daily accounting.

Reimplemented from the independently recovered 2026-11-03 validate.py, whose
original 17 acceptance tests and source report accompany this distribution.
Fixed root zone, early water input, stress after wetting, ET then drainage.
This does NOT simulate biomass, yield, detailed soil layers, or root growth.
"""
from __future__ import annotations
from datetime import timedelta
from dataclasses import asdict
import math
from .capability import CapabilityRegistry, OUTPUT_VERSION, ADAPTER_VERSION, REGISTRY_VERSION
from .validation import validate_run
from .contracts import (
    BALANCE_TOL_MM, FAO_ENGINE_VERSION, CONTRACT_VERSION,
    FaoRequest, Soil, WeatherDay, fail, real, stable_hash,
)

def kc_at_day(elapsed_day: int, lengths: tuple[int,int,int,int], coeff: tuple[float,float,float]) -> tuple[float,str]:
    if not isinstance(lengths, (list, tuple)) or len(lengths) != 4 or any(type(v) is not int or v <= 0 for v in lengths):
        fail("INVALID_STAGE_LENGTHS", "four positive integer stage lengths required")
    if not isinstance(coeff, (list, tuple)) or len(coeff) != 3:
        fail("MISSING_PARAMETERS", "three Kc coefficients required")
    for value in coeff:
        real(value, "Kc coefficient", minimum=0)
    if type(elapsed_day) is not int or not 1 <= elapsed_day <= sum(lengths):
        fail("INVALID_KC_DAY", "elapsed day outside declared season")
    a,b,c,d = lengths
    ki,km,ke = coeff
    if elapsed_day <= a:
        return ki, "initial"
    if elapsed_day <= a+b:
        return ki+(elapsed_day-a)/b*(km-ki), "development"
    if elapsed_day <= a+b+c:
        return km, "mid"
    return km+(elapsed_day-a-b-c)/d*(ke-km), "late"

def fao_day(soil: Soil, dr: float, *, et0: float, kc: float, rain: float = 0,
            irrigation: float = 0, runoff: float = 0, capillary: float = 0) -> dict:
    soil.validate()
    for key,value in {"dr":dr,"et0":et0,"kc":kc,"rain":rain,"irrigation":irrigation,
                      "runoff":runoff,"capillary":capillary}.items():
        real(value, key)
    if not 0 <= dr <= soil.taw_mm + BALANCE_TOL_MM:
        fail("INVALID_DEPLETION", "root zone depletion outside [0, TAW]")
    if min(et0,kc,rain,irrigation,runoff,capillary) < 0 or runoff > rain:
        fail("INVALID_FLUX", "negative flux or runoff > rainfall")
    taw=real(soil.taw_mm,"root-zone available storage",minimum=0)
    if taw == 0:
        fail("INVALID_SOIL", "root-zone available storage must be representable and positive")
    raw=soil.depletion_fraction*taw
    inflow=real(rain-runoff+irrigation+capillary,"net inflow")
    dr_wet=dr-inflow
    dr_stress=max(0,dr_wet)
    ks=1.0 if dr_stress<=raw else max(0.0,(taw-dr_stress)/(taw-raw))
    potential=real(kc*et0,"potential ET")
    actual=min(ks*potential,max(0.0,taw-dr+inflow))
    drainage=max(0.0,inflow-dr-actual)
    end=dr-inflow+actual+drainage
    if not (-BALANCE_TOL_MM <= end <= taw+BALANCE_TOL_MM):
        fail("MODEL_BOUNDS", "computed root depletion outside physical bounds")
    end=min(taw,max(0.0,end))
    theta_start=soil.field_capacity-dr/(1000*soil.root_depth_m)
    theta_end=soil.field_capacity-end/(1000*soil.root_depth_m)
    s0=1000*soil.root_depth_m*theta_start
    s1=1000*soil.root_depth_m*theta_end
    residual=s0+rain+irrigation+capillary-runoff-actual-drainage-s1
    depletion_residual=end-(dr-rain+runoff-irrigation-capillary+actual+drainage)
    if (not math.isfinite(residual) or not math.isfinite(depletion_residual)
        or abs(residual)>BALANCE_TOL_MM or abs(depletion_residual)>BALANCE_TOL_MM):
        fail("CONSERVATION_FAILURE", "daily water mass conservation failed")
    return {"depletionStartMm":dr,"depletionEndMm":end,"tawMm":taw,"rawMm":raw,
            "rainfallMm":rain,"runoffMm":runoff,"irrigationMm":irrigation,
            "capillaryRiseMm":capillary,"referenceEtMm":et0,"kc":kc,"ks":ks,
            "potentialEtMm":potential,"actualEtMm":actual,"drainageMm":drainage,
            "soilThetaEndM3M3":theta_end,"storageStartMm":s0,"storageEndMm":s1,
            "conservationResidualMm":residual,"depletionResidualMm":depletion_residual}

def run_fao(request: FaoRequest, *, capabilities: CapabilityRegistry | None = None,
            requested_outputs=()) -> dict:
    if not isinstance(request,FaoRequest):
        fail("INVALID_REQUEST", "expected a FaoRequest")
    if not isinstance(request.soil,Soil):
        fail("MISSING_PARAMETERS", "complete sourced soil parameters are required")
    if not isinstance(request.weather,(tuple,list)) or any(not isinstance(day,WeatherDay) for day in request.weather):
        fail("INVALID_WEATHER", "weather must contain dated WeatherDay records")
    if not isinstance(request.irrigation_mm_by_date,dict):
        fail("INVALID_IRRIGATION", "effective irrigation must be a date-to-mm mapping")
    registration = (capabilities or CapabilityRegistry()).require_fao(request.crop, requested_outputs=requested_outputs)
    request.validate()
    from datetime import date
    planting=date.fromisoformat(request.planting_date)
    input_hash=request.input_hash()
    run_id=stable_hash({"contractVersion":CONTRACT_VERSION,"engineVersion":FAO_ENGINE_VERSION,
                        "inputHash":input_hash,"adapterVersion":ADAPTER_VERSION,
                        "capability":registration})
    dr=request.initial_depletion_mm
    states=[]
    raw_rows=[]
    season_len=request.crop.duration_days
    for w in request.weather:
        current=date.fromisoformat(w.date)
        elapsed=(current-planting).days+1
        active=1<=elapsed<=season_len
        if active:
            kc,stage=kc_at_day(elapsed,request.crop.stage_lengths_days,
                               (request.crop.kc_initial,request.crop.kc_mid,request.crop.kc_end))
        else:
            kc=request.fallow_kc
            stage=None
            if kc is None:
                fail("FALLOW_ASSUMPTION_REQUIRED", "fallow Kc missing")
        d=fao_day(request.soil,dr,et0=w.reference_et_mm,kc=kc,rain=w.rainfall_mm,
                  runoff=w.runoff_mm,irrigation=request.irrigation_mm_by_date.get(w.date,0.0))
        dr=d["depletionEndMm"]
        raw_rows.append({"date":w.date,"cropActive":active,**d})
        metrics={
          "rootZoneDepletionMm": {"status":"available","value":dr,"unit":"mm","definition":"depletion from field capacity at day end"},
          "soilThetaM3M3": {"status":"available","value":d["soilThetaEndM3M3"],"unit":"m3/m3","definition":"homogeneous root-zone mean; not soil-layer profile"},
          "actualEtMm": {"status":"available" if active else "inactive","value":d["actualEtMm"] if active else None,"unit":"mm/day","definition":"FAO56 actual crop ET; unavailable outside declared crop season"},
          "potentialEtMm": {"status":"available" if active else "inactive","value":d["potentialEtMm"] if active else None,"unit":"mm/day","definition":"single Kc x reference ET0"},
          "waterStressKs": {"status":"available" if active else "inactive","value":d["ks"] if active else None,"unit":"fraction","definition":"1=no stress, 0=maximum stress"},
          "fallowEtMm": {"status":"available" if not active else "inactive","value":d["actualEtMm"] if not active else None,"unit":"mm/day","definition":"explicit illustrative fallow coefficient; not calibrated evaporation"},
          "drainageMm": {"status":"available","value":d["drainageMm"],"unit":"mm/day","definition":"water leaving fixed root zone"},
          "biomassTonnesPerHa": {"status":"unsupported","value":None,"unit":"tonnes/ha","definition":"FAO56 does not simulate biomass"},
          "yieldTonnesPerHa": {"status":"unsupported","value":None,"unit":"tonnes/ha","definition":"FAO56 does not simulate yield"},
        }
        v01={"plotId":request.plot_id,"branchId":request.branch_id,"date":w.date,
             "engine":"fao56","modelVersion":FAO_ENGINE_VERSION,"growthStage":stage,
             "rootZoneDepletionMm":dr,"actualEtMm":d["actualEtMm"] if active else None,
             "rainfallMm":w.rainfall_mm,
             "effectiveIrrigationMm":request.irrigation_mm_by_date.get(w.date,0.0),
             "drainageMm":d["drainageMm"],"waterStressIndex":(1-d["ks"]) if active else None,
             "biomassTonnesPerHa":None,"yieldTonnesPerHa":None}
        states.append({"v01C3":v01,"plotId":request.plot_id,"branchId":request.branch_id,
                       "date":w.date,"runId":run_id,"cropActive":active,"elapsedDay":elapsed if active else None,
                       "status":"active" if active else "inactive", "metrics":metrics,
                       "weatherMemberId":w.member_id,"provenanceId":request.input_snapshot_id})
    cumulative_residual=math.fsum(row["conservationResidualMm"] for row in raw_rows)
    if abs(cumulative_residual)>BALANCE_TOL_MM*max(1,len(raw_rows)):
        fail("CONSERVATION_FAILURE", "accumulated daily residual failed")
    warnings=["Water-balance numerical validation is not field/crop/yield calibration.",
              "Single-Kc model with fixed root depth; no layered soil-water or dual-Kc transpiration."]
    if request.crop.mapping_status=="provisional":
        warnings.append("Four-stage Kc calendar is a provisional sensitivity mapping, not observed canopy phenology.")
    if request.fallow_kc is not None:
        warnings.append("Fallow Kc is an explicit simplifying assumption, not verified bare-soil evaporation.")
    totals = {k:math.fsum(row[k] for row in raw_rows) for k in
              ("rainfallMm", "runoffMm", "irrigationMm", "capillaryRiseMm", "actualEtMm", "drainageMm")}
    window_residual = math.fsum((raw_rows[0]["storageStartMm"], totals["rainfallMm"], totals["irrigationMm"],
                       totals["capillaryRiseMm"], -totals["runoffMm"], -totals["actualEtMm"],
                       -totals["drainageMm"], -raw_rows[-1]["storageEndMm"]))
    if abs(window_residual) > BALANCE_TOL_MM * len(raw_rows):
        fail("CONSERVATION_FAILURE", "independent full-window storage balance failed")
    result = {"contractVersion":CONTRACT_VERSION,"runId":run_id,"status":"completed",
            "scientificOutputVersion":OUTPUT_VERSION,"adapterVersion":ADAPTER_VERSION,
            "registryVersion":REGISTRY_VERSION,"capability":registration,
            "evidenceKind":"executed-fao56","waterBalance":{
                "status":"verified", "scope":"continuous full input window including fallow",
                "unit":"mm", "initialStorageMm":raw_rows[0]["storageStartMm"],
                "finalStorageMm":raw_rows[-1]["storageEndMm"], "totals":totals,
                "residualMm":window_residual,"toleranceMm":BALANCE_TOL_MM * len(raw_rows)},
            "engine":"fao56","modelVersion":FAO_ENGINE_VERSION,
            "plotId":request.plot_id,"branchId":request.branch_id,"areaM2":request.area_m2,
            "plantingDate":request.planting_date,"inputSnapshotId":request.input_snapshot_id,
            "weatherRealizationId":request.weather_realization_id,
            "weatherMemberId":request.weather[0].member_id,
            "inputHash":input_hash,"weatherHash":stable_hash([asdict(w) for w in request.weather]),
            "soil":asdict(request.soil),"crop":asdict(request.crop),"comparableBaseline":request.comparable_baseline(),
            "initialDepletionMm":request.initial_depletion_mm,"startDate":request.start_date,
            "endDate":request.end_date,"fallowKc":request.fallow_kc,"irrigationSource":request.irrigation_source,
            "warnings":warnings,"states":states,
            "summary":{"days":len(states),"activeCropDays":sum(s["cropActive"] for s in states),
                       "cropSeasonComplete":request.end_date >= (planting+timedelta(days=season_len-1)).isoformat(),
                       "activeActualEtMm":math.fsum(r["actualEtMm"] for r in raw_rows if r["cropActive"]),
                       "effectiveIrrigationMm":totals["irrigationMm"],
                       "maxAbsResidualMm":max(abs(r["conservationResidualMm"]) for r in raw_rows),
                       "cumulativeResidualMm":cumulative_residual}}
    return validate_run(result)
