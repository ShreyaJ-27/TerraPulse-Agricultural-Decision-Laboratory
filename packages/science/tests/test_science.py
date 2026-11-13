import copy
import csv
from datetime import date,timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile

# Editable install is optional: load source directly for a fresh ZIP extraction.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from terrapulse_science import (
    ScienceError,Soil,CropKc,WeatherDay,FaoRequest,fao_day,kc_at_day,run_fao,
    compare_runs,compare_aquacrop_runs,turmeric_profile,registry,from_c1_with_root_depth,
    irrigation_from_c8,parse_aquacrop_fixture,parse_aquacrop_outputs,
    run_published_wheat,request_from_dict
)

ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/'tests'/'fixtures'/'aquacrop_3_1_0'
SOIL=Soil(.30,.30,.15,.40,'synthetic FC/WP; Pereira 2024 p','1')
CROP=turmeric_profile('A')
SRC={'provider':'deterministic fixture','reference':'tests/test_science.py','kind':'assumption','acquiredAt':'2026-11-03T00:00:00Z'}

def req(branch='original',plant='2025-05-15',start='2025-05-01',end='2026-04-11',
        member='synthetic-v1', soil=SOIL, crop=CROP, rainfall=0, et0=5,
        irrig=None, snap='fixture-snapshot-01', fallow=.20):
    s=date.fromisoformat(start);e=date.fromisoformat(end)
    return FaoRequest(plot_id='plot-1',branch_id=branch,area_m2=100,
        planting_date=plant,start_date=start,end_date=end,
        weather_realization_id='same-absolute-calendar-series',input_snapshot_id=snap,
        initial_depletion_mm=15,soil=soil,crop=crop,
        weather=tuple(WeatherDay((s+timedelta(days=i)).isoformat(),rainfall,et0,SRC,member)
                      for i in range((e-s).days+1)),
        irrigation_mm_by_date=irrig or {},irrigation_source='explicit-fixture',fallow_kc=fallow)

class TestFaoNumerics(unittest.TestCase):
    def test_taw_raw(self):
        self.assertAlmostEqual(SOIL.taw_mm,45)
        d=fao_day(SOIL,15,et0=5,kc=1.05)
        self.assertAlmostEqual(d['rawMm'],18)
        self.assertAlmostEqual(d['actualEtMm'],5.25)
        self.assertAlmostEqual(d['depletionEndMm'],20.25)
    def test_rewetting(self):
        x=fao_day(SOIL,35,et0=5,kc=1.05)
        self.assertAlmostEqual(x['ks'],10/27)
        self.assertAlmostEqual(x['actualEtMm'],5.25*10/27)
    def test_excess_drainage(self):
        x=fao_day(SOIL,15,et0=5,kc=1.05,irrigation=100)
        self.assertAlmostEqual(x['actualEtMm'],5.25)
        self.assertAlmostEqual(x['drainageMm'],79.75)
        self.assertAlmostEqual(x['depletionEndMm'],0)
    def test_wilting(self):
        x=fao_day(SOIL,45,et0=5,kc=1.05)
        self.assertEqual(x['actualEtMm'],0)
        self.assertEqual(x['ks'],0)
    def test_water_cap_and_runoff(self):
        x=fao_day(SOIL,18,et0=1000,kc=1.05)
        self.assertAlmostEqual(x['actualEtMm'],27)
        y=fao_day(SOIL,15,et0=5,kc=1.05,rain=12,runoff=2,capillary=1)
        self.assertAlmostEqual(y['depletionEndMm'],9.25)
    def test_fao_example37(self):
        soil=Soil(.8,.32,.12,.4,'FAO Example 37','source')
        dr=55
        targets=[61,67,72.8,78.3,83.4,88.2,92.6,96.9,100.8,104.5]
        for target in targets:
            x=fao_day(soil,dr,et0=5,kc=1.2)
            self.assertLessEqual(abs(x['depletionEndMm']-target),0.1)
            dr=x['depletionEndMm']
        self.assertAlmostEqual(dr,104.505088934,places=7)
    def test_season_kc_sums(self):
        for mapping,expect in [('A',237.625),('B',213.25),('C',231.625)]:
            c=turmeric_profile(mapping)
            total=math.fsum(kc_at_day(t,c.stage_lengths_days,(c.kc_initial,c.kc_mid,c.kc_end))[0]
                            for t in range(1,c.duration_days+1))
            self.assertAlmostEqual(total,expect)
    def test_invalid_inputs(self):
        for x in [float('nan'),float('inf'),-1,True,'5']:
            with self.subTest(x=x):
                with self.assertRaises(ScienceError):fao_day(SOIL,15,et0=x,kc=1.05)
        with self.assertRaises(ScienceError):fao_day(SOIL,15,et0=5,kc=1,rain=1,runoff=2)
        with self.assertRaises(ScienceError):fao_day(SOIL,46,et0=5,kc=1)
    def test_daily_conservation_random_sweep(self):
        import random
        rng=random.Random(5602024)
        for _ in range(1000):
            rain=rng.uniform(0,100)
            x=fao_day(SOIL,rng.uniform(0,45),et0=rng.uniform(0,80),kc=rng.uniform(0,2),
                      rain=rain,runoff=rng.uniform(0,rain),irrigation=rng.uniform(0,100),
                      capillary=rng.uniform(0,3))
            self.assertLess(abs(x['conservationResidualMm']),1e-9)
            self.assertGreaterEqual(x['depletionEndMm'],-1e-9)
            self.assertLessEqual(x['depletionEndMm'],45+1e-9)

class TestFaoRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=run_fao(req())
    def test_result_provenance(self):
        r=self.a
        self.assertEqual(r['contractVersion'],'science-0.2')
        self.assertEqual(r['modelVersion'],'fao56-single-kc-1.0')
        self.assertEqual(len(r['inputHash']),64)
        self.assertEqual(r['weatherMemberId'],'synthetic-v1')
    def test_determinism(self):
        self.assertEqual(self.a,run_fao(req()))
        self.assertEqual(self.a['runId'],run_fao(req())['runId'])
    def test_no_yield(self):
        state=self.a['states'][15]
        self.assertIsNone(state['v01C3']['yieldTonnesPerHa'])
        self.assertEqual(state['metrics']['yieldTonnesPerHa']['status'],'unsupported')
        self.assertEqual(state['metrics']['biomassTonnesPerHa']['status'],'unsupported')
        self.assertAlmostEqual(state['v01C3']['waterStressIndex'],1-state['metrics']['waterStressKs']['value'])
    def test_fallow_not_zero_crop(self):
        state=self.a['states'][0]
        self.assertEqual(state['status'],'inactive')
        self.assertIsNone(state['v01C3']['actualEtMm'])
        self.assertIsNone(state['v01C3']['waterStressIndex'])
        self.assertEqual(state['metrics']['fallowEtMm']['status'],'available')
    def test_season_complete(self):
        self.assertTrue(self.a['summary']['cropSeasonComplete'])
        self.assertEqual(self.a['summary']['activeCropDays'],270)
        self.assertLess(self.a['summary']['maxAbsResidualMm'],1e-9)
    def test_missing_day_blocks(self):
        r=req()
        from dataclasses import replace
        with self.assertRaisesRegex(ScienceError,'WEATHER_COVERAGE'):
            run_fao(replace(r,weather=r.weather[:-1]))
    def test_duplicate_weather_blocks(self):
        r=req()
        from dataclasses import replace
        with self.assertRaisesRegex(ScienceError,'DUPLICATE_WEATHER'):
            run_fao(replace(r,weather=r.weather[:-1]+(r.weather[0],)))
    def test_missing_assumption_blocks(self):
        from dataclasses import replace
        with self.assertRaisesRegex(ScienceError,'FALLOW_ASSUMPTION_REQUIRED'):
            run_fao(replace(req(),fallow_kc=None))
    def test_mixed_member_blocks(self):
        from dataclasses import replace
        r=req()
        weather=list(r.weather);weather[5]=replace(weather[5],member_id='other')
        with self.assertRaisesRegex(ScienceError,'MIXED_WEATHER_MEMBERS'):
            run_fao(replace(r,weather=tuple(weather)))
    def test_invalid_date(self):
        from dataclasses import replace
        with self.assertRaisesRegex(ScienceError,'INVALID_DATE'):
            run_fao(replace(req(),end_date='2025-02-30'))
    def test_identity_change_changes_hash(self):
        self.assertNotEqual(self.a['runId'],run_fao(req(branch='alt'))['runId'])
        self.assertNotEqual(self.a['runId'],run_fao(req(irrig={'2025-06-01':4}))['runId'])
    def test_json_roundtrip(self):
        from dataclasses import asdict
        r=req()
        recreated=request_from_dict(json.loads(json.dumps(asdict(r))))
        self.assertEqual(self.a,run_fao(recreated))
    def test_no_weather_inference(self):
        from dataclasses import replace
        r=req();weather=list(r.weather);weather[0]=replace(weather[0],reference_et_mm=None)
        with self.assertRaisesRegex(ScienceError,'INVALID_NUMBER'):
            run_fao(replace(r,weather=tuple(weather)))
    def test_temperature_rejection(self):
        from dataclasses import replace
        r=req();w=list(r.weather);w[0]=replace(w[0],min_temp_c=34,max_temp_c=25)
        with self.assertRaisesRegex(ScienceError,'INVALID_TEMPERATURE'):
            run_fao(replace(r,weather=tuple(w)))
    def test_soil_physically_invalid(self):
        from dataclasses import replace
        with self.assertRaisesRegex(ScienceError,'INVALID_SOIL'):
            run_fao(replace(req(),soil=Soil(.3,.1,.15,.4,'x','1')))
    def test_no_arbitrary_map(self):
        with self.assertRaisesRegex(ScienceError,'UNSUPPORTED_MAPPING'):
            turmeric_profile('D')

class TestLedgerC1(unittest.TestCase):
    def setUp(self):
        self.ledger={"reservoirId":"reserve-1","branchId":"original","initialLiters":2000,
        "remainingLiters":1500,"entries":[{"allocationId":"alloc-1","date":"2025-05-15",
        "plotId":"plot-1","requestedLiters":500,"withdrawnLiters":500,
        "effectiveLiters":400,"lossLiters":100,"effectiveIrrigationDepthMm":4.0}]}
        self.c1={"location":{"latitude":12.9,"longitude":77.6},
           "soilLayers":[{"fromCm":0,"toCm":30,"fieldCapacityM3M3":.3,"wiltingPointM3M3":.15,
               "provenance":SRC}],
           "weather":[{"date":"2025-05-15","ensembleMemberId":"m1","rainfallMm":0,
                        "referenceEtMm":5,"minTemperatureC":22,"maxTemperatureC":32,"provenance":SRC}]}
    def test_ledger_conversion_and_reservoir(self):
        water=irrigation_from_c8(self.ledger,plot_id='plot-1',branch_id='original',area_m2=100,
                    start_date='2025-05-15',end_date='2025-05-15')
        self.assertEqual(water,{'2025-05-15':4})
    def test_single_day_integration(self):
        r=from_c1_with_root_depth(c1=self.c1,plot_id='plot-1',branch_id='original',area_m2=100,
            planting_date='2025-05-15',start_date='2025-05-15',end_date='2025-05-15',
            crop=turmeric_profile('A'),root_depth_m=.3,depletion_fraction=.4,initial_depletion_mm=15,
            input_snapshot_id='snapshot-1',weather_realization_id='realization-1',ensemble_member_id='m1',ledger=self.ledger)
        result=run_fao(r)
        self.assertAlmostEqual(result['states'][0]['v01C3']['rootZoneDepletionMm'],13.0)
        self.assertAlmostEqual(result['states'][0]['v01C3']['actualEtMm'],2.0) # Kc initial=0.40; ET0=5
        self.assertEqual(result['irrigationSource'],'c8-ledger')
    def test_bad_ledger_balance(self):
        self.ledger['remainingLiters']=1000
        with self.assertRaisesRegex(ScienceError,'LEDGER_CONSERVATION'):
            irrigation_from_c8(self.ledger,plot_id='plot-1',branch_id='original',area_m2=100,
                    start_date='2025-05-15',end_date='2025-05-15')
    def test_bad_ledger_depth(self):
        self.ledger['entries'][0]['effectiveIrrigationDepthMm']=5.0
        with self.assertRaisesRegex(ScienceError,'LEDGER_DEPTH_MISMATCH'):
            irrigation_from_c8(self.ledger,plot_id='plot-1',branch_id='original',area_m2=100,
                    start_date='2025-05-15',end_date='2025-05-15')
    def test_mismatched_branch(self):
        with self.assertRaisesRegex(ScienceError,'LEDGER_BRANCH_MISMATCH'):
            irrigation_from_c8(self.ledger,plot_id='plot-1',branch_id='other',area_m2=100,
                    start_date='2025-05-15',end_date='2025-05-15')
    def test_double_source_blocks(self):
        with self.assertRaisesRegex(ScienceError,'AMBIGUOUS_IRRIGATION'):
            from_c1_with_root_depth(c1=self.c1,plot_id='plot-1',branch_id='original',area_m2=100,
             planting_date='2025-05-15',start_date='2025-05-15',end_date='2025-05-15',crop=CROP,
             root_depth_m=.3,depletion_fraction=.4,initial_depletion_mm=15,input_snapshot_id='i',
             weather_realization_id='r',ensemble_member_id='m1',ledger=self.ledger,explicit_irrigation_mm={})
    def test_missing_soil_blocks(self):
        self.c1['soilLayers']=[]
        with self.assertRaisesRegex(ScienceError,'MISSING_SOIL'):
            from_c1_with_root_depth(c1=self.c1,plot_id='plot-1',branch_id='original',area_m2=100,
             planting_date='2025-05-15',start_date='2025-05-15',end_date='2025-05-15',crop=CROP,
             root_depth_m=.3,depletion_fraction=.4,initial_depletion_mm=15,input_snapshot_id='i',
             weather_realization_id='r',ensemble_member_id='m1',explicit_irrigation_mm={})
    def test_heterogeneous_soil_blocks(self):
        self.c1['soilLayers']=[dict(self.c1['soilLayers'][0],toCm=15),
            {**self.c1['soilLayers'][0],"fromCm":15,"toCm":30,"fieldCapacityM3M3":.35}]
        with self.assertRaisesRegex(ScienceError,'HETEROGENEOUS_SOIL_UNSUPPORTED'):
            from_c1_with_root_depth(c1=self.c1,plot_id='plot-1',branch_id='original',area_m2=100,
             planting_date='2025-05-15',start_date='2025-05-15',end_date='2025-05-15',crop=CROP,
             root_depth_m=.3,depletion_fraction=.4,initial_depletion_mm=15,input_snapshot_id='i',
             weather_realization_id='r',ensemble_member_id='m1',explicit_irrigation_mm={})

class TestFutureFold(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=run_fao(req())
        cls.b=run_fao(req(branch='later',plant='2025-06-15'))
    def test_independently_recomputed(self):
        self.assertNotEqual(self.a['runId'],self.b['runId'])
        self.assertEqual(compare_runs(self.a,self.b,fork_date='2025-05-01')['status'],'comparable')
    def test_seasonal_and_daily_compared(self):
        cmp=compare_runs(self.a,self.b,fork_date='2025-05-01')
        self.assertEqual(cmp['metrics'][0]['name'],'seasonalActualEtMm')
        self.assertTrue(cmp['daily'])
        self.assertTrue(cmp['skippedDates'])
    def test_no_inactive_as_zero(self):
        cmp=compare_runs(self.a,self.b,fork_date='2025-05-01')
        self.assertIn('2025-05-15',[v['date'] for v in cmp['skippedDates']])
    def test_reject_changed_weather_member(self):
        b=run_fao(req(branch='later',plant='2025-06-15',member='different'))
        self.assertEqual(compare_runs(self.a,b,fork_date='2025-05-01')['status'],'not-comparable')
    def test_reject_changed_soil(self):
        soil=Soil(.30,.31,.15,.4,'synthetic','2')
        b=run_fao(req(branch='later',plant='2025-06-15',soil=soil))
        self.assertIn('soil differs',compare_runs(self.a,b,fork_date='2025-05-01')['reasons'])
    def test_reject_changed_crop_parameters(self):
        b=run_fao(req(branch='later',plant='2025-06-15',crop=turmeric_profile('B')))
        self.assertEqual(compare_runs(self.a,b,fork_date='2025-05-01')['status'],'not-comparable')
    def test_fork_date_required(self):
        with self.assertRaisesRegex(ScienceError,'FORK_DATE_REQUIRED'):
            compare_runs(self.a,self.b)
    def test_late_fork_prevents_comparison(self):
        result=compare_runs(self.a,self.b,fork_date='2025-05-15')
        self.assertEqual(result['status'],'not-comparable')
        self.assertIn('forkDate must precede earliest planting decision',result['reasons'])
    def test_reject_same_run(self):
        with self.assertRaisesRegex(ScienceError,'NOT_INDEPENDENT'):
            compare_runs(self.a,self.a)
    def test_irrigation_alternative_allowed(self):
        b=run_fao(req(branch='irrigated',irrig={'2025-05-16':4}))
        self.assertEqual(compare_runs(self.a,b,fork_date='2025-05-01')['status'],'comparable')
    def test_changed_input_snapshot_not_comparable(self):
        b=run_fao(req(branch='later',plant='2025-06-15',snap='different'))
        self.assertIn('inputSnapshotId differs',compare_runs(self.a,b,fork_date='2025-05-01')['reasons'])

class TestAquaCropEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=parse_aquacrop_fixture(FIX,label='baseline',start_date='1979-10-01',
             plot_id='tunis-demo',branch_id='baseline',input_snapshot_id='tunis',weather_realization_id='fixture')
        cls.nov=parse_aquacrop_fixture(FIX,label='planting_11_01',start_date='1979-10-01',
             plot_id='tunis-demo',branch_id='nov',input_snapshot_id='tunis',weather_realization_id='fixture')
    def test_archived_csv_hashes(self):
        expected=json.loads((FIX/'sha256_manifest.json').read_text())
        for name,digest in expected.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((FIX/name).read_bytes()).hexdigest(),digest)
    def test_harvest_yield(self):
        self.assertEqual(len(self.original['harvests']),6)
        self.assertAlmostEqual(self.original['harvests'][0]['dryYieldTonnesPerHa'],8.940139992,places=7)
    def test_unexecuted_slots_not_zero(self):
        s=self.original['summary']
        self.assertGreater(s['unexecuted'],0)
        self.assertEqual(s['totalAllocatedSlots'],2069)
        last=self.original['states'][-1]
        self.assertLess(last['date'],'1985-05-30')
    def test_season_gap_inactive_not_fabricated(self):
        self.assertFalse(any(x['date']=='1980-04-15' and x['status']=='active' and x['v01C3']['rootZoneDepletionMm']==0
                              for x in self.original['states']))
    def test_storage_not_depletion(self):
        first=next(x for x in self.original['states'] if x['status']=='active')
        self.assertEqual(first['metrics']['rootZoneDepletionMm']['status'],'unsupported')
        self.assertIsNone(first['v01C3']['rootZoneDepletionMm'])
        self.assertAlmostEqual(first['metrics']['rootWaterStorageMm']['value'],63.08)
    def test_biomass_conversion(self):
        at_30=next(x for x in self.original['states'] if x.get('dap')==30 and x.get('seasonCounter')==0)
        self.assertAlmostEqual(at_30['metrics']['biomassTonnesPerHa']['value'],.46341365,places=5)
    def test_planting_date_changes(self):
        self.assertNotEqual(self.original['runId'],self.nov['runId'])
        self.assertEqual(self.nov['states'][0]['status'],'inactive')
        a=next(x for x in self.original['states'] if x['date']=='1980-01-15')
        b=next(x for x in self.nov['states'] if x['date']=='1980-01-15')
        self.assertEqual((a['dap'],b['dap']),(107,76))
        self.assertAlmostEqual(a['metrics']['canopyCoverFraction']['value'],.9164,delta=.002)
        self.assertAlmostEqual(b['metrics']['canopyCoverFraction']['value'],.7981,delta=.002)
    def test_aquacrop_controlled_comparison(self):
        comparison=compare_aquacrop_runs(self.original,self.nov,fork_date='1979-09-30')
        self.assertEqual(comparison['status'],'comparable')
        self.assertEqual(len(comparison['seasonalDryYield']),6)
        self.assertAlmostEqual(comparison['meanDryYieldA'],8.800855,places=4)
        self.assertAlmostEqual(comparison['meanDryYieldB'],8.61284937,places=4)
        self.assertTrue(comparison['skippedDates'])
        self.assertIn('1980-01-15',[r['date'] for r in comparison['daily']])
    def test_aquacrop_late_fork_blocks(self):
        result=compare_aquacrop_runs(self.original,self.nov,fork_date='1979-10-01')
        self.assertEqual(result['status'],'not-comparable')
    def test_aquacrop_unmatched_input_blocks(self):
        bad=copy.deepcopy(self.nov);bad['weatherRealizationId']='different'
        result=compare_aquacrop_runs(self.original,bad,fork_date='1979-09-30')
        self.assertIn('weatherRealizationId differs',result['reasons'])
    def test_bad_counter_rejected(self):
        g=[{'time_step_counter':0,'dap':1,'z_root':.3,'canopy_cover':.5,'biomass':100,'season_counter':0},
           {'time_step_counter':7,'dap':2,'z_root':.3,'canopy_cover':.5,'biomass':100,'season_counter':0}]
        f=[{'time_step_counter':0,'Es':1,'Tr':2,'EsPot':2,'TrPot':3,'Wr':10,'IrrDay':0,'DeepPerc':0},
           {'time_step_counter':7,'Es':1,'Tr':2,'EsPot':2,'TrPot':3,'Wr':10,'IrrDay':0,'DeepPerc':0}]
        with self.assertRaisesRegex(ScienceError,'AQUACROP_INVALID_SLOT'):
            parse_aquacrop_outputs(growth=g,flux=f,final=[],start_date='1979-10-01',plot_id='p',
              branch_id='b',input_snapshot_id='s',weather_realization_id='w')
    def test_unsupported_crop_blocked(self):
        with self.assertRaisesRegex(ScienceError,'AQUACROP_UNSUPPORTED'):
            parse_aquacrop_outputs(growth=[{}],flux=[{}],final=[],start_date='1979-10-01',plot_id='p',
               branch_id='b',input_snapshot_id='s',weather_realization_id='w',crop_name='Turmeric')
    def test_runtime_missing_is_typed(self):
        import importlib.util
        if importlib.util.find_spec('aquacrop') is None:
            with self.assertRaisesRegex(ScienceError,'DEPENDENCY_UNAVAILABLE'):
                run_published_wheat()
    def test_historical_identical_repeat(self):
        repeat=parse_aquacrop_fixture(FIX,label='repeat',start_date='1979-10-01',
             plot_id='tunis-demo',branch_id='baseline',input_snapshot_id='tunis',weather_realization_id='fixture')
        self.assertEqual(self.original,repeat)

class TestProvenanceFixtures(unittest.TestCase):
    def test_original_archives_present_intact(self):
        archives = sorted((ROOT/'research_evidence').glob('*.zip'))
        self.assertEqual(len(archives),3,"Restore the authorized evidence bundle before running this suite")
        for p in archives:
            with self.subTest(name=p.name):
                with zipfile.ZipFile(p) as z:
                    self.assertIsNone(z.testzip())
    def test_registry(self):
        r=registry()
        self.assertEqual(len(r['models']),2)
        self.assertEqual(r['models'][0]['status'],'conditional-numerical')
        self.assertNotIn('yieldTonnesPerHa',r['models'][0]['supportedOutputs'])

if __name__=='__main__':unittest.main()
