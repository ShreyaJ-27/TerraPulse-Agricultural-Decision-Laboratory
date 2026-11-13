from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_get_crop_catalog():
    response = client.get("/api/v1/crops")
    assert response.status_code == 200
    payload = response.json()
    assert payload["contractVersion"] == "1.0"
    assert "data" in payload
    assert "crops" in payload["data"]
    assert payload["data"]["total"] >= 5


def test_resolve_crop_exact():
    response = client.get("/api/v1/crops/resolve", params={"q": "haldi"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["contractVersion"] == "1.0"
    data = payload["data"]
    assert data["status"] == "exact_match"
    assert data["crop"]["canonicalName"] == "Turmeric"
    assert data["capability"]["selectedEngine"] == "FAO-56"
    assert data["capability"]["contractVersion"] == "1.0"


def test_resolve_okra_identity_crop():
    response = client.get("/api/v1/crops/resolve", params={"q": "okra"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "exact_match"
    assert data["crop"]["canonicalName"] == "Okra"
    assert data["capability"]["selectedEngine"] == "identity/ecology-only"


def test_resolve_crop_ambiguous():
    response = client.get("/api/v1/crops/resolve", params={"q": "millet"})
    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    assert data["status"] == "ambiguous"
    assert data["crop"] is None
    assert len(data["candidates"]) >= 2


def test_resolve_crop_not_found():
    response = client.get("/api/v1/crops/resolve", params={"q": "fictional_plant"})
    assert response.status_code == 404


def test_resolve_crop_allow_unsupported():
    response = client.get(
        "/api/v1/crops/resolve",
        params={"q": "Dragon Fruit", "allow_unsupported": True, "scientific_name": "Selenicereus undatus"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "unsupported_off_catalogue"
    assert data["capability"]["selectedEngine"] == "identity/ecology-only"
    assert data["capability"]["supportedOutputs"] == []


def test_get_crop_capability_by_id():
    turmeric_id = "00000000-0000-0000-0000-000000000003"
    response = client.get(f"/api/v1/crops/{turmeric_id}/capability")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["contractVersion"] == "1.0"
    assert data["cropId"] == turmeric_id
    assert data["selectedEngine"] == "FAO-56"


def test_get_crop_capability_not_found():
    random_id = "00000000-0000-0000-0000-999999999999"
    response = client.get(f"/api/v1/crops/{random_id}/capability")
    assert response.status_code == 404
