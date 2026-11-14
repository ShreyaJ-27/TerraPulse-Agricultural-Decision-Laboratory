from datetime import date
from uuid import uuid4

from app.contracts import C2FarmDefinition
from app.main import app
from app.routers.farms import get_onboarding_service
from app.schemas import FarmResponse
from app.services.onboarding import OnboardingService
from fastapi.testclient import TestClient

in_memory_service = OnboardingService()
app.dependency_overrides[get_onboarding_service] = lambda: in_memory_service
client = TestClient(app)


def test_confirm_plot_planting_date_preserves_other_management():
    farm = client.post("/api/v1/farms", json=_valid_farm_payload()).json()["data"]
    plots_url = f"/api/v1/farms/{farm['farmId']}/plots"
    plot = client.post(plots_url, json={
        "cropQuery": "maize", "areaM2": {"value": 1000},
        "management": {"plotName": "Existing name", "regionId": "test", "plantingDateCertainty": "unconfirmed"},
    }).json()["data"]
    plot_url = f"{plots_url}/{plot['plotId']}"
    assert client.patch(f"{plot_url}/planting-date", json={
        "plantingDate": date.max.isoformat(),
    }).status_code == 422
    saved = client.patch(f"{plot_url}/planting-date", json={"plantingDate": "2026-01-01"})
    assert saved.status_code == 200
    reread = client.get(plot_url).json()["data"]
    assert reread["plantingDate"] == "2026-01-01"
    assert reread["management"] == {
        "plotName": "Existing name", "regionId": "test", "plantingDateCertainty": "confirmed",
    }
    assert reread["cropId"] == plot["cropId"]


def _valid_farm_payload():
    return {
        "name": "Karnataka Research Station",
        "timezone": "Asia/Kolkata",
        "location": {
            "latitude": 15.3173,
            "longitude": 75.7139,
            "crs": "EPSG:4326",
        },
        "locationConfirmed": True,
    }


def test_create_farm_success():
    response = client.post("/api/v1/farms", json=_valid_farm_payload())
    assert response.status_code == 201
    payload = response.json()
    assert payload["contractVersion"] == "1.0"
    data = payload["data"]
    assert "farmId" in data
    assert data["name"] == "Karnataka Research Station"
    assert data["location"]["latitude"] == 15.3173
    assert data["location"]["longitude"] == 75.7139
    assert data["plots"] == []


def test_create_farm_invalid_coordinates():
    # Latitude > 90
    bad_lat = _valid_farm_payload()
    bad_lat["location"]["latitude"] = 91.5
    res = client.post("/api/v1/farms", json=bad_lat)
    assert res.status_code == 422
    assert "VALIDATION_ERROR" in res.json()["error"]["code"]

    # Longitude < -180
    bad_lon = _valid_farm_payload()
    bad_lon["location"]["longitude"] = -185.0
    res = client.post("/api/v1/farms", json=bad_lon)
    assert res.status_code == 422


def test_create_farm_unconfirmed_location_rejected():
    unconfirmed = _valid_farm_payload()
    unconfirmed["locationConfirmed"] = False
    res = client.post("/api/v1/farms", json=unconfirmed)
    assert res.status_code == 422
    err_msg = str(res.json()["error"])
    assert "confirmed" in err_msg.lower()


def test_get_farm_by_id():
    create_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = create_res.json()["data"]["farmId"]

    get_res = client.get(f"/api/v1/farms/{farm_id}")
    assert get_res.status_code == 200
    data = get_res.json()["data"]
    assert data["farmId"] == farm_id
    assert data["name"] == "Karnataka Research Station"


def test_get_farm_not_found():
    non_existent = str(uuid4())
    res = client.get(f"/api/v1/farms/{non_existent}")
    assert res.status_code == 404


def test_list_farms():
    res = client.get("/api/v1/farms")
    assert res.status_code == 200
    assert "farms" in res.json()["data"]
    assert res.json()["data"]["total"] >= 1


def test_create_plot_with_crop_alias_resolution():
    farm_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = farm_res.json()["data"]["farmId"]

    plot_payload = {
        "areaM2": {"value": 1500.0, "unit": "m2"},
        "cropQuery": "haldi",  # Vernacular alias for Turmeric
        "plantingDate": "2026-06-01",
    }
    plot_res = client.post(f"/api/v1/farms/{farm_id}/plots", json=plot_payload)
    assert plot_res.status_code == 201
    plot_data = plot_res.json()["data"]
    assert plot_data["farmId"] == farm_id
    assert plot_data["cropId"] == "00000000-0000-0000-0000-000000000003"
    assert plot_data["cropCanonicalName"] == "Turmeric"
    assert plot_data["cropScientificName"] == "Curcuma longa"
    assert plot_data["areaM2"]["value"] == 1500.0
    assert plot_data["areaM2"]["unit"] == "m2"
    assert plot_data["areaM2"]["availability"]["status"] == "available"


def test_create_plot_with_direct_crop_id():
    farm_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = farm_res.json()["data"]["farmId"]

    maize_id = "00000000-0000-0000-0000-000000000010"
    plot_payload = {
        "areaM2": {"value": 2500.0, "unit": "m2"},
        "cropId": maize_id,
        "plantingDate": "2026-06-15",
    }
    plot_res = client.post(f"/api/v1/farms/{farm_id}/plots", json=plot_payload)
    assert plot_res.status_code == 201
    plot_data = plot_res.json()["data"]
    assert plot_data["cropId"] == maize_id
    assert plot_data["cropCanonicalName"] == "Maize"


def test_create_plot_ambiguous_crop_requires_confirmation():
    farm_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = farm_res.json()["data"]["farmId"]

    # "millet" matches multiple crops
    plot_payload = {
        "areaM2": {"value": 1000.0, "unit": "m2"},
        "cropQuery": "millet",
    }
    plot_res = client.post(f"/api/v1/farms/{farm_id}/plots", json=plot_payload)
    assert plot_res.status_code == 422
    err = plot_res.json()["error"]
    assert err["code"] == "AMBIGUOUS_CROP_IDENTITY"
    assert "cropQuery" in err["fields"]
    assert len(err["fields"]["cropQuery"]) >= 2


def test_create_plot_unresolvable_crop_rejected():
    farm_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = farm_res.json()["data"]["farmId"]

    plot_payload = {
        "areaM2": {"value": 1000.0, "unit": "m2"},
        "cropQuery": "non_existent_crop_xyz",
    }
    plot_res = client.post(f"/api/v1/farms/{farm_id}/plots", json=plot_payload)
    assert plot_res.status_code == 422
    assert "VALIDATION_ERROR" in plot_res.json()["error"]["code"]


def test_create_plot_invalid_area_value():
    farm_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = farm_res.json()["data"]["farmId"]

    # Zero area
    res_zero = client.post(
        f"/api/v1/farms/{farm_id}/plots",
        json={"areaM2": {"value": 0, "unit": "m2"}, "cropQuery": "haldi"},
    )
    assert res_zero.status_code == 422

    # Negative area
    res_neg = client.post(
        f"/api/v1/farms/{farm_id}/plots",
        json={"areaM2": {"value": -500, "unit": "m2"}, "cropQuery": "haldi"},
    )
    assert res_neg.status_code == 422

    # Invalid unit (not m2)
    res_unit = client.post(
        f"/api/v1/farms/{farm_id}/plots",
        json={"areaM2": {"value": 100, "unit": "hectares"}, "cropQuery": "haldi"},
    )
    assert res_unit.status_code == 422


def test_create_plot_non_existent_farm():
    non_existent = str(uuid4())
    res = client.post(
        f"/api/v1/farms/{non_existent}/plots",
        json={"areaM2": {"value": 1000, "unit": "m2"}, "cropQuery": "haldi"},
    )
    assert res.status_code == 404


def test_list_and_get_plots_under_farm():
    farm_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = farm_res.json()["data"]["farmId"]

    # Add plot 1
    p1 = client.post(
        f"/api/v1/farms/{farm_id}/plots",
        json={"areaM2": {"value": 800, "unit": "m2"}, "cropQuery": "haldi"},
    ).json()["data"]

    # Add plot 2
    p2 = client.post(
        f"/api/v1/farms/{farm_id}/plots",
        json={"areaM2": {"value": 1200, "unit": "m2"}, "cropQuery": "gehun"},
    ).json()["data"]

    # List plots
    list_res = client.get(f"/api/v1/farms/{farm_id}/plots")
    assert list_res.status_code == 200
    plots = list_res.json()["data"]["plots"]
    assert len(plots) == 2

    # Get individual plot
    p1_get = client.get(f"/api/v1/farms/{farm_id}/plots/{p1['plotId']}")
    assert p1_get.status_code == 200
    assert p1_get.json()["data"]["plotId"] == p1["plotId"]
    assert p1_get.json()["data"]["cropCanonicalName"] == "Turmeric"

    p2_get = client.get(f"/api/v1/farms/{farm_id}/plots/{p2['plotId']}")
    assert p2_get.status_code == 200
    assert p2_get.json()["data"]["plotId"] == p2["plotId"]
    assert p2_get.json()["data"]["cropCanonicalName"] == "Wheat"


def test_farm_with_plots_validates_as_c2_contract():
    farm_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = farm_res.json()["data"]["farmId"]

    client.post(
        f"/api/v1/farms/{farm_id}/plots",
        json={"areaM2": {"value": 1000, "unit": "m2"}, "cropQuery": "haldi", "plantingDate": "2026-06-01"},
    )

    # Fetch farm and validate against C2FarmDefinition
    get_res = client.get(f"/api/v1/farms/{farm_id}")
    farm_data = get_res.json()["data"]

    farm_model = FarmResponse.model_validate(farm_data)
    c2 = farm_model.to_c2_definition()
    assert isinstance(c2, C2FarmDefinition)
    assert c2.contract_version == "1.0"
    assert len(c2.plots) == 1
    assert c2.plots[0].area_m2.value == 1000
    assert c2.plots[0].area_m2.unit == "m2"


def test_create_plot_invalid_crop_id_rejected():
    farm_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm_id = farm_res.json()["data"]["farmId"]

    invalid_id = "00000000-0000-0000-0000-999999999999"
    plot_payload = {
        "areaM2": {"value": 1000.0, "unit": "m2"},
        "cropId": invalid_id,
    }
    plot_res = client.post(f"/api/v1/farms/{farm_id}/plots", json=plot_payload)
    assert plot_res.status_code == 422
    err = plot_res.json()["error"]
    assert "VALIDATION_ERROR" in err["code"]
    assert "not found in registry" in err["message"]


def test_get_plot_cross_farm_isolation():
    farm1_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm1_id = farm1_res.json()["data"]["farmId"]

    farm2_res = client.post("/api/v1/farms", json=_valid_farm_payload())
    farm2_id = farm2_res.json()["data"]["farmId"]

    p1 = client.post(
        f"/api/v1/farms/{farm1_id}/plots",
        json={"areaM2": {"value": 500, "unit": "m2"}, "cropQuery": "haldi"},
    ).json()["data"]

    # Fetching farm1's plot using farm2's ID must return 404
    res = client.get(f"/api/v1/farms/{farm2_id}/plots/{p1['plotId']}")
    assert res.status_code == 404
