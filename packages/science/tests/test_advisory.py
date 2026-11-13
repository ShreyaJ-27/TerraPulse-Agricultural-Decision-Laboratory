from copy import deepcopy
from dataclasses import replace
import json
import os
import sys
import unittest

from test_science import FIX, ROOT, req
from terrapulse_science import (
    ScienceError, compare_advisory_signals, evaluate_advisory_signals,
    parse_aquacrop_fixture, run_fao,
)
from terrapulse_science.repository_contracts import c3_states_from_run

sys.path.insert(0, str(ROOT / "examples"))
from advisory_demo import DECISION_DATE, replay


class TestAdvisory(unittest.TestCase):
    def setUp(self):
        self.request = req(plant="2025-05-02", start="2025-05-01", end="2025-05-05")
        self.envelope = run_fao(self.request)

    def test_day_end_depletion_and_intraday_stress_are_separate(self):
        monitor = evaluate_advisory_signals(self.envelope, date="2025-05-02")
        self.assertEqual([s["decisionCategory"] for s in monitor["signals"]],
                         ["crop-water-demand", "monitor-depletion"])
        self.assertAlmostEqual(monitor["signals"][1]["supportingValues"]["headroomMm"], 0)
        review = evaluate_advisory_signals(self.envelope, date="2025-05-03")
        self.assertEqual(review["metrics"]["waterStressKs"]["value"], 1)
        self.assertEqual([s["metric"] for s in review["signals"]
                          if s["decisionCategory"] == "irrigation-review"], ["rootZoneDepletionMm"])
        later = evaluate_advisory_signals(self.envelope, date="2025-05-04", simulation_run_id="persisted-id")
        stress = next(signal for signal in later["signals"] if signal["metric"] == "waterStressKs")
        self.assertLess(stress["supportingValues"]["ks"], 1)
        self.assertEqual(stress["unit"], "fraction")
        self.assertEqual(stress["identity"]["simulationRunId"], "persisted-id")
        self.assertEqual(stress["identity"]["runId"], self.envelope["runId"])
        self.assertEqual(stress["provenance"]["crop"]["mapping_status"], "provisional")
        self.assertEqual(stress["confidence"]["basis"], "model-derived")

    def test_inactive_missing_and_invalid_metric_handling(self):
        inactive = evaluate_advisory_signals(self.envelope, date="2025-05-01")
        self.assertEqual(inactive["status"], "inactive")
        self.assertEqual(inactive["metrics"]["rootZoneDepletionMm"]["status"], "available")
        self.assertEqual(inactive["metrics"]["waterStressKs"]["status"], "inactive")
        self.assertEqual(inactive["signals"], [])
        self.assertEqual(evaluate_advisory_signals(self.envelope, date="2025-05-06")["status"],
                         "unavailable")
        self.assertEqual(evaluate_advisory_signals(None, date="2025-05-05")["status"], "unavailable")
        changed = deepcopy(self.envelope)
        metrics = changed["states"][-1]["metrics"]
        metrics["waterStressKs"].update(value=None, status="unavailable")
        for name in ("rootZoneDepletionMm", "potentialEtMm"):
            del metrics[name]
        unavailable = evaluate_advisory_signals(changed, date="2025-05-05")
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unavailable["signals"], [])
        metrics["waterStressKs"].update(status="available", value=0.5, unit="mm")
        with self.assertRaisesRegex(ScienceError, "UNIT_MISMATCH"):
            evaluate_advisory_signals(changed, date="2025-05-05")

    def test_zero_ks_is_available_and_unsupported_engine_emits_no_signal(self):
        wilted = run_fao(replace(self.request, planting_date=self.request.start_date,
                                 initial_depletion_mm=self.request.soil.taw_mm))
        result = evaluate_advisory_signals(wilted, date=self.request.start_date)
        self.assertEqual(result["metrics"]["waterStressKs"]["value"], 0)
        stress = next(s for s in result["signals"] if s["metric"] == "waterStressKs")
        self.assertEqual(stress["supportingValues"]["stressIndex"], 1)
        unsupported = evaluate_advisory_signals({"status": "completed", "engine": "other"},
                                                date=self.request.start_date)
        self.assertEqual(unsupported["status"], "unsupported")
        self.assertEqual(unsupported["signals"], [])

    def test_aquacrop_demand_available_without_fao_stress(self):
        run = parse_aquacrop_fixture(FIX, label="planting_11_01", start_date="1979-10-01",
                                     plot_id="plot", branch_id="branch",
                                     input_snapshot_id="tunis", weather_realization_id="tunis")
        result = evaluate_advisory_signals(run, date="1979-11-01")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["metrics"]["waterStressKs"]["status"], "unsupported")
        self.assertEqual(result["metrics"]["rootZoneDepletionMm"]["status"], "unsupported")
        self.assertEqual([s["decisionCategory"] for s in result["signals"]], ["crop-water-demand"])

    def test_comparison_gates_on_shared_weather_and_fork(self):
        other = run_fao(replace(self.request, branch_id="alternative"))
        equal = compare_advisory_signals(self.envelope, other, date="2025-05-05", fork_date="2025-05-02")
        self.assertEqual(equal["status"], "available")
        self.assertEqual(equal["signals"], [])
        pre_fork = compare_advisory_signals(self.envelope, other, date="2025-05-01", fork_date="2025-05-02")
        self.assertEqual(pre_fork["status"], "unavailable")
        inactive = compare_advisory_signals(self.envelope, other, date="2025-05-01", fork_date="2025-05-01")
        self.assertEqual(inactive["status"], "inactive")
        different = run_fao(replace(self.request, branch_id="alternative", weather_realization_id="other"))
        result = compare_advisory_signals(self.envelope, different, date="2025-05-05", fork_date="2025-05-02")
        self.assertEqual(result["status"], "not-comparable")
        self.assertIn("weatherRealizationId differs", result["reasons"])
        self.assertEqual(result["signals"], [])

    def test_c3_stress_direction_and_availability(self):
        demo = replay()
        for branch in demo["branches"].values():
            ks = branch["advisory"]["metrics"]["waterStressKs"]["value"]
            c3 = branch["c3"][-1]["waterStress"]
            self.assertEqual(c3, {"unit": "ratio", "value": 1 - ks,
                                  "availability": {"status": "available"}})
        branch = demo["branches"]["baseline"]
        identity = branch["c3"][0]
        request = replace(self.request, plot_id=identity["plotId"], branch_id=identity["branchId"])
        run = run_fao(request)
        run["states"][1]["metrics"]["waterStressKs"].update(status="unavailable", value=None)
        run["states"][2]["metrics"]["waterStressKs"].update(status="unsupported", value=None)
        rows = c3_states_from_run(run, farm_id=identity["farmId"],
                                  simulation_run_id=identity["simulationRunId"],
                                  provenance=identity["provenance"])
        inactive, unavailable, unsupported = [row["waterStress"] for row in rows[:3]]
        self.assertEqual(inactive["availability"], {"status": "missing",
                                                    "reason": "crop inactive on this date"})
        self.assertEqual(unavailable["availability"]["status"], "missing")
        self.assertNotEqual(unavailable["availability"]["reason"], inactive["availability"]["reason"])
        self.assertEqual(unsupported["availability"]["status"], "unsupported")
        self.assertTrue(all("value" not in metric for metric in (inactive, unavailable, unsupported)))

    def test_replay_is_deterministic_and_conserved(self):
        demo = replay()
        self.assertEqual(json.dumps(demo, allow_nan=False), json.dumps(replay(), allow_nan=False))
        baseline, alternative = (demo["branches"][name] for name in ("baseline", "alternative"))
        self.assertEqual(baseline["c3"][-1]["irrigation"]["value"], 0)
        self.assertTrue(all(row["irrigation"]["value"] == 0 for row in alternative["c3"][:-1]))
        self.assertEqual(alternative["c3"][-1]["irrigation"]["value"], 9)
        for branch in (baseline, alternative):
            self.assertEqual(branch["c3"][-1]["date"], DECISION_DATE)
            balance = branch["waterBalance"]
            self.assertLessEqual(abs(balance["residualMm"]), balance["toleranceMm"])
        comparison = demo["comparison"]
        self.assertEqual(comparison["status"], "available")
        self.assertEqual({s["metric"] for s in comparison["signals"]},
                         {"waterStressKs", "rootZoneDepletionMm"})
        if os.getenv("TERRAPULSE_TEST_REPOSITORY_CONTRACTS") == "1":
            sys.path.insert(0, str(ROOT.parents[1] / "apps/api"))
            from app.contracts import C3ScientificState
            for branch in (baseline, alternative):
                for row in branch["c3"]:
                    C3ScientificState.model_validate(row)
