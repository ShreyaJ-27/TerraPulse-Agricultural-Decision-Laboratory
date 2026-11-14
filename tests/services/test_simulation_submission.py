from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.models import DecisionBranch, EnvironmentalSnapshot, Plot
from app.services.simulations.orchestration import SimulationService, farm_execution_blocker
from app.services.simulations.schemas import SimulationSubmitRequest
from terrapulse_science.crop_binding import TURMERIC_ID


def test_farm_capability_uses_verified_science_binding():
    from uuid import UUID

    assert farm_execution_blocker(TURMERIC_ID) is None
    assert farm_execution_blocker(UUID("00000000-0000-0000-0000-000000000010"))[0] == (
        "UNSUPPORTED_CROP_CAPABILITY"
    )
    assert farm_execution_blocker(UUID("00000000-0000-0000-0000-000000000020"))[0] == (
        "CROP_EXAMPLE_ONLY"
    )


@pytest.mark.asyncio
async def test_submit_persists_branch_planting_and_explicit_fallow_assumption():
    farm_id, plot_id, snapshot_id, branch_id = [uuid4() for _ in range(4)]
    plot = SimpleNamespace(farm_id=farm_id, crop_id=TURMERIC_ID, planting_date=date(2026, 11, 14))
    snapshot = SimpleNamespace(
        id=snapshot_id, farm_id=farm_id, plot_id=plot_id, input_hash="matched", payload={},
    )
    branch = SimpleNamespace(
        farm_id=farm_id, plot_id=plot_id, base_snapshot_hash="matched",
        decision_type="planting_date", decision_diff={"plantingDate": "2026-11-15"},
    )
    records = {Plot: plot, EnvironmentalSnapshot: snapshot, DecisionBranch: branch}
    session = SimpleNamespace(
        get=AsyncMock(side_effect=lambda model, _id: records[model]),
        add=Mock(), flush=AsyncMock(), commit=AsyncMock(),
    )
    request = SimulationSubmitRequest(
        farmId=farm_id, plotId=plot_id, environmentalSnapshotId=snapshot_id,
        branchId=branch_id, turmericMapping="A", irrigationMode="rainfed", fallowKc=0,
    )
    run = await SimulationService(session).submit(request)
    assert run.input_provenance["plantingDate"] == "2026-11-15"
    assert run.input_provenance["fallowKc"] == 0.0

    branch.base_snapshot_hash = "different"
    with pytest.raises(ValueError, match="BRANCH_SNAPSHOT_MISMATCH"):
        await SimulationService(session).submit(request)
