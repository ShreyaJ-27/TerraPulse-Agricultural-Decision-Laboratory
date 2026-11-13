from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_interact_endpoint_kannada_turmeric():
    payload = {
        "query": "ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ",
        "language": "kn",
    }
    res = client.post("/api/v1/crops/interact", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["intent"] == "crop_resolution"
    assert data["language"] == "kn"
    assert data["resolutionStatus"] == "exact_match"
    assert data["resolvedCrop"] is not None
    assert data["resolvedCrop"]["canonicalName"] == "Turmeric"
    assert "Turmeric" in data["responseText"]
    assert data["speechText"] != ""
    assert data["escalationRequired"] is False


def test_interact_endpoint_hindi_turmeric():
    payload = {
        "query": "मेरी फसल हल्दी है",
        "language": "hi",
    }
    res = client.post("/api/v1/crops/interact", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["intent"] == "crop_resolution"
    assert data["language"] == "hi"
    assert data["resolutionStatus"] == "exact_match"
    assert data["resolvedCrop"]["canonicalName"] == "Turmeric"


def test_interact_endpoint_english_yield_limitation():
    payload = {
        "query": "I grow turmeric. Can you predict yield?",
        "language": "en",
    }
    res = client.post("/api/v1/crops/interact", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["intent"] == "crop_capability"
    assert "FAO-56" in data["responseText"]
    assert any("yield" in lim.lower() for lim in data["limitations"])


def test_interact_endpoint_plant_pathology_escalation():
    payload = {
        "query": "My crop has brown spots and fungal blight",
        "language": "en",
    }
    res = client.post("/api/v1/crops/interact", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["intent"] == "escalation_plant_pathology"
    assert data["escalationRequired"] is True
    assert "Krishi Vigyan Kendra" in data["responseText"]


def test_interact_endpoint_market_pricing_refusal():
    payload = {
        "query": "What is today's turmeric market price?",
        "language": "en",
    }
    res = client.post("/api/v1/crops/interact", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["intent"] == "refusal_market_pricing"
    assert data["escalationRequired"] is False
    assert "Agmarknet" in data["responseText"]


def test_interact_endpoint_ambiguity_returns_candidates():
    payload = {
        "query": "millet",
        "language": "en",
    }
    res = client.post("/api/v1/crops/interact", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["resolutionStatus"] == "ambiguous"
    assert len(data["candidates"]) >= 3
    assert data["resolvedCrop"] is None


def test_interact_endpoint_empty_query_rejected_422():
    payload = {
        "query": "",
        "language": "en",
    }
    res = client.post("/api/v1/crops/interact", json=payload)
    assert res.status_code == 422
