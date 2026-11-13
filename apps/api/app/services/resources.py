from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.models import (
    DecisionBranch,
    Farm,
    FarmResource,
    Plot,
    ResourceAllocation,
    ResourceLedger,
    ResourcePlotAuthorization,
    TimelineEvent,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

LEDGER_TOL_L = Decimal("0.000001")
WATER_UNIT = "litre"


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_{field.upper()}") from exc
    if not result.is_finite():
        raise ValueError(f"INVALID_{field.upper()}")
    return result


def _stable_hash(value: object) -> str:
    science_path = Path(__file__).parents[4] / "packages" / "science" / "src"
    if str(science_path) not in sys.path:
        sys.path.insert(0, str(science_path))
    from terrapulse_science.contracts import stable_hash

    return stable_hash(value)


def _measurement(value: Decimal) -> dict[str, Any]:
    return {
        "value": float(value),
        "unit": WATER_UNIT,
        "availability": {"status": "available"},
    }


class ResourceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_resource(
        self,
        farm_id: UUID,
        *,
        name: str,
        resource_type: str,
        opening_volume: Decimal,
        metadata: dict[str, Any],
    ) -> FarmResource:
        if await self.session.get(Farm, farm_id) is None:
            raise ValueError("FARM_NOT_FOUND")
        if not name.strip():
            raise ValueError("RESOURCE_NAME_REQUIRED")
        if opening_volume < 0:
            raise ValueError("NEGATIVE_OPENING_VOLUME")
        resource = FarmResource(
            id=uuid4(),
            farm_id=farm_id,
            name=name.strip(),
            resource_type=resource_type.strip(),
            unit=WATER_UNIT,
            opening_volume=opening_volume,
            metadata_json=metadata,
        )
        self.session.add(resource)
        await self.session.commit()
        await self.session.refresh(resource)
        return resource

    async def get_resource(self, farm_id: UUID, resource_id: UUID) -> FarmResource:
        resource = await self.session.get(FarmResource, resource_id)
        if resource is None:
            raise ValueError("RESOURCE_NOT_FOUND")
        if resource.farm_id != farm_id:
            raise ValueError("RESOURCE_FARM_MISMATCH")
        return resource

    async def list_resources(self, farm_id: UUID) -> list[FarmResource]:
        result = await self.session.execute(
            select(FarmResource).where(FarmResource.farm_id == farm_id).order_by(FarmResource.created_at)
        )
        return list(result.scalars())

    async def assign_plot(self, farm_id: UUID, resource_id: UUID, plot_id: UUID) -> ResourcePlotAuthorization:
        resource = await self.get_resource(farm_id, resource_id)
        plot = await self.session.get(Plot, plot_id)
        if plot is None or plot.farm_id != farm_id:
            raise ValueError("PLOT_FARM_MISMATCH")
        existing = await self.session.scalar(
            select(ResourcePlotAuthorization).where(
                ResourcePlotAuthorization.resource_id == resource.id,
                ResourcePlotAuthorization.plot_id == plot_id,
            )
        )
        if existing is not None:
            return existing
        assignment = ResourcePlotAuthorization(
            id=uuid4(), resource_id=resource.id, plot_id=plot_id
        )
        self.session.add(assignment)
        self.session.add(
            TimelineEvent(
                id=uuid4(),
                farm_id=farm_id,
                plot_id=plot_id,
                event_type="resource_assigned",
                event_date=date.today(),
                description=f"Authorized plot {plot_id} to use {resource.name}.",
                payload={"resourceId": str(resource.id)},
            )
        )
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def initialize_branch_ledgers(
        self, farm_id: UUID, branch_id: UUID, parent_branch_id: UUID | None, fork_date: date
    ) -> None:
        resources = await self.session.execute(
            select(FarmResource).where(FarmResource.farm_id == farm_id)
        )
        for resource in resources.scalars():
            existing = await self._current_ledger(resource.id, branch_id)
            if existing is not None:
                continue
            inherited: list[ResourceAllocation] = []
            if parent_branch_id is not None:
                result = await self.session.execute(
                    select(ResourceAllocation).where(
                        ResourceAllocation.resource_id == resource.id,
                        ResourceAllocation.branch_id == parent_branch_id,
                        ResourceAllocation.allocation_date <= fork_date,
                    )
                )
                for source in result.scalars():
                    inherited.append(
                        ResourceAllocation(
                            id=uuid4(),
                            resource_id=source.resource_id,
                            branch_id=branch_id,
                            plot_id=source.plot_id,
                            allocation_id=f"{source.allocation_id}:inherited:{branch_id}",
                            idempotency_key=f"{source.idempotency_key}:inherited:{branch_id}",
                            allocation_date=source.allocation_date,
                            requested_litres=source.requested_litres,
                            withdrawn_litres=source.withdrawn_litres,
                            effective_litres=source.effective_litres,
                            loss_litres=source.loss_litres,
                            measurement_provenance={
                                **(source.measurement_provenance or {}),
                                "inheritedFrom": str(source.id),
                            },
                            inherited=True,
                            source_allocation_id=source.id,
                        )
                    )
            self.session.add_all(inherited)
            await self.session.flush()
            payload = self._payload(resource, branch_id, inherited)
            self.session.add(
                ResourceLedger(
                    id=uuid4(),
                    resource_id=resource.id,
                    branch_id=branch_id,
                    payload=payload,
                    closing_volume=Decimal(str(payload["closingVolume"]["value"])),
                    version=1,
                    ledger_hash=_stable_hash(payload),
                    validation_status="valid",
                )
            )
        await self.session.flush()

    async def get_ledger(self, farm_id: UUID, resource_id: UUID, branch_id: UUID) -> ResourceLedger:
        resource = await self.get_resource(farm_id, resource_id)
        await self._branch(farm_id, branch_id)
        ledger = await self._current_ledger(resource.id, branch_id)
        if ledger is None:
            await self.initialize_branch_ledgers(farm_id, branch_id, None, date.today())
            await self.session.commit()
            ledger = await self._current_ledger(resource.id, branch_id)
        if ledger is None:
            raise ValueError("LEDGER_NOT_FOUND")
        return ledger

    async def list_ledger_versions(
        self, farm_id: UUID, resource_id: UUID, branch_id: UUID
    ) -> list[ResourceLedger]:
        await self.get_resource(farm_id, resource_id)
        await self._branch(farm_id, branch_id)
        result = await self.session.execute(
            select(ResourceLedger)
            .where(
                ResourceLedger.resource_id == resource_id,
                ResourceLedger.branch_id == branch_id,
            )
            .order_by(ResourceLedger.version)
        )
        return list(result.scalars())

    async def list_allocations(
        self, farm_id: UUID, resource_id: UUID, branch_id: UUID
    ) -> list[ResourceAllocation]:
        await self.get_ledger(farm_id, resource_id, branch_id)
        result = await self.session.execute(
            select(ResourceAllocation)
            .where(
                ResourceAllocation.resource_id == resource_id,
                ResourceAllocation.branch_id == branch_id,
            )
            .order_by(ResourceAllocation.allocation_date, ResourceAllocation.created_at)
        )
        return list(result.scalars())

    async def allocate(
        self,
        farm_id: UUID,
        resource_id: UUID,
        branch_id: UUID,
        *,
        plot_id: UUID,
        allocation_id: str,
        idempotency_key: str,
        allocation_date: date,
        requested: Decimal,
        withdrawn: Decimal,
        effective: Decimal,
        provenance: dict[str, Any],
    ) -> tuple[ResourceAllocation, ResourceLedger]:
        resource = await self.get_resource(farm_id, resource_id)
        branch = await self._branch(farm_id, branch_id)
        plot = await self.session.get(Plot, plot_id)
        if plot is None or plot.farm_id != farm_id:
            raise ValueError("PLOT_FARM_MISMATCH")
        authorized = await self.session.scalar(
            select(ResourcePlotAuthorization).where(
                ResourcePlotAuthorization.resource_id == resource_id,
                ResourcePlotAuthorization.plot_id == plot_id,
            )
        )
        if authorized is None:
            raise ValueError("PLOT_RESOURCE_NOT_ASSIGNED")
        if not allocation_id.strip() or not idempotency_key.strip():
            raise ValueError("ALLOCATION_ID_REQUIRED")
        existing = await self.session.scalar(
            select(ResourceAllocation).where(
                ResourceAllocation.resource_id == resource_id,
                ResourceAllocation.branch_id == branch_id,
                ResourceAllocation.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            same = (
                existing.allocation_id == allocation_id
                and existing.plot_id == plot_id
                and Decimal(str(existing.withdrawn_litres)) == withdrawn
                and Decimal(str(existing.effective_litres)) == effective
            )
            if not same:
                raise ValueError("IDEMPOTENCY_CONFLICT")
            ledger = await self.get_ledger(farm_id, resource_id, branch_id)
            return existing, ledger
        duplicate = await self.session.scalar(
            select(ResourceAllocation).where(
                ResourceAllocation.resource_id == resource_id,
                ResourceAllocation.branch_id == branch_id,
                ResourceAllocation.allocation_id == allocation_id,
            )
        )
        if duplicate is not None:
            raise ValueError("DUPLICATE_ALLOCATION")
        if min(requested, withdrawn, effective) < 0:
            raise ValueError("NEGATIVE_ALLOCATION")
        if effective > withdrawn + LEDGER_TOL_L or withdrawn > requested + LEDGER_TOL_L:
            raise ValueError("LEDGER_CONSERVATION")
        current = await self._current_ledger(resource_id, branch_id, lock=True)
        if current is None:
            await self.initialize_branch_ledgers(farm_id, branch_id, branch.parent_branch_id, branch.effective_date)
            await self.session.flush()
            current = await self._current_ledger(resource_id, branch_id, lock=True)
        allocations = await self._allocation_rows(resource_id, branch_id)
        available = _decimal(resource.opening_volume, "opening_volume") - sum(
            (_decimal(row.withdrawn_litres, "withdrawn_litres") for row in allocations), Decimal()
        )
        if withdrawn > available + LEDGER_TOL_L:
            raise ValueError("INSUFFICIENT_WATER")
        loss = withdrawn - effective
        allocation = ResourceAllocation(
            id=uuid4(),
            resource_id=resource_id,
            branch_id=branch_id,
            plot_id=plot_id,
            allocation_id=allocation_id,
            idempotency_key=idempotency_key,
            allocation_date=allocation_date,
            requested_litres=requested,
            withdrawn_litres=withdrawn,
            effective_litres=effective,
            loss_litres=loss,
            measurement_provenance=provenance,
        )
        self.session.add(allocation)
        await self.session.flush()
        allocations.append(allocation)
        payload = self._payload(resource, branch_id, allocations)
        ledger = ResourceLedger(
            id=uuid4(),
            resource_id=resource_id,
            branch_id=branch_id,
            payload=payload,
            closing_volume=Decimal(str(payload["closingVolume"]["value"])),
            version=(current.version or 0) + 1 if current else 1,
            ledger_hash=_stable_hash(payload),
            parent_ledger_id=current.id if current else None,
            validation_status="valid",
        )
        self.session.add(ledger)
        self.session.add(
            TimelineEvent(
                id=uuid4(),
                farm_id=farm_id,
                plot_id=plot_id,
                branch_id=branch_id,
                event_type="water_allocation",
                event_date=allocation_date,
                description=f"Allocated {effective} litre effective water to plot {plot_id}.",
                payload={
                    "resourceId": str(resource_id),
                    "allocationId": allocation_id,
                    "ledgerVersion": ledger.version,
                    "ledgerHash": ledger.ledger_hash,
                },
            )
        )
        await self.session.commit()
        await self.session.refresh(ledger)
        return allocation, ledger

    async def _branch(self, farm_id: UUID, branch_id: UUID) -> DecisionBranch:
        branch = await self.session.get(DecisionBranch, branch_id)
        if branch is None or branch.farm_id != farm_id:
            raise ValueError("BRANCH_SCOPE_MISMATCH")
        return branch

    async def _current_ledger(
        self, resource_id: UUID, branch_id: UUID, lock: bool = False
    ) -> ResourceLedger | None:
        query = (
            select(ResourceLedger)
            .where(
                ResourceLedger.resource_id == resource_id,
                ResourceLedger.branch_id == branch_id,
            )
            .order_by(ResourceLedger.version.desc())
            .limit(1)
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def _allocation_rows(self, resource_id: UUID, branch_id: UUID) -> list[ResourceAllocation]:
        result = await self.session.execute(
            select(ResourceAllocation)
            .where(
                ResourceAllocation.resource_id == resource_id,
                ResourceAllocation.branch_id == branch_id,
            )
            .order_by(ResourceAllocation.allocation_date, ResourceAllocation.created_at)
        )
        return list(result.scalars())

    @staticmethod
    def _payload(
        resource: FarmResource, branch_id: UUID, allocations: list[ResourceAllocation]
    ) -> dict[str, Any]:
        opening = _decimal(resource.opening_volume, "opening_volume")
        by_plot: dict[UUID, dict[str, Decimal]] = {}
        withdrawals = Decimal()
        losses = Decimal()
        for row in allocations:
            item = by_plot.setdefault(
                row.plot_id,
                {"requested": Decimal(), "withdrawn": Decimal(), "effective": Decimal()},
            )
            item["requested"] += _decimal(row.requested_litres, "requested_litres")
            item["withdrawn"] += _decimal(row.withdrawn_litres, "withdrawn_litres")
            item["effective"] += _decimal(row.effective_litres, "effective_litres")
            withdrawals += _decimal(row.withdrawn_litres, "withdrawn_litres")
            losses += _decimal(row.loss_litres, "loss_litres")
        closing = opening - withdrawals
        difference = opening - withdrawals - closing
        return {
            "contractVersion": "1.0",
            "farmId": str(resource.farm_id),
            "branchId": str(branch_id),
            "resourceId": str(resource.id),
            "unit": WATER_UNIT,
            "openingVolume": _measurement(opening),
            "plotAllocations": [
                {
                    "plotId": str(plot_id),
                    "requestedAmount": _measurement(values["requested"]),
                    "withdrawnAmount": _measurement(values["withdrawn"]),
                    "effectiveAmount": _measurement(values["effective"]),
                }
                for plot_id, values in sorted(by_plot.items(), key=lambda item: str(item[0]))
            ],
            "losses": _measurement(losses),
            "closingVolume": _measurement(closing),
            "accountingValidation": {
                "isValid": abs(difference) <= LEDGER_TOL_L,
                "difference": _measurement(difference),
            },
            "errors": [],
        }

    async def build_scientific_inputs(
        self,
        farm_id: UUID,
        resource_id: UUID,
        branch_id: UUID,
        plot_id: UUID,
        *,
        area_m2: Decimal,
        start_date: date,
        end_date: date,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        ledger = await self.get_ledger(farm_id, resource_id, branch_id)
        authorized = await self.session.scalar(
            select(ResourcePlotAuthorization).where(
                ResourcePlotAuthorization.resource_id == resource_id,
                ResourcePlotAuthorization.plot_id == plot_id,
            )
        )
        if authorized is None:
            raise ValueError("PLOT_RESOURCE_NOT_ASSIGNED")
        payload = ledger.payload
        if payload.get("branchId") != str(branch_id) or payload.get("farmId") != str(farm_id):
            raise ValueError("LEDGER_BRANCH_MISMATCH")
        allocations = await self.list_allocations(farm_id, resource_id, branch_id)
        days = [
            {"date": row.allocation_date.isoformat(), "effectiveLitres": float(row.effective_litres)}
            for row in allocations
            if row.plot_id == plot_id and start_date <= row.allocation_date <= end_date
        ]
        aggregate: dict[str, float] = {}
        for row in days:
            aggregate[row["date"]] = aggregate.get(row["date"], 0) + row["effectiveLitres"]
        schedule = {
            "ledgerHash": ledger.ledger_hash,
            "resourceId": str(resource_id),
            "plotId": str(plot_id),
            "days": [
                {"date": day, "effectiveLitres": value}
                for day, value in sorted(aggregate.items())
            ],
        }
        science_path = Path(__file__).parents[4] / "packages" / "science" / "src"
        if str(science_path) not in sys.path:
            sys.path.insert(0, str(science_path))
        from terrapulse_science.repository_contracts import irrigation_from_c8_v1

        irrigation_from_c8_v1(
            payload,
            farm_id=str(farm_id),
            branch_id=str(branch_id),
            plot_id=str(plot_id),
            area_m2=float(area_m2),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            schedule=schedule,
        )
        return payload, schedule
