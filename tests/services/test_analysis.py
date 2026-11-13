from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from app.contracts import (
    Availability,
    C1EnvironmentalInput,
    C2FarmDefinition,
    C3ScientificState,
    C5Comparison,
    ComparisonMetric,
    Coordinates,
    DailyWeather,
    DataStatus,
    Measurement,
    PlotDefinition,
)
from app.schemas import FarmCreateRequest, PlotAreaInput, PlotCreateRequest
from app.services.analysis import (
    AnalysisLlmClient,
    AnalysisRequest,
    AnalysisResponseData,
    DeterministicExplainer,
    EvidenceBundle,
    EvidenceBundleBuilder,
    EvidenceGroundedAnalysisService,
    GroundedClaim,
    GuardrailEvaluator,
    QuantitativeClaimValidator,
    StalenessEvaluator,
)
from app.services.analysis.staleness import format_measurement_str, safe_measurement_val
from app.services.crop_lens.registry import CROP_REGISTRY, get_crop_by_id
from app.services.crop_lens.resolver import CropLensResolver
from app.services.environmental import EnvironmentalInputService
from app.services.onboarding import OnboardingService

FIXTURES_DIR = Path(__file__).parents[2] / "packages" / "contracts" / "fixtures"
SAMPLE_C1 = json.loads((FIXTURES_DIR / "c1.json").read_text())
SAMPLE_C2 = json.loads((FIXTURES_DIR / "c2.json").read_text())
SAMPLE_C3 = json.loads((FIXTURES_DIR / "c3.json").read_text())
SAMPLE_C5 = json.loads((FIXTURES_DIR / "c5.json").read_text())

TURMERIC_ID = UUID("00000000-0000-0000-0000-000000000003")


@pytest.fixture
def in_memory_onboarding():
    service = OnboardingService()
    # Reset in-memory dictionaries
    service._in_memory_farms.clear()
    service._in_memory_plots.clear()
    return service


@pytest.fixture
def crop_resolver():
    return CropLensResolver(CROP_REGISTRY)


@pytest.fixture
def environmental_service(crop_resolver):
    return EnvironmentalInputService(crop_resolver=crop_resolver)


@pytest.fixture
async def seeded_farm_and_plot(in_memory_onboarding):
    farm_req = FarmCreateRequest(
        name="Raichur Research Farm",
        timezone="Asia/Kolkata",
        location=Coordinates(latitude=16.2120, longitude=77.3439, crs="EPSG:4326"),
        locationConfirmed=True,
    )
    farm = await in_memory_onboarding.create_farm(farm_req)

    plot_req = PlotCreateRequest(
        areaM2=PlotAreaInput(value=10000.0, unit="m2"),
        cropId=TURMERIC_ID,
        plantingDate=date(2026, 6, 1),
    )
    plot = await in_memory_onboarding.create_plot(farm.farm_id, plot_req)
    return farm, plot


# -----------------------------------------------------------------------------
# 1. Evidence Builder Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evidence_builder_success(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    builder = EvidenceBundleBuilder(
        onboarding_service=in_memory_onboarding,
        crop_resolver=crop_resolver,
        environmental_service=environmental_service,
    )

    req = AnalysisRequest(
        farmId=farm.farm_id,
        plotId=plot.plot_id,
        includeWeather=False,
        includeSoil=False,
    )

    bundle = await builder.build(req)
    assert bundle.farm.farm_id == farm.farm_id
    assert bundle.farm.farm_name == "Raichur Research Farm"
    assert bundle.plot.plot_id == plot.plot_id
    assert bundle.crop_canonical_name == "Turmeric"
    assert bundle.crop_capability.selected_engine == "FAO-56"


@pytest.mark.asyncio
async def test_evidence_builder_unknown_farm(in_memory_onboarding, crop_resolver, environmental_service):
    builder = EvidenceBundleBuilder(
        onboarding_service=in_memory_onboarding,
        crop_resolver=crop_resolver,
        environmental_service=environmental_service,
    )
    req = AnalysisRequest(farmId=uuid4(), plotId=uuid4())
    with pytest.raises(KeyError, match="not found"):
        await builder.build(req)


@pytest.mark.asyncio
async def test_evidence_builder_with_c1_override(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    builder = EvidenceBundleBuilder(
        onboarding_service=in_memory_onboarding,
        crop_resolver=crop_resolver,
        environmental_service=environmental_service,
    )

    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    req = AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id)
    bundle = await builder.build(req, c1_override=c1_model)

    assert bundle.c1_input is not None
    assert bundle.c1_input.contract_version == "1.0"
    assert len(bundle.c1_input.daily_weather) == 1


# -----------------------------------------------------------------------------
# 2. Guardrails & Topic Restriction Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_guardrail_disease_query_escalation(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)
    bundle = await builder.build(AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id, includeWeather=False, includeSoil=False))

    # English query about fungus and leaf rot
    status, _limitations, escalations = GuardrailEvaluator.evaluate("My turmeric leaves have brown leaf spot fungus and rot", bundle)
    assert not status.passed
    assert "plant_pathology" in status.restricted_topics
    assert status.escalation_required
    assert any(e.category == "plant_pathology" for e in escalations)
    assert "KVK" in escalations[0].recommended_authority

    # Hindi query about pest/disease
    status_hi, _, _escalations_hi = GuardrailEvaluator.evaluate("फसल में कीट और फफूंद रोग लग गया है क्या करें", bundle)
    assert not status_hi.passed
    assert "plant_pathology" in status_hi.restricted_topics

    # Kannada query about rot/pest
    status_kn, _, _escalations_kn = GuardrailEvaluator.evaluate("ಬೆಳೆಯಲ್ಲಿ ಕೀಟ ಮತ್ತು ರೋಗ ಬಾಧೆ ಹೆಚ್ಚಾಗಿದೆ", bundle)
    assert not status_kn.passed
    assert "plant_pathology" in status_kn.restricted_topics


@pytest.mark.asyncio
async def test_guardrail_commodity_pricing_refusal(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)
    bundle = await builder.build(AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id, includeWeather=False, includeSoil=False))

    status, _, escalations = GuardrailEvaluator.evaluate("What will be the mandi price per quintal next month?", bundle)
    assert not status.passed
    assert "commodity_pricing" in status.restricted_topics
    assert any(e.category == "commodity_pricing" for e in escalations)
    assert "e-NAM" in escalations[0].recommended_authority


@pytest.mark.asyncio
async def test_guardrail_fao56_yield_limitation(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)
    bundle = await builder.build(AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id, includeWeather=False, includeSoil=False))

    status, limitations, _ = GuardrailEvaluator.evaluate("How many tonnes of yield will I harvest?", bundle)
    assert not status.passed
    assert "yield_forecasting" in status.restricted_topics
    assert any(lim.code == "FAO56_YIELD_UNSUPPORTED" for lim in limitations)


@pytest.mark.asyncio
async def test_guardrail_clean_irrigation_query(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)
    bundle = await builder.build(AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id, includeWeather=False, includeSoil=False))

    status, _, escalations = GuardrailEvaluator.evaluate("How much water do my crops need this week?", bundle)
    assert status.passed
    assert not status.escalation_required
    assert len(escalations) == 0


# -----------------------------------------------------------------------------
# 3. Staleness & Data Quality Tests
# -----------------------------------------------------------------------------
def test_staleness_evaluator_fresh_and_stale_weather():
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)

    # Make c1 retrieved 2 hours ago
    c1_model.retrieved_at = datetime.now(UTC) - timedelta(hours=2)
    bundle = EvidenceBundle(
        farm=farm_model,
        plot=PlotDefinition(
            plotId=uuid4(),
            areaM2=Measurement(value=5000.0, unit="m2", availability=Availability(status=DataStatus.AVAILABLE)),
            sharedResourceIds=[],
        ),
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_model,
    )

    assessments = StalenessEvaluator.evaluate(bundle)
    weather_ass = next(a for a in assessments if a.data_type == "daily_weather_forecast")
    assert not weather_ass.is_stale
    assert "fresh" in weather_ass.freshness_label

    # Make c1 retrieved 30 hours ago (> 24h threshold)
    c1_model.retrieved_at = datetime.now(UTC) - timedelta(hours=30)
    assessments_stale = StalenessEvaluator.evaluate(bundle)
    weather_stale = next(a for a in assessments_stale if a.data_type == "daily_weather_forecast")
    assert weather_stale.is_stale
    assert "stale (> 24h)" in weather_stale.freshness_label
    assert weather_stale.warning is not None


def test_safe_measurement_missingness_preservation():
    # Available measurement returns float value
    avail = Measurement(value=42.5, unit="mm", availability=Availability(status=DataStatus.AVAILABLE))
    assert safe_measurement_val(avail) == 42.5
    assert format_measurement_str(avail) == "42.5 mm"

    # Missing measurement NEVER returns 0
    missing = Measurement(value=None, unit="mm", availability=Availability(status=DataStatus.MISSING))
    assert safe_measurement_val(missing) is None
    assert safe_measurement_val(None) is None
    assert format_measurement_str(missing) == "Not available"


# -----------------------------------------------------------------------------
# 4. Quantitative Claim Validator Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_validator_grounded_vs_hallucinated(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)
    bundle = await builder.build(AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id), c1_override=c1_model)

    # Valid claim matching plot area
    valid_claim = GroundedClaim(
        claimId="c-1",
        metric="plot_area",
        value=10000.0,
        unit="m2",
        sourceField="c2.plot.areaM2",
        sourceId="c2-farm-plot",
        category="observation",
    )
    is_valid, errors = QuantitativeClaimValidator.validate_claims([valid_claim], bundle)
    assert is_valid
    assert len(errors) == 0

    # Hallucinated claim (invented yield number 5432.1 kg)
    fake_claim = GroundedClaim(
        claimId="c-fake",
        metric="yield",
        value=5432.1,
        unit="kg/ha",
        sourceField="hallucination",
        sourceId="unknown",
        category="simulation_state",
    )
    is_valid_fake, errors_fake = QuantitativeClaimValidator.validate_claims([fake_claim], bundle)
    assert not is_valid_fake
    assert len(errors_fake) == 1
    assert "does not exist or is unavailable" in errors_fake[0] or "cannot be grounded" in errors_fake[0]


def test_validator_text_number_check(in_memory_onboarding, crop_resolver, environmental_service):
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)
    bundle = EvidenceBundle(
        farm=farm_model,
        plot=PlotDefinition(
            plotId=uuid4(),
            areaM2=Measurement(value=10000.0, unit="m2", availability=Availability(status=DataStatus.AVAILABLE)),
            sharedResourceIds=[],
        ),
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_model,
    )

    # Grounded text using valid numbers (area 10000.0, year 2026, SoilGrids 250)
    grounded_text = "The plot area is 10000 m2. Year 2026 model with 250m gridded data."
    is_g, unmatched = QuantitativeClaimValidator.validate_text(grounded_text, bundle, [])
    assert is_g
    assert len(unmatched) == 0

    # Text containing hallucinated number 999.85
    hallucinated_text = "Expected harvest is 999.85 tonnes per hectare."
    is_h, unmatched_h = QuantitativeClaimValidator.validate_text(hallucinated_text, bundle, [])
    assert not is_h
    assert "999.85" in unmatched_h


# -----------------------------------------------------------------------------
# 5. Deterministic Multi-Lingual Explainer Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_deterministic_explainer_en_kn_hi(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    c3_model = C3ScientificState.model_validate(SAMPLE_C3)
    c5_model = C5Comparison.model_validate(SAMPLE_C5)

    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)
    bundle = await builder.build(
        AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id),
        c1_override=c1_model,
        c3_states=[c3_model],
        c5_comparison=c5_model,
    )

    staleness = StalenessEvaluator.evaluate(bundle)
    _, limitations, escalations = GuardrailEvaluator.evaluate(None, bundle)

    # 1. English
    sum_en, sec_en, claims_en = DeterministicExplainer.generate(bundle, staleness, limitations, escalations, "en")
    assert "Raichur Research Farm" in sum_en
    assert len(sec_en) >= 5
    assert len(claims_en) > 0
    # Every generated claim MUST pass quantitative validation
    val_en, err_en = QuantitativeClaimValidator.validate_claims(claims_en, bundle)
    assert val_en, f"English claims validation errors: {err_en}"

    # 2. Kannada
    sum_kn, _sec_kn, claims_kn = DeterministicExplainer.generate(bundle, staleness, limitations, escalations, "kn")
    assert "Raichur Research Farm" in sum_kn
    assert "ಬೆಳೆ" in sum_kn or "ಕ್ಷೇತ್ರ" in sum_kn
    val_kn, err_kn = QuantitativeClaimValidator.validate_claims(claims_kn, bundle)
    assert val_kn, f"Kannada claims validation errors: {err_kn}"

    # 3. Hindi
    sum_hi, _sec_hi, claims_hi = DeterministicExplainer.generate(bundle, staleness, limitations, escalations, "hi")
    assert "Raichur Research Farm" in sum_hi
    assert "फसल" in sum_hi or "खेत" in sum_hi
    val_hi, err_hi = QuantitativeClaimValidator.validate_claims(claims_hi, bundle)
    assert val_hi, f"Hindi claims validation errors: {err_hi}"


# -----------------------------------------------------------------------------
# 6. LLM Client Fallback & Post-Validation Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_llm_client_fallback_when_unconfigured(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)
    bundle = await builder.build(AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id), c1_override=c1_model)

    client = AnalysisLlmClient(api_key=None)
    assert not client.is_configured
    res = await client.generate_explanation(bundle, "What is my water balance?")
    assert res is None


@pytest.mark.asyncio
async def test_llm_client_fallback_on_hallucinated_number(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)
    bundle = await builder.build(AnalysisRequest(farmId=farm.farm_id, plotId=plot.plot_id), c1_override=c1_model)

    client = AnalysisLlmClient(api_key="mock-api-key")

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    # Gemini returns a response with a hallucinated number 8877.66
    mock_resp.json = lambda: {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Your farm is doing well. Projected yield is 8877.66 kg."}]
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        res = await client.generate_explanation(bundle, "Will my crop grow well?")
        # Must be rejected because 8877.66 is not in evidence bundle!
        assert res is None


# -----------------------------------------------------------------------------
# 7. End-to-End Analysis Service Orchestration
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_service_orchestration_full_pipeline(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    farm, plot = seeded_farm_and_plot
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    c3_model = C3ScientificState.model_validate(SAMPLE_C3)
    c5_model = C5Comparison.model_validate(SAMPLE_C5)

    service = EvidenceGroundedAnalysisService(
        onboarding_service=in_memory_onboarding,
        crop_resolver=crop_resolver,
        environmental_service=environmental_service,
    )

    req = AnalysisRequest(
        farmId=farm.farm_id,
        plotId=plot.plot_id,
        question="What is the moisture and evapotranspiration status?",
        language="en",
    )

    response_data: AnalysisResponseData = await service.analyze(
        request=req,
        c3_states=[c3_model],
        c5_comparison=c5_model,
        c1_override=c1_model,
    )

    assert response_data.farm_id == farm.farm_id
    assert response_data.plot_id == plot.plot_id
    assert response_data.language == "en"
    assert response_data.generation_mode == "deterministic"
    assert response_data.evidence_summary.c1_available
    assert response_data.evidence_summary.c3_states_count == 1
    assert response_data.evidence_summary.c5_comparison_available
    assert len(response_data.claims) > 0
    assert len(response_data.sections) >= 5
    assert response_data.guardrail_status.passed


# -----------------------------------------------------------------------------
# 8. Post-Audit Regression Tests (Priorities 1 & 2)
# -----------------------------------------------------------------------------
def test_validator_rejects_bare_integers_and_quantities():
    """Verify that bare numbers between 1 and 31 (like 25 bags, 30 rupees, 10 quintals, 25% loss)

    are strictly rejected and not falsely excused as dates.
    """
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    bundle = EvidenceBundle(
        farm=farm_model,
        plot=farm_model.plots[0],
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_model,
    )

    # Hallucinated text with numbers that were previously bypassed by 1..31 check
    unauthorized_text = (
        "You will harvest 28 bags of turmeric and sell each for 99 rupees per bag. "
        "Estimated yield is 10 quintals with 25% loss."
    )
    is_grounded, unmatched = QuantitativeClaimValidator.validate_text(unauthorized_text, bundle, [])
    assert not is_grounded
    assert "28" in unmatched
    assert "99" in unmatched
    assert "10" in unmatched
    assert "25" in unmatched


def test_validator_supports_negative_numbers():
    """Verify signed number extraction: negative values match only negative evidence."""
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)
    c5_model = C5Comparison.model_validate(SAMPLE_C5)
    # Inject a negative difference metric: -12.5 mm
    neg_metric = ComparisonMetric(
        metric="water_difference",
        valueA=Measurement(value=20.0, unit="mm", availability=Availability(status=DataStatus.AVAILABLE)),
        valueB=Measurement(value=7.5, unit="mm", availability=Availability(status=DataStatus.AVAILABLE)),
        difference=Measurement(value=-12.5, unit="mm", availability=Availability(status=DataStatus.AVAILABLE)),
    )
    c5_model.metrics.append(neg_metric)

    bundle = EvidenceBundle(
        farm=farm_model,
        plot=farm_model.plots[0],
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c5Comparison=c5_model,
    )

    # Grounded text with negative value: should pass
    valid_text = "The difference in water balance between scenarios is -12.5 mm."
    is_g, unmatched_g = QuantitativeClaimValidator.validate_text(valid_text, bundle, [])
    assert is_g
    assert len(unmatched_g) == 0

    # Opposite signed value: positive 12.5 should not match negative -12.5
    invalid_text = "The positive difference is 12.5 mm."
    is_inv, unmatched_inv = QuantitativeClaimValidator.validate_text(invalid_text, bundle, [])
    assert not is_inv
    assert "12.5" in unmatched_inv


def test_validator_cross_metric_collision_rejected():
    """Verify that a claim cannot validate against an unrelated field with the same numerical value."""
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    # Latitude is 15.3173, but rainfall is 0.0
    assert math.isclose(farm_model.location.latitude, 15.3173)

    bundle = EvidenceBundle(
        farm=farm_model,
        plot=farm_model.plots[0],
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_model,
    )

    # Claim asserts rainfall is 15.3173 (stealing latitude's number)
    colliding_claim = GroundedClaim(
        claimId="fake-rain-claim",
        metric="rainfall_mm",
        value=15.3173,
        unit="mm",
        sourceField="c1.daily_weather.rainfall_mm.sum",
        sourceId="open-meteo",
        category="gridded_modelled",
    )
    is_valid, errors = QuantitativeClaimValidator.validate_claims([colliding_claim], bundle)
    assert not is_valid
    assert any("does not match the actual value" in err for err in errors)


def test_deterministic_explainer_missing_irrigation_en_kn_hi():
    """Verify that missing irrigation in C3 state is NEVER displayed as 0.0."""
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    c3_model = C3ScientificState.model_validate(SAMPLE_C3)
    # Set irrigation to MISSING
    c3_model.irrigation = Measurement(value=None, unit="mm", availability=Availability(status=DataStatus.MISSING))

    bundle = EvidenceBundle(
        farm=farm_model,
        plot=farm_model.plots[0],
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_model,
        c3States=[c3_model],
    )

    staleness = StalenessEvaluator.evaluate(bundle)
    _, limitations, escalations = GuardrailEvaluator.evaluate(None, bundle)

    # English
    _, sec_en, _ = DeterministicExplainer.generate(bundle, staleness, limitations, escalations, "en")
    c3_sec_en = next(s for s in sec_en if s.key == "crop_water_dynamics")
    assert "Irrigation applied: Not available." in c3_sec_en.content
    assert "Irrigation applied: 0.0 mm" not in c3_sec_en.content

    # Kannada
    _, sec_kn, _ = DeterministicExplainer.generate(bundle, staleness, limitations, escalations, "kn")
    c3_sec_kn = next(s for s in sec_kn if s.key == "crop_water_dynamics")
    assert "ನೀರಾವರಿ: ಲಭ್ಯವಿಲ್ಲ." in c3_sec_kn.content
    assert "ನೀರಾವರಿ: 0.0" not in c3_sec_kn.content

    # Hindi
    _, sec_hi, _ = DeterministicExplainer.generate(bundle, staleness, limitations, escalations, "hi")
    c3_sec_hi = next(s for s in sec_hi if s.key == "crop_water_dynamics")
    assert "सिंचाई: उपलब्ध नहीं." in c3_sec_hi.content
    assert "सिंचाई: 0.0" not in c3_sec_hi.content


def test_deterministic_explainer_rainfall_variations():
    """Verify missing, partial, and genuine zero rainfall reporting."""
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)

    # 1. All-missing rainfall
    for d in c1_model.daily_weather:
        d.rainfall_mm = Measurement(value=None, unit="mm", availability=Availability(status=DataStatus.MISSING))

    bundle_missing = EvidenceBundle(
        farm=farm_model,
        plot=farm_model.plots[0],
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_model,
    )
    staleness = StalenessEvaluator.evaluate(bundle_missing)
    _, lim, esc = GuardrailEvaluator.evaluate(None, bundle_missing)

    _, sec_miss, claims_miss = DeterministicExplainer.generate(bundle_missing, staleness, lim, esc, "en")
    w_sec_miss = next(s for s in sec_miss if s.key == "weather_atmosphere")
    assert "Precipitation: Not available" in w_sec_miss.content
    assert not any(c.metric == "total_rainfall" for c in claims_miss)

    # 2. Genuine zero rainfall
    c1_zero = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    for d in c1_zero.daily_weather:
        d.rainfall_mm = Measurement(value=0.0, unit="mm", availability=Availability(status=DataStatus.AVAILABLE))
    bundle_zero = EvidenceBundle(
        farm=farm_model,
        plot=farm_model.plots[0],
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_zero,
    )
    _, sec_zero, claims_zero = DeterministicExplainer.generate(bundle_zero, staleness, lim, esc, "en")
    w_sec_zero = next(s for s in sec_zero if s.key == "weather_atmosphere")
    assert "Precipitation: 0.0 mm" in w_sec_zero.content
    assert any(c.metric == "total_rainfall" and c.value == 0.0 for c in claims_zero)


def test_deterministic_explainer_ensemble_independent_trajectories():
    """Verify that multiple weather ensemble members are kept independent and not summed into a fabricated total."""
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)

    # Create 2 ensemble members for day 1: member 0 has 10mm, member 1 has 25mm
    day1_m0 = DailyWeather(
        date=date(2026, 6, 1),
        temperatureMinC=Measurement(value=22.0, unit="degC", availability=Availability(status=DataStatus.AVAILABLE)),
        temperatureMaxC=Measurement(value=32.0, unit="degC", availability=Availability(status=DataStatus.AVAILABLE)),
        rainfallMm=Measurement(value=10.0, unit="mm", availability=Availability(status=DataStatus.AVAILABLE)),
        ensembleMemberId="member_0",
    )
    day1_m1 = DailyWeather(
        date=date(2026, 6, 1),
        temperatureMinC=Measurement(value=22.0, unit="degC", availability=Availability(status=DataStatus.AVAILABLE)),
        temperatureMaxC=Measurement(value=32.0, unit="degC", availability=Availability(status=DataStatus.AVAILABLE)),
        rainfallMm=Measurement(value=25.0, unit="mm", availability=Availability(status=DataStatus.AVAILABLE)),
        ensembleMemberId="member_1",
    )
    c1_model.daily_weather = [day1_m0, day1_m1]

    bundle = EvidenceBundle(
        farm=farm_model,
        plot=farm_model.plots[0],
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_model,
    )

    staleness = StalenessEvaluator.evaluate(bundle)
    _, lim, esc = GuardrailEvaluator.evaluate(None, bundle)
    _, sec, claims = DeterministicExplainer.generate(bundle, staleness, lim, esc, "en")

    w_sec = next(s for s in sec if s.key == "weather_atmosphere")
    # Must NOT report 35.0 mm!
    assert "35.0 mm" not in w_sec.content
    assert "range of 10.0 mm to 25.0 mm across 2 ensemble members" in w_sec.content
    # Claims should reflect bounds, not 35 mm
    assert not any(c.value == 35.0 for c in claims)
    assert any(c.metric == "min_ensemble_rainfall" and c.value == 10.0 for c in claims)
    assert any(c.metric == "max_ensemble_rainfall" and c.value == 25.0 for c in claims)


def test_forecast_evidence_classification():
    """Verify that weather forecast claims are categorized as gridded_modelled, not observations."""
    farm_model = C2FarmDefinition.model_validate(SAMPLE_C2)
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)
    bundle = EvidenceBundle(
        farm=farm_model,
        plot=farm_model.plots[0],
        cropCanonicalName="Turmeric",
        cropCapability=get_crop_by_id(TURMERIC_ID).to_c7_capability(),
        c1Input=c1_model,
    )
    staleness = StalenessEvaluator.evaluate(bundle)
    _, lim, esc = GuardrailEvaluator.evaluate(None, bundle)
    _, _sec, claims = DeterministicExplainer.generate(bundle, staleness, lim, esc, "en")

    weather_claims = [c for c in claims if "daily_weather" in c.source_field]
    assert len(weather_claims) > 0
    for wc in weather_claims:
        assert wc.category == "gridded_modelled"
        assert wc.source_id == "open-meteo"


@pytest.mark.asyncio
async def test_llm_not_invoked_on_guardrail_failure(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    """Verify that if guardrails fail (disease or pricing query), the LLM client is never invoked."""
    farm, plot = seeded_farm_and_plot
    c1_model = C1EnvironmentalInput.model_validate(SAMPLE_C1)

    mock_llm_client = AsyncMock()
    # If generate_explanation is called, fail the test immediately
    mock_llm_client.is_configured = True
    mock_llm_client.generate_explanation.side_effect = AssertionError("LLM client should not be invoked when guardrails fail!")

    service = EvidenceGroundedAnalysisService(
        onboarding_service=in_memory_onboarding,
        crop_resolver=crop_resolver,
        environmental_service=environmental_service,
        llm_client=mock_llm_client,
    )

    req = AnalysisRequest(
        farmId=farm.farm_id,
        plotId=plot.plot_id,
        question="My leaves have yellow fungus rot, what pesticide cures it?",
        language="en",
    )

    response_data = await service.analyze(req, c1_override=c1_model)
    # LLM was never called
    mock_llm_client.generate_explanation.assert_not_called()
    assert response_data.generation_mode == "deterministic"
    assert response_data.guardrail_status.passed is False
    assert response_data.guardrail_status.escalation_required is True


@pytest.mark.asyncio
async def test_evidence_builder_c3_simulation_run_retrieval(in_memory_onboarding, crop_resolver, environmental_service, seeded_farm_and_plot):
    """Verify that EvidenceBundleBuilder retrieves C3 states when simulationRunId is present in store."""
    farm, plot = seeded_farm_and_plot
    c3_model = C3ScientificState.model_validate(SAMPLE_C3)
    sim_run_id = uuid4()

    # Seed in-memory simulation store
    EvidenceBundleBuilder._in_memory_simulation_states[sim_run_id] = [c3_model]

    builder = EvidenceBundleBuilder(in_memory_onboarding, crop_resolver, environmental_service)

    # 1. With valid simulationRunId in store
    req_with_run = AnalysisRequest(
        farmId=farm.farm_id,
        plotId=plot.plot_id,
        simulationRunId=sim_run_id,
        includeWeather=False,
        includeSoil=False,
    )
    bundle = await builder.build(req_with_run)
    assert len(bundle.c3_states) == 1
    assert bundle.c3_states[0].contract_version == "1.0"
    assert "c3_simulation_states" not in bundle.missing_evidence

    # 2. With unknown simulationRunId
    req_unknown = AnalysisRequest(
        farmId=farm.farm_id,
        plotId=plot.plot_id,
        simulationRunId=uuid4(),
        includeWeather=False,
        includeSoil=False,
    )
    bundle_unknown = await builder.build(req_unknown)
    assert len(bundle_unknown.c3_states) == 0
    assert "c3_simulation_states" in bundle_unknown.missing_evidence
