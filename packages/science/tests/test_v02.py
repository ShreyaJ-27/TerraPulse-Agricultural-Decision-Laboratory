"""Developer A scientific regression and rejection tests."""
import json
import subprocess
import sys
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from terrapulse_science import (
    CapabilityRegistry,
    ScienceError,
    compare_aquacrop_runs,
    compare_runs,
    dry_bean_reference_profile,
    fao_day,
    from_c1_with_root_depth,
    kc_at_day,
    parse_aquacrop_fixture,
    parse_aquacrop_outputs,
    request_from_dict,
    run_fao,
    run_published_wheat,
)
from terrapulse_science.aquacrop_adapter import UPSTREAM_UNITS, audit_water_balance, read_csv
from terrapulse_science.aquacrop_reference import REFERENCE_SOIL_PROFILE
from terrapulse_science.capability import WEATHER_SHA256
from terrapulse_science.validation import validate_metrics
from test_science import (
    FIX,
    SRC,
    aquacrop_fixture_unavailable_message,
    missing_aquacrop_fixture_files,
    req,
)


class TestMalformedInputs(unittest.TestCase):
    def test_c1_rejects_non_object_layers(self):
        layer = dict(fromCm=0, toCm=30, fieldCapacityM3M3=.3,
                     wiltingPointM3M3=.15, provenance=SRC)
        for invalid in (None, [], "layer"):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ScienceError, "INVALID_SOIL"):
                self.c1_request([layer, invalid])

    def test_c1_rejects_bad_depth_before_sorting(self):
        for invalid in (None, "30", True):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ScienceError, "INVALID_NUMBER"):
                self.c1_request([{"fromCm":0}, {"fromCm":invalid}])

    def c1_request(self, layers):
        request = req()
        return from_c1_with_root_depth(c1={"soilLayers":layers,"weather":[]},
            plot_id=request.plot_id, branch_id=request.branch_id, area_m2=request.area_m2,
            planting_date=request.planting_date, start_date=request.start_date,
            end_date=request.end_date, crop=request.crop, root_depth_m=.3, depletion_fraction=.4,
            initial_depletion_mm=15, input_snapshot_id="snapshot", weather_realization_id="weather",
            ensemble_member_id="m1", explicit_irrigation_mm={})

    def test_metric_container_rejects_non_objects(self):
        for invalid in (None, [], 1):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ScienceError, "INVALID_METRICS"):
                validate_metrics(invalid)

    def test_null_metric_rejected_at_comparison_boundary(self):
        a, b = run_fao(req()), run_fao(req(branch="b"))
        b["states"][0]["metrics"]["drainageMm"] = None
        with self.assertRaisesRegex(ScienceError, "INVALID_METRIC"):
            compare_runs(a,b)

    def test_metric_rejects_invalid_status_and_missing_value(self):
        for metric, code in (
            ({"status":[],"unit":"m","value":None}, "INVALID_METRIC_STATUS"),
            ({"status":"unavailable","unit":"m"}, "INVALID_METRIC"),
        ):
            with self.subTest(metric=metric), self.assertRaisesRegex(ScienceError, code):
                validate_metrics({"groundwaterDepthM":metric})

    def test_unavailable_metric_preserves_explicit_null(self):
        validate_metrics({"groundwaterDepthM":{"status":"unavailable","unit":"m","value":None}})


def aqua_args(branch="a"):
    return dict(start_date="1979-10-01", plot_id="tunis", branch_id=branch,
                input_snapshot_id="tunis-reference", weather_realization_id="tunis")


def table(kind, label="baseline"):
    return read_csv(FIX / f"{label}_{kind}.csv")


class TestCapabilitiesV02(unittest.TestCase):
    def test_unregistered_crop_rejected(self):
        request = req()
        with self.assertRaisesRegex(ScienceError, "UNSUPPORTED_CROP_CAPABILITY"):
            run_fao(replace(request, crop=replace(request.crop, scientific_name="Unregistered")))

    def test_registered_parameter_values_cannot_drift(self):
        request = req()
        with self.assertRaisesRegex(ScienceError, "PARAMETER_MISMATCH"):
            run_fao(replace(request, crop=replace(request.crop, kc_mid=0.99)))

    def test_missing_crop_and_provenance(self):
        with self.assertRaisesRegex(ScienceError, "MISSING_PARAMETERS"):
            run_fao(replace(req(), crop=None))
        with self.assertRaisesRegex(ScienceError, "MISSING_PROVENANCE"):
            CapabilityRegistry().register_fao_profile(dry_bean_reference_profile(),
                capability_id="example", references=[])

    def test_claimed_calibration_requires_evidence(self):
        profile = replace(dry_bean_reference_profile(), mapping_status="calibrated")
        with self.assertRaisesRegex(ScienceError, "UNCERTIFIED_CALIBRATION"):
            CapabilityRegistry().register_fao_profile(profile, capability_id="example", references=["FAO"])

    def test_example28_reference_checkpoints_and_opt_in(self):
        profile = dry_bean_reference_profile()
        expected = {20:0.15, 40:0.774, 70:1.19, 95:0.56}
        for day, value in expected.items():
            self.assertAlmostEqual(kc_at_day(day, profile.stage_lengths_days,
                (profile.kc_initial, profile.kc_mid, profile.kc_end))[0], value, places=12)
        request = replace(req(), crop=profile)
        with self.assertRaisesRegex(ScienceError, "UNSUPPORTED_CROP_CAPABILITY"):
            run_fao(request)
        result = run_fao(request, capabilities=CapabilityRegistry(include_reference_profiles=True))
        self.assertEqual(result["summary"]["activeCropDays"], 100)
        self.assertEqual(result["capability"]["validationStatus"], "numerical-only-not-field-calibrated")

    def test_unsupported_metric_rejected_by_both_engines(self):
        with self.assertRaisesRegex(ScienceError, "UNSUPPORTED_OUTPUT"):
            run_fao(req(), requested_outputs=["yieldTonnesPerHa"])
        with self.assertRaisesRegex(ScienceError, "UNSUPPORTED_OUTPUT"):
            run_published_wheat(requested_outputs=["rootZoneDepletionMm"])

    def test_unsupported_aquacrop_planting(self):
        with self.assertRaisesRegex(ScienceError, "AQUACROP_UNSUPPORTED"):
            run_published_wheat(planting_mmdd="12/01")


class TestFaoV02(unittest.TestCase):
    def test_shipped_examples_replay_and_compare(self):
        examples = Path(__file__).resolve().parents[1] / "examples"
        required = [examples / f"fao_{name}.json" for name in ("baseline", "delayed", "irrigated")]
        if any(not path.is_file() for path in required):
            subprocess.run(
                [sys.executable, str(examples / "make_fixtures.py")],
                check=True,
            )
        a, delayed, irrigated = [
            run_fao(request_from_dict(json.loads((examples/f"fao_{name}.json").read_text(encoding="utf-8"))))
            for name in ("baseline","delayed","irrigated")]
        self.assertEqual(compare_runs(a,delayed,fork_date="2025-05-01")["status"],"comparable")
        self.assertEqual(compare_runs(a,irrigated)["status"],"comparable")
        self.assertEqual(irrigated["summary"]["effectiveIrrigationMm"],10)

    def test_missing_soil_and_invalid_irrigation(self):
        with self.assertRaisesRegex(ScienceError, "MISSING_PARAMETERS"):
            run_fao(replace(req(), soil=None))
        with self.assertRaisesRegex(ScienceError, "INVALID_IRRIGATION"):
            run_fao(replace(req(), irrigation_mm_by_date=None))

    def test_full_window_balance_replay_and_irrigation_difference(self):
        a = run_fao(req())
        request = req(branch="b", irrig={"2025-06-01":12})
        b = run_fao(request)
        self.assertEqual(b, run_fao(request))
        self.assertEqual(compare_runs(a,b)["status"], "comparable")
        self.assertGreater(b["summary"]["activeActualEtMm"], a["summary"]["activeActualEtMm"])
        ledger = b["waterBalance"]
        self.assertAlmostEqual(ledger["residualMm"], 0, places=9)
        self.assertEqual(ledger["totals"]["irrigationMm"], 12)
        self.assertGreater(ledger["totals"]["actualEtMm"], b["summary"]["activeActualEtMm"])

    def test_weather_label_cannot_mask_content_change(self):
        a = run_fao(req())
        b = run_fao(req(branch="b", rainfall=1))
        result = compare_runs(a,b)
        self.assertIn("weatherHash differs", result["reasons"])
        self.assertFalse(result["matchedWeatherRealization"])

    def test_irrigation_before_fork_rejected(self):
        a = run_fao(req())
        b = run_fao(req(branch="b", irrig={"2025-05-02":1}))
        self.assertIn("effective irrigation differs before forkDate",
                      compare_runs(a,b,fork_date="2025-05-03")["reasons"])

    def test_overflow_rejected(self):
        with self.assertRaisesRegex(ScienceError, "INVALID_NUMBER"):
            fao_day(req().soil, 0, et0=1e308, kc=10)

    def test_comparison_rejects_changed_units(self):
        a, b = run_fao(req()), run_fao(req(branch="b"))
        b["states"][-1]["metrics"]["drainageMm"]["unit"] = "cm/day"
        with self.assertRaisesRegex(ScienceError, "UNIT_MISMATCH"):
            compare_runs(a,b)


@unittest.skipIf(missing_aquacrop_fixture_files(), aquacrop_fixture_unavailable_message())
class TestAquaV02(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.october = parse_aquacrop_fixture(FIX, **aqua_args())
        cls.november = parse_aquacrop_fixture(FIX, label="planting_11_01", **aqua_args("b"))

    def test_harvest_uses_end_of_interval(self):
        self.assertEqual(self.october["harvests"][0]["harvestDate"], "1980-04-15")
        row = next(s for s in self.october["states"] if s["date"] == "1980-04-14")
        self.assertEqual(row["dap"], 197)
        self.assertFalse(any(s["date"] == "1980-04-15" for s in self.october["states"]))

    def test_executed_preplant_and_resets(self):
        row = self.november["states"][0]
        self.assertEqual(row["status"], "inactive")
        self.assertIsNone(row["metrics"]["actualEtMm"]["value"])
        self.assertGreater(row["metrics"]["fallowEtMm"]["value"], 0)
        for run, days in ((self.october,1182),(self.november,1213)):
            audit = run["waterBalance"]
            self.assertEqual(audit["auditedDays"], days)
            self.assertEqual(len(audit["plantingResets"]), 6)
            self.assertLess(audit["maxAbsResidualMm"], 1e-9)
            self.assertIsNone(audit["plantingResets"][1]["changeFromPreviousDayMm"])
        self.assertAlmostEqual(self.november["waterBalance"]["plantingResets"][0]["changeFromPreviousDayMm"],
                               -3.87065500152, places=8)

    def test_storage_tamper_detected_by_conservation(self):
        g,f,w = table("crop_growth"),table("water_flux"),table("water_storage")
        w[0]["th1"] = "0.20"
        with self.assertRaisesRegex(ScienceError, "AQUACROP_CONSERVATION"):
            audit_water_balance(g,f,w,REFERENCE_SOIL_PROFILE)

    def test_skipped_storage_cannot_contain_observation(self):
        g,f,w = table("crop_growth"),table("water_flux"),table("water_storage")
        w[197]["th1"] = "0.20"
        with self.assertRaisesRegex(ScienceError, "AQUACROP_INVALID_SLOT"):
            audit_water_balance(g,f,w,REFERENCE_SOIL_PROFILE)

    def test_missing_flux_cannot_close_balance(self):
        g,f,w = table("crop_growth"),table("water_flux"),table("water_storage")
        del f[0]["Infl"]
        with self.assertRaisesRegex(ScienceError, "AQUACROP_COLUMN_MISSING"):
            audit_water_balance(g,f,w,REFERENCE_SOIL_PROFILE)

    def test_unsupported_boundary_flux(self):
        g,f,w = table("crop_growth"),table("water_flux"),table("water_storage")
        f[0]["GwIn"] = "1"
        with self.assertRaisesRegex(ScienceError, "AQUACROP_BALANCE_UNSUPPORTED"):
            audit_water_balance(g,f,w,REFERENCE_SOIL_PROFILE)

    def test_weather_and_execution_provenance_required_for_comparison(self):
        self.assertEqual(self.october["weatherHash"], WEATHER_SHA256)
        bad = deepcopy(self.november)
        bad["weatherHash"] = None
        self.assertEqual(compare_aquacrop_runs(self.october,bad,fork_date="1979-09-30")["status"],
                         "not-comparable")
        with self.assertRaisesRegex(ScienceError, "INVALID_PROVENANCE"):
            parse_aquacrop_outputs(evidence_kind="executed-aquacrop")

    def test_invalid_harvest_step_rejected(self):
        final = table("final_results")
        final[0]["Harvest Date (Step)"] = "197"
        with self.assertRaisesRegex(ScienceError, "AQUACROP_INVALID_HARVEST"):
            parse_aquacrop_outputs(growth=table("crop_growth"),flux=table("water_flux"),
                                  final=final,**aqua_args())

class TestAquaCropAdapterValidation(unittest.TestCase):
    def test_tampered_csv_rejected_before_parsing(self):
        with (
            patch.object(Path, "read_bytes", return_value=b"replacement"),
            self.assertRaisesRegex(ScienceError, "AQUACROP_FIXTURE_HASH_MISMATCH"),
        ):
            parse_aquacrop_fixture(FIX, **aqua_args())

    def test_input_unit_conflict(self):
        with self.assertRaisesRegex(ScienceError, "UNIT_MISMATCH"):
            parse_aquacrop_outputs(growth=[],flux=[],final=[],**aqua_args(),
                                  source_units={**UPSTREAM_UNITS,"biomass":"kg/m2"})
