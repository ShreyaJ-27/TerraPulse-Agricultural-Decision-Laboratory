"""Create deterministic SYNTHETIC comparison inputs (not a farm forecast).
Run from the package root: python examples/make_fixtures.py
"""
from __future__ import annotations
from datetime import date,timedelta
from dataclasses import asdict
from pathlib import Path
import json,math,sys

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/"src"))
from terrapulse_science import turmeric_profile
START=date(2025,5,1)
END=date(2026,4,11)
PROVENANCE={"provider":"Developer A synthetic calendar fixture", "reference":"examples/make_fixtures.py",
    "kind":"assumption","acquiredAt":"2026-11-13T00:00:00+05:30",
    "notes":"Synthetic mathematical input; NOT field weather or climate forecast"}
W=[]
for i in range((END-START).days+1):
    d=START+timedelta(days=i)
    phase=2*math.pi*((d-date(2025,1,1)).days-79)/365.25
    W.append({"date":d.isoformat(),"rainfall_mm":12.0 if i%11==0 else 0.0,
       "reference_et_mm":4.5+math.sin(phase),"runoff_mm":0,
       "min_temp_c":21.0,"max_temp_c":33.0,
       "member_id":"synthetic-member-1","provenance":PROVENANCE})
BASE={"plot_id":"plot-test-1","branch_id":"original","area_m2":100,
      "planting_date":"2025-05-15","start_date":START.isoformat(),"end_date":END.isoformat(),
      "weather_realization_id":"demo-absolute-calendar-fixed-inputs",
      "input_snapshot_id":"demo-synthetic-snapshot-1","initial_depletion_mm":15.0,
      "soil":{"root_depth_m":.30,"field_capacity":.30,"wilting_point":.15,
              "depletion_fraction":.40,"parameter_source":"synthetic soil example; not SoilGrids",
              "parameter_version":"synthetic-soil-1"},
      "crop":asdict(turmeric_profile()),
      "weather":W,"irrigation_mm_by_date":{},"irrigation_source":"explicit-fixture",
      "fallow_kc":.20}
DELAYED={**BASE,"branch_id":"planting-one-month-later","planting_date":"2025-06-15"}
IRRIGATED={**BASE,"branch_id":"irrigation-choice","irrigation_mm_by_date":{"2025-06-15":5.0,"2025-07-16":5.0}}
for name,obj in [('fao_baseline.json',BASE),('fao_delayed.json',DELAYED),('fao_irrigated.json',IRRIGATED)]:
    (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Generated three synthetic C3/FAO56 fixtures with one shared absolute-date weather series.')
