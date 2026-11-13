from __future__ import annotations

import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.contracts import C5Comparison
from app.models import DecisionBranch, SimulationComparison, SimulationRun
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ComparisonService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def compare(
        self,
        farm_id: UUID,
        plot_id: UUID,
        branch_a_id: UUID,
        branch_b_id: UUID,
        run_a_id: UUID,
        run_b_id: UUID,
        fork_date: date | None,
    ) -> SimulationComparison:
        branches = await self.session.execute(
            select(DecisionBranch).where(
                DecisionBranch.id.in_([branch_a_id, branch_b_id]),
                DecisionBranch.farm_id == farm_id,
                DecisionBranch.plot_id == plot_id,
            )
        )
        branch_map = {branch.id: branch for branch in branches.scalars()}
        if len(branch_map) != 2 or branch_a_id == branch_b_id:
            raise ValueError("BRANCH_SCOPE_MISMATCH")
        runs = await self.session.execute(
            select(SimulationRun).where(
                SimulationRun.id.in_([run_a_id, run_b_id]),
                SimulationRun.farm_id == farm_id,
                SimulationRun.plot_id == plot_id,
            )
        )
        run_map = {run.id: run for run in runs.scalars()}
        if len(run_map) != 2:
            raise ValueError("RUN_SCOPE_MISMATCH")
        run_a, run_b = run_map[run_a_id], run_map[run_b_id]
        if run_a.branch_id != branch_a_id or run_b.branch_id != branch_b_id:
            raise ValueError("RUN_BRANCH_MISMATCH")
        if run_a.status != "completed" or run_b.status != "completed":
            raise ValueError("RUN_INCOMPLETE")
        if not run_a.science_envelope or not run_b.science_envelope:
            raise ValueError("SCIENCE_ENVELOPE_MISSING")

        result = self._compare(
            run_a.science_envelope,
            run_b.science_envelope,
            run_a,
            run_b,
            fork_date,
        )
        result["c5"] = self._project_c5(result, run_a, run_b, fork_date or date.today())
        status = result["status"]
        comparison = SimulationComparison(
            id=uuid4(),
            farm_id=farm_id,
            plot_id=plot_id,
            branch_a_id=branch_a_id,
            branch_b_id=branch_b_id,
            run_a_id=run_a_id,
            run_b_id=run_b_id,
            comparison_date=fork_date or date.today(),
            matched_inputs=status == "comparable",
            status=status,
            non_comparable_reasons=result.get("reasons", []),
            payload={
                "result": result,
                "provenance": {
                    "baseline": self._provenance(run_a),
                    "alternative": self._provenance(run_b),
                },
                "createdAt": datetime.now(UTC).isoformat(),
            },
        )
        self.session.add(comparison)
        await self.session.commit()
        await self.session.refresh(comparison)
        return comparison

    async def get(self, farm_id: UUID, plot_id: UUID, comparison_id: UUID) -> SimulationComparison:
        comparison = await self.session.get(SimulationComparison, comparison_id)
        if comparison is None or comparison.farm_id != farm_id or comparison.plot_id != plot_id:
            raise ValueError("COMPARISON_SCOPE_MISMATCH")
        return comparison

    async def list(self, farm_id: UUID, plot_id: UUID) -> list[SimulationComparison]:
        result = await self.session.execute(
            select(SimulationComparison)
            .where(
                SimulationComparison.farm_id == farm_id,
                SimulationComparison.plot_id == plot_id,
            )
            .order_by(SimulationComparison.comparison_date.desc())
        )
        return list(result.scalars())

    @staticmethod
    def _compare(
        envelope_a: dict[str, Any],
        envelope_b: dict[str, Any],
        run_a: SimulationRun,
        run_b: SimulationRun,
        fork_date: date | None,
    ) -> dict[str, Any]:
        science_path = Path(__file__).parents[4] / "packages" / "science" / "src"
        if str(science_path) not in sys.path:
            sys.path.insert(0, str(science_path))
        from terrapulse_science.compare import compare_runs

        a = dict(envelope_a)
        b = dict(envelope_b)
        a["runId"], b["runId"] = str(run_a.id), str(run_b.id)
        a["status"], b["status"] = "completed", "completed"
        return compare_runs(a, b, fork_date=fork_date.isoformat() if fork_date else None)

    @staticmethod
    def _provenance(run: SimulationRun) -> dict[str, Any]:
        envelope = run.science_envelope or {}
        return {
            "simulationRunId": str(run.id),
            "farmId": str(run.farm_id),
            "plotId": str(run.plot_id),
            "branchId": str(run.branch_id),
            "environmentalSnapshotId": str(run.environmental_snapshot_id)
            if run.environmental_snapshot_id
            else None,
            "inputHash": run.input_hash,
            "engine": run.engine_name,
            "engineVersion": run.engine_version,
            "parameterVersion": run.parameter_version,
            "weatherRealizationId": run.weather_realization_id,
            "weatherMemberId": run.weather_member_id,
            "scienceInputHash": envelope.get("inputHash"),
            "inputProvenance": run.input_provenance,
        }

    @staticmethod
    def _project_c5(
        result: dict[str, Any],
        run_a: SimulationRun,
        run_b: SimulationRun,
        comparison_date: date,
    ) -> dict[str, Any]:
        metrics = []
        for day in result.get("daily", []):
            for metric in day.get("metrics", []):
                metrics.append(
                    {
                        "metric": f"{metric['name']}@{day['date']}",
                        "valueA": {
                            "value": metric["branchA"],
                            "unit": metric["unit"],
                            "availability": {"status": "available"},
                        },
                        "valueB": {
                            "value": metric["branchB"],
                            "unit": metric["unit"],
                            "availability": {"status": "available"},
                        },
                        "difference": {
                            "value": metric["differenceBMinusA"],
                            "unit": metric["unit"],
                            "availability": {"status": "available"},
                        },
                    }
                )
        payload = {
            "contractVersion": "1.0",
            "branchA": run_a.branch_id,
            "branchB": run_b.branch_id,
            "comparisonDate": comparison_date,
            "matchedInputs": result["status"] == "comparable",
            "metrics": metrics,
            "availability": {
                "status": "available" if result["status"] == "comparable" else "unsupported",
                "reason": None
                if result["status"] == "comparable"
                else "; ".join(result.get("reasons", [])),
            },
            "assumptions": result.get("warnings", []),
            "provenance": [
                {
                    "sourceId": f"simulation:{run_a.id}",
                    "sourceVersion": run_a.engine_version,
                    "retrievedAt": run_a.completed_at or run_a.requested_at,
                    "reference": run_a.input_hash,
                },
                {
                    "sourceId": f"simulation:{run_b.id}",
                    "sourceVersion": run_b.engine_version,
                    "retrievedAt": run_b.completed_at or run_b.requested_at,
                    "reference": run_b.input_hash,
                },
            ],
        }
        return C5Comparison.model_validate(payload).model_dump(by_alias=True, mode="json")
