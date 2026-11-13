import json
from pathlib import Path

import pytest

from app.contracts import (
    C1EnvironmentalInput,
    C2FarmDefinition,
    C3ScientificState,
    C4BranchDecision,
    C5Comparison,
    C6VisualState,
    C7ModelCapability,
    C8ResourceLedger,
    Measurement,
)

FIXTURES = Path(__file__).parents[2] / "packages" / "contracts" / "fixtures"
MODELS = [C1EnvironmentalInput, C2FarmDefinition, C3ScientificState, C4BranchDecision, C5Comparison, C6VisualState, C7ModelCapability, C8ResourceLedger]


@pytest.mark.parametrize("number,model", enumerate(MODELS, start=1))
def test_shared_fixture_validates(number, model):
    payload = json.loads((FIXTURES / f"c{number}.json").read_text())
    assert model.model_validate(payload)


def test_unavailable_measurement_cannot_have_a_value():
    with pytest.raises(ValueError):
        Measurement(value=0, unit="mm", availability={"status": "missing"})


def test_coordinates_are_bounded():
    payload = {"latitude": 91, "longitude": 0, "crs": "EPSG:4326"}
    with pytest.raises(ValueError):
        from app.contracts import Coordinates
        Coordinates.model_validate(payload)
