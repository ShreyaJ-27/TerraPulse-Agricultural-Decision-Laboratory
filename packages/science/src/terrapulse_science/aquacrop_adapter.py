"""AquaCrop-OSPy 3.1.0 published-example adapter and strict daily output parser.

Important: a zero-filled output slot with a reset counter is NOT a valid
simulated crop state. Wr is root-zone WATER STORAGE, not FAO56 depletion.
Daily biomass is g/m2; convert g/m2 to tonnes/ha with /100. Final dry yield
is already tonnes/ha in final_results and is NOT daily DryYield.

This only runs the documented Tunis/Wheat/SandyLoam example. Add another crop
only after C7 registration, sourced parameters and an independent golden test.
"""
from __future__ import annotations
from datetime import date,timedelta
import csv, hashlib, importlib.metadata, math
from pathlib import Path
from typing import Any
from .contracts import CONTRACT_VERSION, ScienceError, fail, iso_date, real, stable_hash, nonempty
from .capability import AQUA_PROFILE, WEATHER_SHA256, OUTPUT_VERSION, ADAPTER_VERSION, REGISTRY_VERSION, require_aquacrop
from .validation import validate_run
from .aquacrop_reference import REFERENCE_CSV_SHA256, REFERENCE_SOIL_PROFILE

ENGINE_VERSION="aquacrop-ospy-3.1.0"
UPSTREAM_UNITS = {"biomass":"g/m2", "z_root":"m", "canopy_cover":"fraction",
    "Wr":"mm", "Es":"mm/day", "Tr":"mm/day", "EsPot":"mm/day", "TrPot":"mm/day",
    "IrrDay":"mm/day", "DeepPerc":"mm/day", "Dry yield (tonne/ha)":"tonnes/ha"}
BALANCE_TOL_MM = 1e-7
START_DATE = AQUA_PROFILE["startDate"]
END_DATE = AQUA_PROFILE["endDate"]

def read_csv(path: str | Path) -> list[dict]:
    with Path(path).open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def _number(row:dict,key:str,*,allow_missing:bool=False) -> float|None:
    if key not in row:
        fail("AQUACROP_COLUMN_MISSING",f"AquaCrop column {key} missing")
    x=row[key]
    if isinstance(x, bool):fail("AQUACROP_INVALID_NUMBER", f"boolean {key}")
    if (x is None or x=="") and allow_missing:return None
    try:
        y=float(x)
    except (TypeError,ValueError):
        fail("AQUACROP_INVALID_NUMBER",f"AquaCrop invalid {key}: {x}")
    return real(y,f"aquacrop.{key}")

def _metric(value:float|None,unit:str,desc:str) -> dict:
    return {"status":"available" if value is not None else "unsupported",
            "value":value,"unit":unit,"definition":desc}

def _is_unexecuted(growth, flux):
    return all(_number(row, key) == 0 for row in (growth, flux) for key in row)


def audit_water_balance(growth, flux, storage, soil_profile):
    """Close the full soil profile on executed days of the registered example.

    With off-season simulation disabled, the engine restores field capacity
    at each sowing. A skipped interval has no simulated storage trajectory.
    """
    if not growth or not len(growth) == len(flux) == len(storage):
        fail("AQUACROP_ROWS_MISMATCH", "storage must align with daily output slots")
    if len(soil_profile) != len(REFERENCE_SOIL_PROFILE) or any(
        len(row) != 4 or any(not math.isclose(real(value, "soil profile"), expected,
            rel_tol=0, abs_tol=1e-9) for value, expected in zip(row, reference))
        for row, reference in zip(soil_profile, REFERENCE_SOIL_PROFILE)
    ):
        fail("AQUACROP_PROFILE_MISMATCH", "expected registered SandyLoam compartment profile")
    initial = math.fsum(1000 * dz * fc for dz, _, fc, _ in soil_profile)
    previous = initial
    previous_slot = -1
    residuals, resets = [], []
    min_storage = max_storage = None
    for slot, (g, f, w) in enumerate(zip(growth, flux, storage)):
        theta = [_number(w, f"th{j}") for j in range(1, len(soil_profile) + 1)]
        if _is_unexecuted(g, f):
            if any(_number(w, key) != 0 for key in w):
                fail("AQUACROP_INVALID_SLOT", f"nonzero storage in unexecuted slot {slot}")
            continue
        dap = _number(g, "dap")
        if (_number(w, "time_step_counter") != slot or _number(w, "dap") != dap
            or _number(w, "growing_season") != int(dap > 0)):
            fail("AQUACROP_COUNTER_MISMATCH", f"storage alignment at slot {slot}")
        for value, (_, dry, _, sat) in zip(theta, soil_profile):
            if not dry - 1e-9 <= value <= sat + 1e-9:
                fail("AQUACROP_STORAGE_BOUNDS", f"compartment theta outside dry-to-saturated bounds at slot {slot}")
        # This specific boundary has no ponding, irrigation, drainage tiles
        # or groundwater. Refuse to apply it to a different configuration.
        if any(_number(f, key) != 0 for key in ("surface_storage","IrrDay","TileDrain","CR","GwIn")):
            fail("AQUACROP_BALANCE_UNSUPPORTED", f"unexpected boundary flux or surface storage at slot {slot}")
        consecutive = slot == previous_slot + 1
        if dap == 1:
            resets.append({"slot":slot, "resetStorageMm":initial,
                           "changeFromPreviousDayMm":initial - previous if consecutive and slot else None})
            start = initial
        elif consecutive:
            start = previous
        else:
            fail("AQUACROP_BALANCE_GAP", f"slot {slot} has no preceding storage or planting reset")
        end = math.fsum(1000 * dz * value for (dz, _, _, _), value in zip(soil_profile, theta))
        infiltration, percolation, evaporation, transpiration = [
            real(_number(f, key), key, minimum=0) for key in ("Infl","DeepPerc","Es","Tr")]
        # Infl is net infiltration at the profile boundary. Rain and runoff
        # have already been partitioned before it enters this equation.
        residual = math.fsum((start, infiltration, -percolation, -evaporation, -transpiration, -end))
        if abs(residual) > BALANCE_TOL_MM:
            fail("AQUACROP_CONSERVATION", f"profile residual {residual:.9g} mm at slot {slot}")
        residuals.append(residual)
        min_storage = end if min_storage is None else min(min_storage, end)
        max_storage = end if max_storage is None else max(max_storage, end)
        previous, previous_slot = end, slot
    if not residuals:
        fail("AQUACROP_BALANCE_EMPTY", "no executed days to audit")
    return {"status":"verified", "scope":"executed-day soil profile with explicit field-capacity planting resets",
            "auditedDays":len(residuals), "unexecutedSlots":len(growth)-len(residuals), "plantingResets":resets,
            "initialProfileStorageMm":initial, "minEndProfileStorageMm":min_storage,
            "maxEndProfileStorageMm":max_storage, "maxAbsResidualMm":max(map(abs,residuals)),
            "sumDailyResidualMm":math.fsum(residuals), "dailyToleranceMm":BALANCE_TOL_MM}


def parse_aquacrop_outputs(**kwargs):
    """Parse caller-supplied tables with unverified execution provenance."""
    if kwargs.get("evidence_kind", "provided-unverified-output") != "provided-unverified-output":
        fail("INVALID_PROVENANCE", "use the verified fixture loader or live runner")
    return _parse_aquacrop_outputs(**kwargs)


def _parse_aquacrop_outputs(*,growth:list[dict],flux:list[dict],final:list[dict],
         start_date:str, plot_id:str,branch_id:str, input_snapshot_id:str,
         weather_realization_id:str, parameter_version:str="Tunis-Wheat-example-3.1.0",
         soil_type:str="SandyLoam",crop_name:str="Wheat",
         model_version:str="3.1.0", weather_sha256:str|None=None,
         evidence_kind:str="provided-unverified-output", source_units:dict|None=None,
         storage:list[dict]|None=None, soil_profile:list[dict]|None=None, requested_outputs=()) -> dict:
    iso_date(start_date,"start_date")
    capability = require_aquacrop(crop_name, soil_type, model_version, parameter_version, requested_outputs)
    for key, value in (("plot_id",plot_id),("branch_id",branch_id),("input_snapshot_id",input_snapshot_id),("weather_realization_id",weather_realization_id)):
        nonempty(value,key)
    if weather_sha256 is not None and weather_sha256 != WEATHER_SHA256:
        fail("AQUACROP_WEATHER_HASH_MISMATCH", "weather content not the registered Tunis example")
    if source_units is not None and source_units != UPSTREAM_UNITS:
        fail("UNIT_MISMATCH", "input units must match the AquaCrop 3.1.0 export schema exactly")
    if evidence_kind not in {"provided-unverified-output", "historical-fixture", "executed-aquacrop"}:
        fail("INVALID_PROVENANCE", "unknown evidence kind")
    if not growth or len(growth)!=len(flux):
        fail("AQUACROP_ROWS_MISMATCH", "nonempty crop growth and flux must have identical allocated row count")
    origin=date.fromisoformat(start_date)
    # Check alignment before decoding values, including malformed inactive rows.
    for i,(g,f) in enumerate(zip(growth,flux)):
        cg,cf = _number(g,"time_step_counter"),_number(f,"time_step_counter")
        if cg != cf: fail("AQUACROP_COUNTER_MISMATCH", f"row {i}")
        if cg not in (0,i): fail("AQUACROP_INVALID_SLOT", f"row {i}")
    states=[]
    previous_crop = None
    slot_count={"cropActive":0,"cropInactive":0,"unexecuted":0}
    for i,(g,f) in enumerate(zip(growth,flux)):
        cg=_number(g,"time_step_counter")
        cf=_number(f,"time_step_counter")
        dap=_number(g,"dap")
        if cg!=cf:
            fail("AQUACROP_COUNTER_MISMATCH",f"growth and flux counter mismatch at row {i}")
        current=(origin+timedelta(days=i)).isoformat()
        if _is_unexecuted(g,f):
            slot_count["unexecuted"]+=1
            continue
        if cg!=i:
            # The model preallocates rows filled with reset zero counters after
            # harvest. Do not interpret any other numeric zero as a crop state.
            fail("AQUACROP_INVALID_SLOT",f"nonzero contents in reset-counter slot {i}")
        if dap<0 or int(dap)!=dap:
            fail("AQUACROP_INVALID_DAP",f"invalid days after planting at {i}")
        season = _number(g,"season_counter")
        if season != int(season) or season < -1 or (dap>0 and season<0):
            fail("AQUACROP_INVALID_SEASON", f"invalid season at {i}")
        if _number(f,"dap") != dap or _number(f,"season_counter") != season:
            fail("AQUACROP_COUNTER_MISMATCH", f"growth/flux season or dap at {i}")
        if dap:
            if previous_crop is None:
                expected = (0, 1)
            elif season == previous_crop[0]:
                expected = (season, previous_crop[1]+1)
                if i != previous_crop[2]+1:
                    fail("AQUACROP_INVALID_SEASON", "gap within an executed crop season")
            else:
                expected = (previous_crop[0]+1, 1)
            if (season,dap) != expected:
                fail("AQUACROP_INVALID_SEASON", f"invalid season or DAP sequence at {i}")
            previous_crop = (season,dap,i)
        gw = f.get("z_gw")
        if gw is not None and gw != "" and str(gw).lower() != "nan":
            fail("AQUACROP_UNSUPPORTED", "groundwater is absent in the registered example")
        es=_number(f,"Es");tr=_number(f,"Tr")
        es_pot=_number(f,"EsPot");tr_pot=_number(f,"TrPot")
        wr=_number(f,"Wr")
        depth=_number(g,"z_root")
        cover=_number(g,"canopy_cover")
        biomass_g_m2=_number(g,"biomass")
        irrigation=_number(f,"IrrDay");drainage=_number(f,"DeepPerc")
        for key,x in [("Es",es),("Tr",tr),("EsPot",es_pot),("TrPot",tr_pot),
                      ("Wr",wr),("z_root",depth),("biomass",biomass_g_m2), ("IrrDay",irrigation),("DeepPerc",drainage)]:
            if x < 0:fail("AQUACROP_INVALID_OUTPUT",f"negative {key} on {current}")
        if not (0<=cover<=1):
            fail("AQUACROP_INVALID_OUTPUT",f"canopy fraction invalid on {current}")
        actual_et=es+tr
        potential_et=es_pot+tr_pot
        if dap==0:
            slot_count["cropInactive"]+=1
            states.append({"date":current,"status":"inactive","plotId":plot_id,
                "branchId":branch_id,"metrics":{
                    "actualEtMm":{"status":"inactive","value":None,"unit":"mm/day","definition":"no active crop"},
                    "fallowEtMm":_metric(actual_et,"mm/day","executed AquaCrop preplant evaporation"),
                    "rootWaterStorageMm":_metric(wr,"mm","executed model root-zone storage"),
                    "drainageMm":_metric(drainage,"mm/day","executed drainage")},"v01C3":None})
            continue
        if actual_et>potential_et+1e-6:
            fail("AQUACROP_INVALID_OUTPUT",f"actual ET exceeds potential ET on {current}")
        metrics={
            "actualEtMm":_metric(actual_et,"mm/day","AquaCrop Es + Tr; actual soil evaporation and transpiration"),
            "potentialEtMm":_metric(potential_et,"mm/day","AquaCrop EsPot + TrPot"),
            "rootWaterStorageMm":_metric(wr,"mm","AquaCrop Wr; storage NOT depletion"),
            "rootDepthM":_metric(depth,"m","AquaCrop simulated effective root depth"),
            "canopyCoverFraction":_metric(cover,"fraction","AquaCrop simulated canopy cover"),
            "biomassTonnesPerHa":_metric(biomass_g_m2/100,"tonnes/ha","AquaCrop biomass g/m2 / 100"),
            "rootZoneDepletionMm":_metric(None,"mm","requires separate defensible profile conversion; Wr is storage"),
            "yieldTonnesPerHa":_metric(None,"tonnes/ha","read final-season result only, not daily DryYield"),
            "waterStressKs":_metric(None,"fraction","not available from these exported tables"),
            "groundwaterDepthM":{"status":"unavailable","value":None,"unit":"m","definition":"no groundwater configured in registered example"},
            "drainageMm":_metric(drainage,"mm/day","AquaCrop deep percolation"),
        }
        v01={"plotId":plot_id,"branchId":branch_id,"date":current,
              "engine":"aquacrop","modelVersion":ENGINE_VERSION,"growthStage":None,
              "rootZoneDepletionMm":None,"actualEtMm":actual_et,
              "rainfallMm":None,"effectiveIrrigationMm":irrigation,
              "drainageMm":drainage,"waterStressIndex":None,
              "biomassTonnesPerHa":biomass_g_m2/100,"yieldTonnesPerHa":None}
        states.append({"date":current,"status":"active","plotId":plot_id,"branchId":branch_id,
                       "seasonCounter":int(_number(g,"season_counter")),"dap":int(dap),
                       "v01C3":v01,"metrics":metrics})
        slot_count["cropActive"]+=1
    harvests=[]
    seen_seasons=set()
    for row in final:
        dt=row.get("Harvest Date (YYYY/MM/DD)")
        if dt is None:fail("AQUACROP_HARVEST_DATE","harvest date missing")
        dt=str(dt)[:10]
        try:
            day=date.fromisoformat(dt.replace("/","-"))
        except ValueError:
            fail("AQUACROP_HARVEST_DATE",f"invalid date {dt}")
        y=_number(row,"Dry yield (tonne/ha)")
        season=_number(row,"Season")
        irr=_number(row,"Seasonal irrigation (mm)")
        step=_number(row,"Harvest Date (Step)")
        if season != int(season) or season < 0 or season in seen_seasons or y<0 or irr<0:
            fail("AQUACROP_INVALID_HARVEST", "invalid/duplicate seasonal output")
        if row.get("crop Type") != "Wheat" or step!=int(step) or (day-origin).days != step+1:
            fail("AQUACROP_INVALID_HARVEST", "harvest date, crop or step mismatch")
        last_day=(day-timedelta(days=1)).isoformat()
        season_days=[s["date"] for s in states if s.get("seasonCounter")==season]
        if not season_days or season_days[-1] != last_day:
            fail("AQUACROP_INVALID_HARVEST", "harvest has no matching executed season/date")
        seen_seasons.add(season)
        harvests.append({"season":int(season),"harvestDate":day.isoformat(),
                         "dryYieldTonnesPerHa":y,
                         "seasonalIrrigationMm":irr})
    summary={"totalAllocatedSlots":len(growth),**slot_count,"harvestedSeasons":len(harvests)}
    if evidence_kind != "provided-unverified-output" and (
        len(harvests) != 6 or (origin+timedelta(days=len(growth)-1)).isoformat() != END_DATE
    ):
        fail("RUN_INCOMPLETE", "registered example requires six completed seasons and its full output window")
    # Optional real AquaCrop DataFrames contain numpy scalars, pandas Timestamps,
    # and a documented NaN groundwater-depth sentinel. They are NOT JSON floats.
    def digest_rows(rows):
        import json
        def normalize(value):
            if isinstance(value,dict):return {str(k):normalize(v) for k,v in value.items()}
            if isinstance(value,(list,tuple)):return [normalize(v) for v in value]
            if value is None:return None
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                x=float(value)
                return x if math.isfinite(x) else None
            if isinstance(value,str):
                if value == "":return None
                try:return float(value)
                except ValueError:return value
            if hasattr(value,"item"):
                try:return normalize(value.item())
                except (TypeError,ValueError):pass
            if hasattr(value,"isoformat"):return value.isoformat()[:10]
            return str(value)
        return stable_hash(normalize(rows))
    digests = {"cropGrowth":digest_rows(growth),"waterFlux":digest_rows(flux),
               "seasonalResults":digest_rows(final),"waterStorage":digest_rows(storage) if storage is not None else None}
    input_id=stable_hash({"plot":plot_id,"branch":branch_id,"snapshot":input_snapshot_id,
       "weather":weather_realization_id,"model":model_version,"parameter":parameter_version,
       "crop":crop_name,"soil":soil_type,"start":start_date,
       "weatherSha256":weather_sha256,"adapterVersion":ADAPTER_VERSION,
       "tableHashes":digests,"evidenceKind":evidence_kind,"soilProfile":soil_profile})
    result = {"contractVersion":CONTRACT_VERSION,"runId":input_id,
      "scientificOutputVersion":OUTPUT_VERSION,"adapterVersion":ADAPTER_VERSION,"registryVersion":REGISTRY_VERSION,
      "weatherHash":weather_sha256,"evidenceKind":evidence_kind,"tableHashes":digests,
      "capability":capability,
      "sourceUnits":dict(UPSTREAM_UNITS),
      "parameterSource":"AquaCrop-OSPy 3.1.0 published example and bundled Wheat/SandyLoam defaults",
      "waterBalance":audit_water_balance(growth,flux,storage,soil_profile) if storage is not None and soil_profile is not None else
          {"status":"unavailable","reason":"profile storage, compartment parameters and initial water are required"},
      "engine":"aquacrop","modelVersion":ENGINE_VERSION,"status":"completed-output-parse",
      "plotId":plot_id,"branchId":branch_id,"inputSnapshotId":input_snapshot_id,
      "weatherRealizationId":weather_realization_id,"parameterVersion":parameter_version,
      "startDate":start_date,"endDate":(origin+timedelta(days=len(growth)-1)).isoformat(),"soilType":soil_type,"cropName":crop_name,
      "firstPlantingDate":next((x["date"] for x in states if x["status"]=="active"),None),
      "warnings":["Tunis wheat published example is not calibrated for other sites or crops.",
                  "AquaCrop daily unexecuted zero-filled slots are deliberately excluded.",
                  "Daily yield is unavailable; dry yield comes only from final seasonal results."],
      "summary":summary,"states":states,"harvests":sorted(harvests,key=lambda x:x["season"])}
    return validate_run(result)


def parse_aquacrop_fixture(directory:str|Path,*,label:str="baseline",**kwargs)->dict:
    p=Path(directory)
    if label not in {"baseline","repeat","planting_11_01"} or kwargs.get("start_date") != START_DATE:
        fail("AQUACROP_UNSUPPORTED", "expected a pinned fixture label and its registered start date")
    tables = {}
    for kind in ("crop_growth","water_flux","final_results","water_storage"):
        name = f"{label}_{kind}.csv"
        data = (p/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != REFERENCE_CSV_SHA256[name]:
            fail("AQUACROP_FIXTURE_HASH_MISMATCH", name)
        tables[kind] = list(csv.DictReader(data.decode("utf-8-sig").splitlines()))
    return _parse_aquacrop_outputs(growth=tables["crop_growth"],flux=tables["water_flux"],
        final=tables["final_results"],storage=tables["water_storage"],soil_profile=REFERENCE_SOIL_PROFILE,
        weather_sha256=WEATHER_SHA256,evidence_kind="historical-fixture",**kwargs)


def run_published_wheat(*, planting_mmdd:str="10/01", plot_id:str="tunis-demo",
                        branch_id:str="original",input_snapshot_id:str="aquacrop-tunis-example",
                        weather_realization_id:str="tunis_climate.txt-verified", requested_outputs=()) ->dict:
    """Execute ONLY the published 3.1.0 example. Requires optional dependency.

    `planting_mmdd` may be 10/01 or 11/01, the two historical golden runs.
    Other arbitrary user fields/crops intentionally fail safely.
    """
    require_aquacrop("Wheat","SandyLoam","3.1.0",AQUA_PROFILE["parameterVersion"],requested_outputs)
    if planting_mmdd not in AQUA_PROFILE["plantingDatesMmDd"]:
        fail("AQUACROP_UNSUPPORTED", "only 10/01 and 11/01 published-example planting comparison supported")
    try:
        version=importlib.metadata.version("aquacrop")
    except importlib.metadata.PackageNotFoundError:
        fail("DEPENDENCY_UNAVAILABLE", "install optional aquacrop==3.1.0 under supported Python 3.12 runtime")
    if version!="3.1.0":
        fail("AQUACROP_VERSION_MISMATCH", "expected exact aquacrop==3.1.0")
    from aquacrop import AquaCropModel, Soil as AquaSoil, Crop, InitialWaterContent
    from aquacrop.utils import prepare_weather, get_filepath
    weather_path=get_filepath("tunis_climate.txt")
    verified_weather_sha256=hashlib.sha256(Path(weather_path).read_bytes()).hexdigest()
    if verified_weather_sha256!=WEATHER_SHA256:
        fail("AQUACROP_WEATHER_HASH_MISMATCH", "published-example Tunis climate differs from validated source")
    weather=prepare_weather(weather_path)
    model=AquaCropModel(sim_start_time="1979/10/01",sim_end_time="1985/05/30",
      weather_df=weather.copy(deep=True),soil=AquaSoil(soil_type="SandyLoam"),
      crop=Crop("Wheat",planting_date=planting_mmdd),
      initial_water_content=InitialWaterContent(value=["FC"]))
    if model.run_model(till_termination=True) is not True:
        fail("RUN_INCOMPLETE", "AquaCrop did not report successful termination")
    profile=tuple(tuple(row[key] for key in ("dz","th_dry","th_fc","th_s"))
                  for row in model.soil.profile.to_dict(orient="records"))
    return _parse_aquacrop_outputs(
       growth=model.get_crop_growth().to_dict(orient="records"),
       flux=model.get_water_flux().to_dict(orient="records"),
       final=model.get_simulation_results().to_dict(orient="records"),
       storage=model.get_water_storage().to_dict(orient="records"),soil_profile=profile,
       weather_sha256=verified_weather_sha256,evidence_kind="executed-aquacrop",requested_outputs=requested_outputs,
       start_date="1979-10-01",plot_id=plot_id,branch_id=branch_id,
       input_snapshot_id=input_snapshot_id,weather_realization_id=weather_realization_id)
