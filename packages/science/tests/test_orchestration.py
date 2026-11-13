"""Exercise the science boundary with C's merged environmental service."""
import asyncio
from datetime import date, datetime, timezone
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from test_science import ROOT as SCIENCE_ROOT
from terrapulse_science.contracts import ScienceError, stable_hash
from terrapulse_science.crop_binding import CropBindingService, TURMERIC_ID, WHEAT_ID
from terrapulse_science.fao56 import run_fao
from terrapulse_science.orchestration import ScientificRunService

REPO = SCIENCE_ROOT.parents[1]
FIXTURES = REPO / "packages/contracts/fixtures"


@unittest.skipUnless(os.getenv("TERRAPULSE_TEST_REPOSITORY_CONTRACTS") == "1",
                     "enable with the repository API dependencies")
class TestScientificRunService(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(REPO / "apps/api"))
        from app.contracts import C1EnvironmentalInput, C3ScientificState, C8ResourceLedger
        from app.services.crop_lens import CropLensResolver, get_crop_by_id
        from app.services.environmental import EnvironmentalInputService
        from app.services.soil import SoilResult
        from app.services.weather import WeatherResult

        raw = self.fixture("c1")
        c1 = C1EnvironmentalInput.model_validate(raw)
        self.c3_model, self.c8_model = C3ScientificState, C8ResourceLedger
        self.day = c1.daily_weather[0]
        self.days = [self.day, self.day.model_copy(update={"date":date(2026, 6, 2)})]
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        self.weather = WeatherResult(location=c1.location, timezone=c1.timezone,
            retrieved_at=now, ensemble_members={"member-01":self.days},
            data_source_ids=["weather-fixture"], provenance=c1.provenance)
        self.soil = SoilResult(location=c1.location, profile_depth_cm=30, soil_properties=c1.soil,
            retrieved_at=now, availability=c1.availability, data_source_ids=["soil-fixture"],
            provenance=[c1.provenance[0].model_copy(update={"source_id":"soil-fixture"})])
        self.environment = EnvironmentalInputService(weather_adapter=AsyncMock(), soil_adapter=AsyncMock())
        binding = CropBindingService(resolve=CropLensResolver().resolve, get_crop_by_id=get_crop_by_id)
        self.science = ScientificRunService(crop_binding=binding, c1_model=C1EnvironmentalInput,
                                            c3_model=C3ScientificState)
        self.options = dict(farm_id=c1.farm_id, crop_id=TURMERIC_ID,
            plot_id=UUID("00000000-0000-0000-0000-000000000002"),
            branch_id=UUID("00000000-0000-0000-0000-000000000004"),
            simulation_run_id=UUID("00000000-0000-0000-0000-000000000005"),
            turmeric_mapping="A", area_m2=100, planting_date="2026-06-01",
            root_depth_m=.3, depletion_fraction=.4, initial_depletion_mm=10,
            weather_realization_id="test-forecast", ensemble_member_id="member-01",
            weather_kind="forecast", rainfed=True)

    def fixture(self, name):
        return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))

    def environmental_result(self):
        self.environment.weather_adapter.fetch_weather.return_value = self.weather
        self.environment.soil_adapter.fetch_soil.return_value = self.soil
        return asyncio.run(self.environment.prepare(farm_id=self.options["farm_id"],
            plot_id=self.options["plot_id"], crop_id=TURMERIC_ID, latitude=15.3173, longitude=75.7139,
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2), weather_member_id="member-01",
            soil_target_depth_cm=30, force_refresh=True))

    def execute(self, environmental, **overrides):
        return self.science.execute(snapshot=environmental.c1_input,
            environmental_warnings=environmental.warnings, **(self.options | overrides))

    def assert_failure(self, result, code, stage="input"):
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], code)
        self.assertEqual(result["error"]["stage"], stage)
        self.assertNotIn("states", result)
        self.assertNotIn("scienceEnvelope", result)

    def test_actual_environmental_service_to_rainfed_c3(self):
        environmental = self.environmental_result()
        self.assertTrue(environmental.is_valid, environmental.errors)
        with patch("terrapulse_science.crop_binding.run_fao", wraps=run_fao) as engine:
            result = self.execute(environmental)
        engine.assert_called_once()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result, self.execute(environmental))
        rows = [self.c3_model.model_validate(row) for row in result["states"]]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].simulation_run_id, self.options["simulation_run_id"])
        self.assertEqual(rows[0].engine.name, "FAO-56")
        self.assertAlmostEqual(rows[0].actual_evapotranspiration.value, 1.68)
        self.assertIsNone(rows[0].yield_.value)
        self.assertIsNone(rows[0].runoff.value)
        self.assertEqual({p.source_id for p in rows[0].provenance}, {"weather-fixture", "soil-fixture"})
        envelope = result["scienceEnvelope"]
        self.assertEqual(envelope["cropBinding"]["cropId"], str(TURMERIC_ID))
        self.assertEqual(envelope["cropBinding"]["parameterHash"], envelope["capability"]["parameterHash"])
        self.assertEqual(envelope["weatherMemberId"], "member-01")
        self.assertEqual(len(envelope["inputHash"]), 64)
        self.assertEqual(len(envelope["weatherHash"]), 64)
        self.assertEqual(result["inputProvenance"]["environmentalSnapshotHash"],
                         stable_hash(environmental.c1_input.model_dump(mode="json", by_alias=True)))
        self.assertEqual(result["inputProvenance"]["irrigation"], {"mode":"rainfed"})
        self.assertTrue(set(envelope["warnings"]).issubset(result["warnings"]))

    def test_reconciled_c8_schedule_controls_daily_delivery(self):
        environmental = self.environmental_result()
        ledger = self.fixture("c8")
        ledger["closingVolume"]["value"] = 9000
        ledger = self.c8_model.model_validate(ledger).model_dump(mode="json", by_alias=True)
        schedule = dict(ledgerHash=stable_hash(ledger), resourceId=ledger["resourceId"],
            plotId=str(self.options["plot_id"]), days=[{"date":"2026-06-02","effectiveLitres":900}])
        result = self.execute(environmental, rainfed=False, ledger=ledger, schedule=schedule)
        self.assertEqual(result["status"], "completed")
        self.assertEqual([row["irrigation"]["value"] for row in result["states"]], [0,9])
        self.assertEqual(result["inputProvenance"]["irrigation"]["scheduleHash"], stable_hash(schedule))
        self.assert_failure(self.execute(environmental, rainfed=False, ledger=ledger), "IRRIGATION_SCHEDULE_REQUIRED")
        self.assert_failure(self.execute(environmental, rainfed=False, ledger=ledger,
            schedule=schedule | {"days":[]}), "LEDGER_SCHEDULE_MISMATCH")
        self.assert_failure(self.execute(environmental, ledger=ledger, schedule=schedule),
                            "IRRIGATION_SOURCE_REQUIRED")

    def test_missing_et0_is_rejected_even_when_c_reports_available(self):
        self.days[0].reference_evapotranspiration_mm = None
        environmental = self.environmental_result()
        self.assertTrue(environmental.is_valid, environmental.errors)
        self.assertTrue(environmental.warnings)
        with patch("terrapulse_science.crop_binding.run_fao") as engine:
            self.assert_failure(self.execute(environmental), "MEASUREMENT_UNAVAILABLE")
        engine.assert_not_called()

    def test_weather_and_soil_coverage_and_bad_units(self):
        environmental = self.environmental_result()
        self.assert_failure(self.execute(environmental, ensemble_member_id="member-02"), "WEATHER_COVERAGE")
        self.assert_failure(self.execute(environmental, root_depth_m=.4), "SOIL_DEPTH_COVERAGE")
        environmental.c1_input.daily_weather[0].rainfall_mm.unit = "cm"
        self.assert_failure(self.execute(environmental), "UNIT_MISMATCH")
        self.weather.ensemble_members["member-01"] = self.days[:1]
        environmental = self.environmental_result()
        self.assertFalse(environmental.is_valid)
        self.assert_failure(self.execute(environmental), "MEASUREMENT_UNAVAILABLE")

    def test_trusted_identity_and_explicit_stage_mapping_are_required(self):
        environmental = self.environmental_result()
        cases = (
            ({"crop_id":str(TURMERIC_ID)}, "INVALID_CANONICAL_CROP_ID"),
            ({"crop_id":WHEAT_ID}, "CROP_EXAMPLE_ONLY"),
            ({"crop_id":UUID("00000000-0000-0000-0000-000000000010")}, "UNSUPPORTED_CROP_CAPABILITY"),
            ({"crop_id":UUID("00000000-0000-0000-0000-000000000050")}, "CROP_IDENTITY_ONLY"),
            ({"turmeric_mapping":None}, "CROP_MAPPING_REQUIRED"),
            ({"farm_id":UUID(int=0)}, "SNAPSHOT_FARM_MISMATCH"),
        )
        with patch("terrapulse_science.crop_binding.run_fao") as engine:
            for changes, code in cases:
                with self.subTest(code=code):
                    self.assert_failure(self.execute(environmental, **changes), code)
        engine.assert_not_called()

    def test_engine_and_c3_failures_are_structured(self):
        environmental = self.environmental_result()
        with patch("terrapulse_science.crop_binding.run_fao",
                   side_effect=ScienceError("WATER_BALANCE_ERROR", "balance did not close")):
            self.assert_failure(self.execute(environmental), "WATER_BALANCE_ERROR", "engine")
        with patch("terrapulse_science.orchestration.c3_states_from_run", return_value=[{}]):
            self.assert_failure(self.execute(environmental), "C3_VALIDATION_FAILED", "output")
