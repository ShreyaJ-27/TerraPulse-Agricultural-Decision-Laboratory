from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from app.models import BranchDecision, DecisionBranch, EnvironmentalSnapshot, Plot, TimelineEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SUPPORTED_DECISIONS = {"planting_date", "irrigation"}


class BranchService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _plot(self, farm_id: UUID, plot_id: UUID) -> Plot:
        plot = await self.session.get(Plot, plot_id)
        if plot is None or plot.farm_id != farm_id:
            raise ValueError("PLOT_FARM_MISMATCH")
        return plot

    async def _branch(self, farm_id: UUID, plot_id: UUID, branch_id: UUID) -> DecisionBranch:
        branch = await self.session.get(DecisionBranch, branch_id)
        if branch is None or branch.farm_id != farm_id or branch.plot_id != plot_id:
            raise ValueError("BRANCH_SCOPE_MISMATCH")
        return branch

    async def create(
        self,
        farm_id: UUID,
        plot_id: UUID,
        *,
        snapshot_id: UUID,
        effective_date: date,
        decision_type: str = "baseline",
        decision_diff: dict[str, Any] | None = None,
        parent_branch_id: UUID | None = None,
    ) -> DecisionBranch:
        await self._plot(farm_id, plot_id)
        snapshot = await self.session.get(EnvironmentalSnapshot, snapshot_id)
        if snapshot is None or snapshot.farm_id != farm_id or snapshot.plot_id != plot_id:
            raise ValueError("SNAPSHOT_OWNERSHIP_MISMATCH")
        diff = decision_diff or {}
        self._validate_decision(decision_type, diff)
        parent = None
        if parent_branch_id is not None:
            parent = await self._branch(farm_id, plot_id, parent_branch_id)
        branch = DecisionBranch(
            id=uuid4(),
            farm_id=farm_id,
            plot_id=plot_id,
            parent_branch_id=parent.id if parent else None,
            base_snapshot_hash=snapshot.input_hash,
            effective_date=effective_date,
            weather_member_id=self._weather_member(snapshot.payload),
            model_version=self._model_version(snapshot.payload),
            input_hashes=[snapshot.input_hash],
            decision_type=decision_type,
            decision_diff=diff,
        )
        self.session.add(branch)
        await self.session.flush()
        self.session.add(
            BranchDecision(
                id=uuid4(), branch_id=branch.id, decision_type=decision_type, payload=diff
            )
        )
        self.session.add(
            TimelineEvent(
                id=uuid4(),
                farm_id=farm_id,
                plot_id=plot_id,
                branch_id=branch.id,
                event_type="branch_created" if parent else "baseline_created",
                event_date=effective_date,
                description=self._description(decision_type, diff, parent is not None),
                payload={"decisionType": decision_type, "decisionDiff": diff},
            )
        )
        from app.services.resources import ResourceService

        await self.session.flush()
        await ResourceService(self.session).initialize_branch_ledgers(
            farm_id,
            branch.id,
            parent.id if parent else None,
            effective_date,
        )
        await self.session.commit()
        await self.session.refresh(branch)
        return branch

    async def get(self, farm_id: UUID, plot_id: UUID, branch_id: UUID) -> DecisionBranch:
        return await self._branch(farm_id, plot_id, branch_id)

    async def list(self, farm_id: UUID, plot_id: UUID) -> list[DecisionBranch]:
        await self._plot(farm_id, plot_id)
        result = await self.session.execute(
            select(DecisionBranch)
            .where(DecisionBranch.farm_id == farm_id, DecisionBranch.plot_id == plot_id)
            .order_by(DecisionBranch.effective_date, DecisionBranch.created_at)
        )
        return list(result.scalars())

    async def timeline(self, farm_id: UUID, plot_id: UUID) -> list[TimelineEvent]:
        await self._plot(farm_id, plot_id)
        result = await self.session.execute(
            select(TimelineEvent)
            .where(TimelineEvent.farm_id == farm_id, TimelineEvent.plot_id == plot_id)
            .order_by(TimelineEvent.event_date, TimelineEvent.created_at)
        )
        return list(result.scalars())

    @staticmethod
    def _validate_decision(decision_type: str, diff: dict[str, Any]) -> None:
        if decision_type not in SUPPORTED_DECISIONS | {"baseline"}:
            raise ValueError("UNSUPPORTED_DECISION")
        if decision_type == "planting_date":
            value = diff.get("plantingDate")
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError):
                raise ValueError("INVALID_PLANTING_DATE") from None
        if decision_type == "irrigation" and (
            not isinstance(diff.get("ledger"), dict) or not diff["ledger"].get("ledgerHash")
        ):
            raise ValueError("C8_LEDGER_REQUIRED")

    @staticmethod
    def _weather_member(payload: dict) -> str | None:
        rows = payload.get("c1Input", payload).get("dailyWeather", [])
        return next((row.get("ensembleMemberId") for row in rows if row.get("ensembleMemberId")), None)

    @staticmethod
    def _model_version(payload: dict) -> str:
        capability = payload.get("capability") or {}
        return capability.get("engineVersion", "unresolved")

    @staticmethod
    def _description(decision_type: str, diff: dict[str, Any], child: bool) -> str:
        prefix = "Created child branch" if child else "Created baseline branch"
        if decision_type == "planting_date":
            return f"{prefix}: planting date {diff['plantingDate']}"
        if decision_type == "irrigation":
            return f"{prefix}: irrigation ledger {diff['ledger']['ledgerHash']}"
        return prefix
