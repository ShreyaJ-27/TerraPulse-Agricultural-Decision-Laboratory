from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.contracts import C3ScientificState, Coordinates
from app.models import (
    DecisionBranch,
    EnvironmentalSnapshot,
    ScientificState,
    SimulationComparison,
    SimulationRun,
)
from app.schemas import FarmCreateRequest, PlotAreaInput, PlotCreateRequest
from app.services.analysis import AnalysisRequest, EvidenceBundleBuilder
from app.services.analysis.evidence_builder import AnalysisEvidenceError
from app.services.comparisons import ComparisonService
from app.services.crop_lens.registry import CROP_REGISTRY
from app.services.crop_lens.resolver import CropLensResolver
from app.services.environmental import EnvironmentalInputService
from app.services.onboarding import OnboardingService

FIXTURES = Path(__file__).parents[2] / "packages" / "contracts" / "fixtures"
SAMPLE_C1 = json.loads((FIXTURES / "c1.json").read_text())
SAMPLE_C3 = json.loads((FIXTURES / "c3.json").read_text())
SAMPLE_C5 = json.loads((FIXTURES / "c5.json").read_text())
TURMERIC_ID = UUID("00000000-0000-0000-0000-000000000003")


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, records=(), states=()):
        self.records = {(type(record), record.id): record for record in records}
        self.states = list(states)

    async def get(self, model, record_id):
        return self.records.get((model, record_id))

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        criteria = {}
        requires_completed_at = False
        for clause in statement._where_criteria:
            left = getattr(clause, "left", None)
            right = getattr(clause, "right", None)
            key = getattr(left, "key", None)
            if key and hasattr(right, "value"):
                criteria[key] = right.value
            elif key == "completed_at" and getattr(clause.operator, "__name__", "") == "is_not":
                requires_completed_at = True

        if entity is SimulationRun:
            rows = [
                record
                for (model, _), record in self.records.items()
                if model is SimulationRun
                and all(getattr(record, key) == value for key, value in criteria.items())
                and (not requires_completed_at or record.completed_at is not None)
            ]
            rows.sort(
                key=lambda run: (
                    run.completed_at,
                    run.requested_at,
                    str(run.id),
                ),
                reverse=True,
            )
            return FakeResult(rows[:1])
        if entity is ScientificState:
            rows = [
                state
                for state in self.states
                if all(getattr(state, key) == value for key, value in criteria.items())
            ]
            rows.sort(key=lambda state: (state.state_date, str(state.id)))
            return FakeResult(rows)
        raise AssertionError(f"Unexpected query entity: {entity}")


async def _seed_farm_and_plot():
    onboarding = OnboardingService()
    farm = await onboarding.create_farm(
        FarmCreateRequest(
            name="Persistence Test Farm",
            timezone="Asia/Kolkata",
            location=Coordinates(latitude=16.2, longitude=77.3, crs="EPSG:4326"),
            locationConfirmed=True,
        )
    )
    plot = await onboarding.create_plot(
        farm.farm_id,
        PlotCreateRequest(
            areaM2=PlotAreaInput(value=10000, unit="m2"),
            cropId=TURMERIC_ID,
            plantingDate=date(2026, 6, 1),
        ),
    )
    return onboarding, farm, plot


def _branch(farm_id, plot_id, branch_id, member_id=None):
    return DecisionBranch(
        id=branch_id,
        farm_id=farm_id,
        plot_id=plot_id,
        parent_branch_id=None,
        base_snapshot_hash="base",
        effective_date=date(2026, 6, 1),
        weather_member_id=member_id,
        model_version="1.0",
        input_hashes=[],
        decision_type="baseline",
        decision_diff={},
    )


def _run(farm_id, plot_id, branch_id, run_id, snapshot_id=None, member_id=None):
    completed_at = datetime(2026, 6, 2, tzinfo=UTC)
    return SimulationRun(
        id=run_id,
        farm_id=farm_id,
        plot_id=plot_id,
        branch_id=branch_id,
        engine_name="FAO-56",
        engine_version="1.0",
        status="completed",
        input_hash=f"hash-{run_id}",
        environmental_snapshot_id=snapshot_id,
        parameter_version="parameters-1",
        weather_realization_id="realization-1",
        weather_member_id=member_id,
        requested_at=completed_at,
        started_at=completed_at,
        completed_at=completed_at,
        warnings=["test warning"],
        science_envelope={"states": []},
        input_provenance={"source": "test"},
    )


def _builder(onboarding, session):
    resolver = CropLensResolver(CROP_REGISTRY)
    return EvidenceBundleBuilder(
        onboarding,
        resolver,
        EnvironmentalInputService(crop_resolver=resolver),
        session=session,
    )


@pytest.mark.asyncio
async def test_selected_run_uses_its_persisted_snapshot_and_c3_states():
    onboarding, farm, plot = await _seed_farm_and_plot()
    branch_id, run_id, snapshot_id = uuid4(), uuid4(), uuid4()
    branch = _branch(farm.farm_id, plot.plot_id, branch_id, "member-01")
    run = _run(farm.farm_id, plot.plot_id, branch_id, run_id, snapshot_id, "member-01")
    c1_payload = {**SAMPLE_C1, "farmId": str(farm.farm_id)}
    snapshot = EnvironmentalSnapshot(
        id=snapshot_id,
        farm_id=farm.farm_id,
        plot_id=plot.plot_id,
        payload={"c1Input": c1_payload},
        availability="available",
        input_hash=run.input_hash,
    )
    snapshot.created_at = datetime(2026, 6, 2, tzinfo=UTC)
    c3_payload = {
        **SAMPLE_C3,
        "farmId": str(farm.farm_id),
        "plotId": str(plot.plot_id),
        "branchId": str(branch_id),
        "simulationRunId": str(run_id),
    }
    state_model = C3ScientificState.model_validate(c3_payload)
    state_record = ScientificState(
        id=uuid4(),
        simulation_run_id=run_id,
        plot_id=plot.plot_id,
        branch_id=branch_id,
        state_date=state_model.date,
        payload=c3_payload,
        availability=state_model.availability.status.value,
    )
    session = FakeSession([branch, run, snapshot], [state_record])

    bundle = await _builder(onboarding, session).build(
        AnalysisRequest(
            farmId=farm.farm_id,
            plotId=plot.plot_id,
            branchId=branch_id,
            simulationRunId=run_id,
            includeWeather=False,
            includeSoil=False,
        )
    )

    assert bundle.simulation_metadata["simulationRunId"] == run_id
    assert bundle.simulation_metadata["branchId"] == branch_id
    assert bundle.simulation_metadata["warnings"] == ["test warning"]
    assert bundle.environmental_metadata["snapshotId"] == snapshot_id
    assert bundle.environmental_metadata["inputHash"] == run.input_hash
    assert bundle.environmental_metadata["weatherMemberId"] == "member-01"
    assert len(bundle.c1_input.daily_weather) == 1
    assert bundle.c1_input.daily_weather[0].ensemble_member_id == "member-01"
    assert [state.date for state in bundle.c3_states] == [state_model.date]


@pytest.mark.asyncio
async def test_selected_run_with_wrong_branch_is_rejected():
    onboarding, farm, plot = await _seed_farm_and_plot()
    selected_branch, run_branch, run_id = uuid4(), uuid4(), uuid4()
    records = [
        _branch(farm.farm_id, plot.plot_id, selected_branch),
        _branch(farm.farm_id, plot.plot_id, run_branch),
        _run(farm.farm_id, plot.plot_id, run_branch, run_id),
    ]

    with pytest.raises(AnalysisEvidenceError, match="does not belong to the requested branch"):
        await _builder(onboarding, FakeSession(records)).build(
            AnalysisRequest(
                farmId=farm.farm_id,
                plotId=plot.plot_id,
                branchId=selected_branch,
                simulationRunId=run_id,
                includeWeather=False,
                includeSoil=False,
            )
        )


@pytest.mark.parametrize(
    ("status", "completed_at"),
    [
        ("running", datetime(2026, 6, 2, tzinfo=UTC)),
        ("completed", None),
    ],
)
@pytest.mark.asyncio
async def test_selected_run_must_be_completed(status, completed_at):
    onboarding, farm, plot = await _seed_farm_and_plot()
    branch_id, run_id = uuid4(), uuid4()
    run = _run(farm.farm_id, plot.plot_id, branch_id, run_id)
    run.status = status
    run.completed_at = completed_at

    with pytest.raises(AnalysisEvidenceError, match="no completed scientific result"):
        await _builder(
            onboarding,
            FakeSession([_branch(farm.farm_id, plot.plot_id, branch_id), run]),
        ).build(
            AnalysisRequest(
                farmId=farm.farm_id,
                plotId=plot.plot_id,
                branchId=branch_id,
                simulationRunId=run_id,
                includeWeather=False,
                includeSoil=False,
            )
        )


@pytest.mark.asyncio
async def test_branch_only_selection_uses_latest_completed_run_from_that_branch():
    onboarding, farm, plot = await _seed_farm_and_plot()
    branch_id, other_branch_id = uuid4(), uuid4()
    older_run = _run(farm.farm_id, plot.plot_id, branch_id, uuid4())
    older_run.completed_at = datetime(2026, 6, 2, tzinfo=UTC)
    latest_run = _run(farm.farm_id, plot.plot_id, branch_id, uuid4())
    latest_run.completed_at = datetime(2026, 6, 4, tzinfo=UTC)
    other_branch_run = _run(farm.farm_id, plot.plot_id, other_branch_id, uuid4())
    other_branch_run.completed_at = datetime(2026, 6, 5, tzinfo=UTC)
    other_branch = _branch(farm.farm_id, plot.plot_id, other_branch_id)
    selected_branch = _branch(farm.farm_id, plot.plot_id, branch_id)
    session = FakeSession(
        [selected_branch, other_branch, older_run, latest_run, other_branch_run]
    )

    bundle = await _builder(onboarding, session).build(
        AnalysisRequest(
            farmId=farm.farm_id,
            plotId=plot.plot_id,
            branchId=branch_id,
            includeWeather=False,
            includeSoil=False,
        )
    )

    assert bundle.simulation_metadata["simulationRunId"] == latest_run.id
    assert bundle.simulation_metadata["branchId"] == branch_id


@pytest.mark.asyncio
async def test_persisted_comparison_is_validated_against_pair_and_run_provenance():
    onboarding, farm, plot = await _seed_farm_and_plot()
    branch_a_id, branch_b_id = uuid4(), uuid4()
    run_a = _run(farm.farm_id, plot.plot_id, branch_a_id, uuid4())
    run_b = _run(farm.farm_id, plot.plot_id, branch_b_id, uuid4())
    comparison_id = uuid4()
    comparison_date = date(2026, 6, 1)

    c5_payload = {
        **SAMPLE_C5,
        "branchA": str(branch_a_id),
        "branchB": str(branch_b_id),
        "comparisonDate": comparison_date.isoformat(),
        "provenance": [
            {
                "sourceId": f"simulation:{run.id}",
                "sourceVersion": run.engine_version,
                "retrievedAt": run.completed_at.isoformat(),
                "reference": run.input_hash,
            }
            for run in (run_a, run_b)
        ],
    }
    comparison = SimulationComparison(
        id=comparison_id,
        farm_id=farm.farm_id,
        plot_id=plot.plot_id,
        branch_a_id=branch_a_id,
        branch_b_id=branch_b_id,
        run_a_id=run_a.id,
        run_b_id=run_b.id,
        comparison_date=comparison_date,
        matched_inputs=True,
        status="comparable",
        non_comparable_reasons=[],
        payload={
            "result": {"status": "comparable", "c5": c5_payload},
            "provenance": {
                "baseline": ComparisonService._provenance(run_a),
                "alternative": ComparisonService._provenance(run_b),
            },
            "createdAt": datetime(2026, 6, 3, tzinfo=UTC).isoformat(),
        },
    )
    session = FakeSession(
        [
            _branch(farm.farm_id, plot.plot_id, branch_a_id),
            _branch(farm.farm_id, plot.plot_id, branch_b_id),
            run_a,
            run_b,
            comparison,
        ]
    )

    bundle = await _builder(onboarding, session).build(
        AnalysisRequest(
            farmId=farm.farm_id,
            plotId=plot.plot_id,
            branchId=branch_a_id,
            comparisonBranchId=branch_b_id,
            comparisonId=comparison_id,
            includeSimulation=False,
            includeWeather=False,
            includeSoil=False,
        )
    )

    assert bundle.comparison_metadata["comparisonId"] == comparison_id
    assert bundle.comparison_metadata["runA"] == run_a.id
    assert bundle.comparison_metadata["runB"] == run_b.id
    assert bundle.c5_comparison is not None
    assert bundle.c5_comparison.branch_a == branch_a_id
    assert bundle.c5_comparison.branch_b == branch_b_id

    bundle_with_comparison_run = await _builder(onboarding, session).build(
        AnalysisRequest(
            farmId=farm.farm_id,
            plotId=plot.plot_id,
            branchId=branch_a_id,
            comparisonBranchId=branch_b_id,
            comparisonId=comparison_id,
            includeWeather=False,
            includeSoil=False,
        )
    )
    assert bundle_with_comparison_run.simulation_metadata["simulationRunId"] == run_a.id

    comparison.status = "not_comparable"
    comparison.matched_inputs = False
    comparison.non_comparable_reasons = ["Weather realizations differ."]
    comparison.payload["result"]["status"] = "not_comparable"
    bundle_non_comparable = await _builder(onboarding, session).build(
        AnalysisRequest(
            farmId=farm.farm_id,
            plotId=plot.plot_id,
            branchId=branch_a_id,
            comparisonBranchId=branch_b_id,
            comparisonId=comparison_id,
            includeSimulation=False,
            includeWeather=False,
            includeSoil=False,
        )
    )
    assert bundle_non_comparable.c5_comparison is None
    assert bundle_non_comparable.comparison_metadata["status"] == "not_comparable"
    assert bundle_non_comparable.comparison_metadata["reasons"] == [
        "Weather realizations differ."
    ]
