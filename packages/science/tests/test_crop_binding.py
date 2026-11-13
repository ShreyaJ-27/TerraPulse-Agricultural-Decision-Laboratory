"""Verify the Developer A gate against the merged Crop Lens and C7 contract."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import unittest

from test_science import req
from terrapulse_science import ScienceError
from terrapulse_science.crop_binding import CropBindingService, TURMERIC_ID, WHEAT_ID

REPO = Path(__file__).resolve().parents[3]


@unittest.skipUnless(os.getenv("TERRAPULSE_TEST_REPOSITORY_CONTRACTS") == "1",
                     "enable in the repository API development environment")
class TestCropBinding(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(REPO / "apps/api"))
        from app.contracts import C1EnvironmentalInput, C7ModelCapability
        from app.services.crop_lens.registry import CROP_REGISTRY, get_crop_by_id
        from app.services.crop_lens.resolver import CropLensResolver
        self.catalogue = CROP_REGISTRY
        self.lookup, self.resolver_type = get_crop_by_id, CropLensResolver
        self.resolver = CropLensResolver()
        self.service = CropBindingService(resolve=self.resolver.resolve, get_crop_by_id=self.lookup)
        self.c7_model = C7ModelCapability
        fixture = REPO / "packages/contracts/fixtures/c1.json"
        raw = json.loads(fixture.read_text(encoding="utf-8"))
        raw["dailyWeather"].append({**raw["dailyWeather"][0], "date":"2026-06-02"})
        self.c1 = C1EnvironmentalInput.model_validate(raw).model_dump(mode="json",by_alias=True)
        self.context = dict(query="haldi", turmeric_mapping="A",
            plot_id="00000000-0000-0000-0000-000000000002",
            branch_id="00000000-0000-0000-0000-000000000004", area_m2=100,
            planting_date="2026-06-01", root_depth_m=.3, depletion_fraction=.4,
            initial_depletion_mm=10, weather_realization_id="test-member-01",
            ensemble_member_id="member-01", weather_kind="assumption", rainfed=True)

    def test_turmeric_replaces_catalogue_placeholder_with_a_profile(self):
        c7 = self.c7_model.model_validate(self.resolver.resolve("haldi").capability)
        self.assertEqual(c7.parameter_versions, ["demo-1"])
        binding, prepared = self.service.prepare_fao(self.c1, **self.context)
        self.assertEqual(binding.crop_id,TURMERIC_ID)
        self.assertEqual(prepared.request.crop,binding.profile)
        self.assertIn("Pereira2024",binding.profile.parameter_version)
        self.assertEqual(binding.profile.mapping_status,"provisional")
        self.assertEqual(binding.profile.kc_mid,1.05)
        run = self.service.run_fao(self.c1, **self.context)
        self.assertEqual(run["cropBinding"]["cropId"],str(TURMERIC_ID))
        self.assertEqual(run["cropBinding"]["parameterVersion"],binding.profile.parameter_version)
        self.assertEqual(run["cropBinding"]["parameterHash"],run["capability"]["parameterHash"])
        self.assertNotIn("demo-1",json.dumps(run))
        self.assertEqual(run["states"][0]["metrics"]["yieldTonnesPerHa"]["status"],"unsupported")

    def test_explicit_mapping_selection_and_unregistered_mapping(self):
        with self.assertRaisesRegex(ScienceError,"CROP_MAPPING_REQUIRED"):
            self.service.prepare_fao(None,query="turmeric")
        binding = self.service.bind_fao("turmeric", turmeric_mapping="B")
        self.assertTrue(binding.profile.parameter_version.endswith("-B"))
        with self.assertRaisesRegex(ScienceError,"UNSUPPORTED_MAPPING"):
            self.service.bind_fao("turmeric", turmeric_mapping="demo-1")

    def test_wheat_catalogue_exposes_only_the_pinned_aquacrop_example(self):
        capability = self.resolver.resolve("gehun").capability
        self.assertEqual(capability.selected_engine, "AquaCrop")
        self.assertEqual(capability.parameter_versions, ["Tunis-Wheat-example-3.1.0"])
        self.assertEqual(capability.supported_outputs, [])
        with self.assertRaisesRegex(ScienceError,"CROP_EXAMPLE_ONLY"):
            self.service.prepare_fao(None,query="wheat")

    def test_maize_millets_and_chickpea_declarations_do_not_enable_models(self):
        for query in ("maize","pearl millet","finger millet","chana"):
            with self.subTest(query=query), self.assertRaisesRegex(ScienceError,"UNSUPPORTED_CROP_CAPABILITY"):
                self.service.bind_fao(query)

    def test_identity_only_and_unknown_fail_before_c1_processing(self):
        for query, code in (("cotton","CROP_IDENTITY_ONLY"),("off catalogue crop","CROP_IDENTITY_UNRESOLVED")):
            with self.subTest(query=query), self.assertRaisesRegex(ScienceError,code):
                self.service.prepare_fao(None,query=query)

    def test_real_ambiguous_resolution_requires_matching_candidate(self):
        result = self.resolver.resolve("millet")
        self.assertEqual(result.status,"ambiguous")
        with self.assertRaisesRegex(ScienceError,"CROP_CONFIRMATION_REQUIRED"):
            self.service.bind_fao("millet")
        with self.assertRaisesRegex(ScienceError,"INVALID_CROP_CONFIRMATION"):
            self.service.bind_fao("millet",confirmed_crop_id=str(TURMERIC_ID))
        confirmed = next(row.crop_id for row in result.candidates if row.canonical_name=="Foxtail Millet")
        with self.assertRaisesRegex(ScienceError,"CROP_IDENTITY_ONLY"):
            self.service.bind_fao("millet",confirmed_crop_id=str(confirmed))

    def test_confirmation_can_select_supported_candidate(self):
        # Exercise C's actual alias resolution with a simulated alias collision.
        records = [replace(self.lookup(uid),aliases=["test alias"]) for uid in (TURMERIC_ID,WHEAT_ID)]
        resolver = self.resolver_type(records)
        service = CropBindingService(resolve=resolver.resolve,get_crop_by_id=self.lookup)
        self.assertEqual(resolver.resolve("test alias").status,"ambiguous")
        binding = service.bind_fao("test alias",confirmed_crop_id=str(TURMERIC_ID),turmeric_mapping="A")
        self.assertEqual(binding.crop_id,TURMERIC_ID)

    def test_no_client_c7_or_crop_parameters_allowed(self):
        forged = self.resolver.resolve("haldi").capability.model_dump(mode="json",by_alias=True)
        forged["parameterVersions"] = ["client-version"]
        for extra in ({"capability":forged},{"crop":req().crop}):
            with self.subTest(fields=list(extra)), self.assertRaisesRegex(ScienceError,"CLIENT_SCIENCE_PROFILE"):
                self.service.prepare_fao(self.c1,**self.context,**extra)
        with self.assertRaisesRegex(ScienceError,"INVALID_CROP_CONFIRMATION"):
            self.service.bind_fao("haldi",confirmed_crop_id=str(WHEAT_ID))
