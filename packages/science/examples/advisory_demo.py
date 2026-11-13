"""Replay the repository C1/C3/C8 fixtures through FAO-56 with fixed inputs."""

from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import sys

SCIENCE = Path(__file__).resolve().parents[1]
FIXTURES = SCIENCE.parent / "contracts" / "fixtures"
sys.path.insert(0, str(SCIENCE / "src"))

from terrapulse_science import (  # noqa: E402
    compare_advisory_signals, evaluate_advisory_signals, run_fao, turmeric_profile,
)
from terrapulse_science.contracts import stable_hash  # noqa: E402
from terrapulse_science.repository_contracts import (  # noqa: E402
    c3_states_from_run, fao_input_from_c1_v1,
)

DECISION_DATE = "2026-06-07"


def _fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def replay():
    c1 = _fixture("c1")
    c3 = _fixture("c3")
    first = c1["simulationPeriod"]["startDate"]
    c1["simulationPeriod"]["endDate"] = DECISION_DATE
    # Replay the existing one-day dry-weather fixture across a seven-day dry spell.
    c1["dailyWeather"] = [
        {**c1["dailyWeather"][0], "date": (date.fromisoformat(first) + timedelta(days=i)).isoformat()}
        for i in range(7)
    ]
    c1["provenance"][0]["reference"] = "Repository C1 fixture; dry day repeated as an assumption"

    irrigated = _fixture("c8")
    irrigated["branchId"] = "00000000-0000-0000-0000-000000000014"
    # Withdrawal already includes conveyance/application loss.
    irrigated["closingVolume"]["value"] = 9000
    baseline = deepcopy(irrigated)
    baseline["branchId"] = c3["branchId"]
    baseline["plotAllocations"] = []
    baseline["losses"]["value"] = 0
    baseline["closingVolume"]["value"] = baseline["openingVolume"]["value"]

    branches = {}
    runs = {}
    run_ids = {
        "baseline": c3["simulationRunId"],
        "alternative": "00000000-0000-0000-0000-000000000015",
    }
    for name, ledger, days in (
        ("baseline", baseline, []),
        ("alternative", irrigated, [{"date": DECISION_DATE, "effectiveLitres": 900}]),
    ):
        schedule = {"ledgerHash": stable_hash(ledger), "resourceId": ledger["resourceId"],
                    "plotId": c3["plotId"], "days": days}
        inputs = fao_input_from_c1_v1(
            c1, plot_id=c3["plotId"], branch_id=ledger["branchId"], area_m2=100,
            planting_date=first, crop=turmeric_profile("A"), root_depth_m=0.3,
            depletion_fraction=0.4, initial_depletion_mm=10,
            weather_realization_id="repeated-c1-dry-day", ensemble_member_id="member-01",
            weather_kind="assumption", ledger=ledger, schedule=schedule,
        )
        run = runs[name] = run_fao(inputs.request)
        provenance = {"sources": inputs.provenance, "weatherKind": "assumption",
                      "irrigation": {"ledgerHash": schedule["ledgerHash"],
                                     "scheduleHash": stable_hash(schedule)}}
        branches[name] = {
            "ledger": ledger,
            "schedule": schedule,
            "waterBalance": run["waterBalance"],
            "c3": c3_states_from_run(run, farm_id=inputs.farm_id,
                                     simulation_run_id=run_ids[name], provenance=inputs.provenance),
            "advisory": evaluate_advisory_signals(
                run, date=DECISION_DATE, simulation_run_id=run_ids[name], input_provenance=provenance,
            ),
        }

    return {
        "scenario": "Turmeric FAO-56 mapping A numerical sensitivity example",
        "limitations": "Repeated fixture weather and provisional parameters. Farm forecast validity is unestablished.",
        "decisions": {
            "baseline": "Continue rainfed through June 7.",
            "alternative": "Test the fixture's scheduled water delivery on June 7.",
        },
        "branches": branches,
        "comparison": compare_advisory_signals(
            runs["baseline"], runs["alternative"], date=DECISION_DATE, fork_date=DECISION_DATE,
            baseline_simulation_run_id=run_ids["baseline"],
            alternative_simulation_run_id=run_ids["alternative"],
            baseline_input_provenance=branches["baseline"]["advisory"]["provenance"]["inputs"],
            alternative_input_provenance=branches["alternative"]["advisory"]["provenance"]["inputs"],
        ),
    }


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True, allow_nan=False))
