"""Read Developer D v0.1 C1 and C8 structures without changing their schema.

C8's branch ledger is authoritative. A rejects mismatch instead of secretly
calculating or allocating water. All efficiencies are D's explicit assumptions.
"""
from __future__ import annotations
from dataclasses import asdict
from .contracts import (
    FaoRequest, Soil, CropKc, WeatherDay, ScienceError, fail,
    iso_date, nonempty, real,
)

LEDGER_TOL_L = 1e-6

def irrigation_from_c8(ledger: dict, *, plot_id: str, branch_id: str,
                       area_m2: float, start_date: str, end_date: str) -> dict[str,float]:
    """Return daily net infiltrated irrigation in mm; one L/m² equals one mm."""
    if not isinstance(ledger,dict):
        fail("INVALID_LEDGER", "C8 ledger must be an object")
    if ledger.get("branchId") != branch_id:
        fail("LEDGER_BRANCH_MISMATCH", "C8 branch does not match simulation")
    nonempty(ledger.get("reservoirId"), "reservoirId")
    initial=real(ledger.get("initialLiters"), "initialLiters",minimum=0)
    remaining=real(ledger.get("remainingLiters"), "remainingLiters",minimum=0)
    area=real(area_m2,"area_m2",minimum=0)
    if area <= 0:
        fail("INVALID_AREA", "area must be positive")
    entries=ledger.get("entries")
    if not isinstance(entries,list):
        fail("INVALID_LEDGER", "entries must be an array")
    sum_withdrawn=0.0
    by_date:dict[str,float]={}
    seen=set()
    for e in entries:
        if not isinstance(e,dict):
            fail("INVALID_LEDGER", "each ledger entry must be an object")
        allocation=nonempty(e.get("allocationId"),"allocationId")
        if allocation in seen:
            fail("DUPLICATE_ALLOCATION", "duplicate ledger allocationId")
        seen.add(allocation)
        d=e.get("date");iso_date(d)
        withdrawn=real(e.get("withdrawnLiters"),"withdrawnLiters",minimum=0)
        effective=real(e.get("effectiveLiters"),"effectiveLiters",minimum=0)
        loss=real(e.get("lossLiters"),"lossLiters",minimum=0)
        depth=real(e.get("effectiveIrrigationDepthMm"),"effectiveIrrigationDepthMm",minimum=0)
        if abs(withdrawn-effective-loss)>LEDGER_TOL_L:
            fail("LEDGER_CONSERVATION", "entry withdrawal != effective + loss")
        if effective>withdrawn+LEDGER_TOL_L:
            fail("LEDGER_CONSERVATION", "effective > withdrawn")
        sum_withdrawn+=withdrawn
        if e.get("plotId")==plot_id:
            if abs(depth - effective/area)>1e-8:
                fail("LEDGER_DEPTH_MISMATCH", "effective depth != effective liters / plot area")
            if not (start_date<=d<=end_date):
                if effective > 0:
                    fail("LEDGER_WINDOW", "nonzero plot allocation outside simulation window")
                continue
            by_date[d]=by_date.get(d,0.0)+depth
    if abs(initial-remaining-sum_withdrawn)>LEDGER_TOL_L:
        fail("LEDGER_CONSERVATION", "initial - withdrawals != remaining liters")
    return by_date


def from_c1_with_root_depth(*, c1: dict, plot_id: str, branch_id: str, area_m2: float,
            planting_date: str, start_date: str, end_date: str,
            crop: CropKc, root_depth_m: float, depletion_fraction: float,
            initial_depletion_mm: float, input_snapshot_id: str, weather_realization_id: str,
            ensemble_member_id: str | None, ledger: dict | None = None,
            explicit_irrigation_mm: dict[str,float] | None = None, fallow_kc: float | None = None,
            soil_parameter_version: str = "c1-snapshot") -> FaoRequest:
    if not isinstance(c1,dict) or not isinstance(c1.get("weather"),list) or not isinstance(c1.get("soilLayers"),list):
        fail("INVALID_C1", "C1 requires weather and soilLayers arrays")
    zr=real(root_depth_m,"root_depth_m",minimum=0)
    if zr<=0:fail("INVALID_SOIL", "root_depth_m must be > 0")
    layers=c1["soilLayers"]
    if not layers: fail("MISSING_SOIL", "C1 has no layers")
    if any(not isinstance(layer,dict) for layer in layers):
        fail("INVALID_SOIL", "each C1 soil layer must be an object")
    layers=sorted(layers,key=lambda layer:real(layer.get("fromCm"),"fromCm",minimum=0))
    prev=0.0
    fc=wp=None
    sources=[]
    for l in layers:
        bottom=real(l.get("toCm"),"toCm",minimum=0)
        top=real(l.get("fromCm"),"fromCm",minimum=0)
        if abs(top-prev)>1e-8:
            fail("SOIL_GAP", "soil layers must be contiguous from 0 cm")
        if bottom<=top:fail("INVALID_SOIL", "layer depth must increase")
        layer_fc=real(l.get("fieldCapacityM3M3"),"fieldCapacityM3M3")
        layer_wp=real(l.get("wiltingPointM3M3"),"wiltingPointM3M3")
        if fc is None:fc,wp=layer_fc,layer_wp
        elif abs(fc-layer_fc)>1e-12 or abs(wp-layer_wp)>1e-12:
            fail("HETEROGENEOUS_SOIL_UNSUPPORTED", "homogeneous FAO root-zone requires equal FC/WP in every used layer")
        source=l.get("provenance")
        if not isinstance(source,dict) or any(not source.get(k) for k in ("provider","kind","reference","acquiredAt")):
            fail("MISSING_PROVENANCE", "soil layer requires source and kind")
        sources.append(source["provider"])
        prev=bottom
        if prev>=zr*100-1e-8:break
    if prev<zr*100-1e-8:
        fail("SOIL_DEPTH_COVERAGE", "soil depth does not cover model root zone")
    soil=Soil(root_depth_m=zr,field_capacity=fc,wilting_point=wp,
              depletion_fraction=depletion_fraction,
              parameter_source=";".join(sorted(set(sources))),parameter_version=soil_parameter_version)
    chosen=[]
    for item in c1["weather"]:
        if item.get("ensembleMemberId")==ensemble_member_id:
            chosen.append(WeatherDay(date=item.get("date"),rainfall_mm=item.get("rainfallMm"),
               reference_et_mm=item.get("referenceEtMm"),min_temp_c=item.get("minTemperatureC"),
               max_temp_c=item.get("maxTemperatureC"),
               provenance=item.get("provenance"),member_id=ensemble_member_id,
               runoff_mm=item.get("runoffMm",0.0)))
    if ledger is not None and explicit_irrigation_mm is not None:
        fail("AMBIGUOUS_IRRIGATION", "provide C8 ledger or explicit fixture, not both")
    if ledger is not None:
        water=irrigation_from_c8(ledger,plot_id=plot_id,branch_id=branch_id,area_m2=area_m2,
                                 start_date=start_date,end_date=end_date)
        water_source="c8-ledger"
    elif explicit_irrigation_mm is not None:
        water=explicit_irrigation_mm
        water_source="explicit-fixture"
    else:
        fail("IRRIGATION_SOURCE_REQUIRED", "provide actual C8 ledger or explicit zero-irrigation fixture")
    req=FaoRequest(plot_id=plot_id,branch_id=branch_id,area_m2=area_m2,
          planting_date=planting_date,start_date=start_date,end_date=end_date,
          weather_realization_id=weather_realization_id,input_snapshot_id=input_snapshot_id,
          initial_depletion_mm=initial_depletion_mm,soil=soil,crop=crop,
          weather=tuple(chosen),irrigation_mm_by_date=water,
          irrigation_source=water_source,fallow_kc=fallow_kc)
    req.validate()
    return req
