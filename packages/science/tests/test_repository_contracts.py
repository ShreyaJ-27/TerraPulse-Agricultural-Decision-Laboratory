"""Cross-contract checks against the repository's actual Pydantic models."""
import json
import os
import sys
import unittest
from pathlib import Path

from terrapulse_science import ScienceError, parse_aquacrop_fixture, run_fao, turmeric_profile
from terrapulse_science.contracts import stable_hash
from terrapulse_science.repository_contracts import (
    c3_states_from_run,
    fao_input_from_c1_v1,
    irrigation_from_c8_v1,
)
from test_science import (
    FIX,
    aquacrop_fixture_unavailable_message,
    missing_aquacrop_fixture_files,
)

REPO = Path(__file__).resolve().parents[3]
CONTRACTS = REPO / "packages/contracts/fixtures"


@unittest.skipUnless(os.getenv("TERRAPULSE_TEST_REPOSITORY_CONTRACTS") == "1",
                     "enable in the repository API development environment")
class TestRepositoryContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO / "apps/api"))
        from app.contracts import C1EnvironmentalInput, C3ScientificState, C8ResourceLedger
        cls.c1_model, cls.c3_model, cls.c8_model = C1EnvironmentalInput, C3ScientificState, C8ResourceLedger

    def fixture(self, name):
        return json.loads((CONTRACTS / f"{name}.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.c1 = self.fixture("c1")
        self.c8 = self.fixture("c8")
        # The shared fixture checks shape only. Its 8,900 L closing volume
        # double-counts the 100 L already included in 1,000 L withdrawn.
        self.c8["closingVolume"]["value"] = 9000
        self.c3 = self.fixture("c3")
        self.c1["dailyWeather"].append({**self.c1["dailyWeather"][0], "date":"2026-06-02"})
        self.args = dict(plot_id=self.c3["plotId"], branch_id=self.c3["branchId"],
            area_m2=100, planting_date="2026-06-01", crop=turmeric_profile(),
            root_depth_m=.3, depletion_fraction=.4, initial_depletion_mm=10,
            weather_realization_id="fixture-member-01", ensemble_member_id="member-01",
            weather_kind="assumption")
        self.ledger_args = {key:self.args[key] for key in ("plot_id","branch_id","area_m2")}
        self.ledger_args.update(farm_id=self.c1["farmId"],start_date="2026-06-01",end_date="2026-06-02")

    def schedule(self, ledger):
        return dict(ledgerHash=stable_hash(ledger),resourceId=ledger["resourceId"],
                    plotId=self.args["plot_id"],days=[dict(date="2026-06-02",effectiveLitres=900)])

    def c3_rows(self, run, sources):
        rows = c3_states_from_run(run, farm_id=self.c1["farmId"],
                                  simulation_run_id=self.c3["simulationRunId"], provenance=sources)
        return [self.c3_model.model_validate(row) for row in rows]

    def test_repository_c1_and_c8_run_and_emit_valid_c3(self):
        c1 = self.c1_model.model_validate(self.c1).model_dump(mode="json",by_alias=True)
        c8 = self.c8_model.model_validate(self.c8).model_dump(mode="json",by_alias=True)
        inputs = fao_input_from_c1_v1(c1, ledger=c8, schedule=self.schedule(c8), **self.args)
        self.assertEqual(inputs.request.irrigation_mm_by_date, {"2026-06-02":9})
        self.assertEqual(inputs.request.weather[0].provenance["sources"],inputs.provenance)
        run = run_fao(inputs.request)
        self.assertEqual(run,run_fao(inputs.request))
        rows = self.c3_rows(run,inputs.provenance)
        self.assertEqual(rows[1].irrigation.value,9)
        self.assertAlmostEqual(rows[0].crop_water_demand.value,.4*4.2)
        self.assertAlmostEqual(rows[0].soil_water.value,.28*300-10-.4*4.2)
        self.assertEqual(rows[0].yield_.availability.status,"unsupported")
        self.assertIsNone(rows[0].yield_.value)

    @unittest.skipIf(missing_aquacrop_fixture_files(), aquacrop_fixture_unavailable_message())
    def test_actual_aquacrop_fixture_projects_without_inventing_fluxes(self):
        run = parse_aquacrop_fixture(FIX, label="planting_11_01", start_date="1979-10-01",
            plot_id=self.args["plot_id"], branch_id=self.args["branch_id"],
            input_snapshot_id="tunis", weather_realization_id="verified-tunis")
        sources = [{"sourceId":"aquacrop-ospy","sourceVersion":"3.1.0",
                    "retrievedAt":"2026-11-13T00:00:00Z"}]
        rows = self.c3_rows(run,sources)
        self.assertEqual(len(rows),1213)
        self.assertEqual(rows[0].actual_evapotranspiration.availability.status,"missing")
        active = rows[31]
        self.assertEqual(active.date.isoformat(),"1979-11-01")
        self.assertGreater(active.soil_water.value,0)
        self.assertIsNone(active.rainfall.value)
        self.assertIsNone(active.water_stress.value)
        self.assertIsNone(active.yield_.value)

    def test_c1_rejects_wrong_unit_unavailable_et_and_insufficient_depth(self):
        et = self.c1["dailyWeather"][0]["referenceEvapotranspirationMm"]
        et["unit"] = "cm"
        with self.assertRaisesRegex(ScienceError,"UNIT_MISMATCH"):
            fao_input_from_c1_v1(self.c1,rainfed=True,**self.args)
        et.update(unit="mm",value=None,availability={"status":"missing"})
        with self.assertRaisesRegex(ScienceError,"MEASUREMENT_UNAVAILABLE"):
            fao_input_from_c1_v1(self.c1,rainfed=True,**self.args)
        self.c1["soil"]["depthCm"]["value"] = 10
        with self.assertRaisesRegex(ScienceError,"SOIL_DEPTH_COVERAGE"):
            fao_input_from_c1_v1(self.c1,rainfed=True,**self.args)

    def test_c1_requires_full_member_coverage_and_provenance(self):
        self.c1["dailyWeather"].pop()
        with self.assertRaisesRegex(ScienceError,"WEATHER_COVERAGE"):
            fao_input_from_c1_v1(self.c1,rainfed=True,**self.args)
        self.c1["provenance"] = []
        with self.assertRaisesRegex(ScienceError,"MISSING_PROVENANCE"):
            fao_input_from_c1_v1(self.c1,rainfed=True,**self.args)

    def test_c8_rejects_missing_schedule_mismatch_and_unbalanced_ledger(self):
        with self.assertRaisesRegex(ScienceError,"IRRIGATION_SCHEDULE_REQUIRED"):
            irrigation_from_c8_v1(self.c8,schedule=None,**self.ledger_args)
        schedule = self.schedule(self.c8)
        schedule["days"][0]["effectiveLitres"] = 100
        with self.assertRaisesRegex(ScienceError,"LEDGER_SCHEDULE_MISMATCH"):
            irrigation_from_c8_v1(self.c8,schedule=schedule,**self.ledger_args)
        self.c8["closingVolume"]["value"] = 8900
        with self.assertRaisesRegex(ScienceError,"LEDGER_CONSERVATION"):
            irrigation_from_c8_v1(self.c8,schedule=self.schedule(self.c8),**self.ledger_args)

    def test_authoritative_c8_fixture_is_shape_valid_but_not_conserved(self):
        ledger = self.fixture("c8")
        self.c8_model.model_validate(ledger)
        with self.assertRaisesRegex(ScienceError,"LEDGER_CONSERVATION"):
            irrigation_from_c8_v1(ledger,schedule=self.schedule(ledger),**self.ledger_args)

    def test_c8_rejects_schedule_from_another_snapshot_or_outside_window(self):
        schedule = self.schedule(self.c8)
        schedule["ledgerHash"] = "different"
        with self.assertRaisesRegex(ScienceError,"LEDGER_IDENTITY_MISMATCH"):
            irrigation_from_c8_v1(self.c8,schedule=schedule,**self.ledger_args)
        schedule = self.schedule(self.c8)
        schedule["days"][0]["date"] = "2026-06-03"
        with self.assertRaisesRegex(ScienceError,"LEDGER_WINDOW"):
            irrigation_from_c8_v1(self.c8,schedule=schedule,**self.ledger_args)

    def test_c8_rejects_replayed_deliveries_and_cross_branch_ledger(self):
        schedule = self.schedule(self.c8)
        schedule["days"].append(dict(schedule["days"][0]))
        with self.assertRaisesRegex(ScienceError, "DUPLICATE_ALLOCATION"):
            irrigation_from_c8_v1(self.c8, schedule=schedule, **self.ledger_args)
        fork = self.ledger_args | {"branch_id": "00000000-0000-0000-0000-000000000014"}
        with self.assertRaisesRegex(ScienceError, "LEDGER_IDENTITY_MISMATCH"):
            irrigation_from_c8_v1(self.c8, schedule=self.schedule(self.c8), **fork)
        self.c8["plotAllocations"].append(dict(self.c8["plotAllocations"][0]))
        with self.assertRaisesRegex(ScienceError, "DUPLICATE_ALLOCATION"):
            irrigation_from_c8_v1(self.c8, schedule=self.schedule(self.c8), **self.ledger_args)

    def test_c8_rejects_small_overdraws_and_unallocated_delivery(self):
        self.c8["plotAllocations"][0]["requestedAmount"]["value"] = 1000 - 1e-7
        with self.assertRaisesRegex(ScienceError, "LEDGER_CONSERVATION"):
            irrigation_from_c8_v1(self.c8, schedule=self.schedule(self.c8), **self.ledger_args)
        self.c8["plotAllocations"][0]["requestedAmount"]["value"] = 1000
        self.c8["plotAllocations"][0]["plotId"] = "00000000-0000-0000-0000-000000000020"
        schedule = self.schedule(self.c8)
        schedule["days"][0]["effectiveLitres"] = 1e-7
        with self.assertRaisesRegex(ScienceError, "LEDGER_SCHEDULE_MISMATCH"):
            irrigation_from_c8_v1(self.c8, schedule=schedule, **self.ledger_args)
