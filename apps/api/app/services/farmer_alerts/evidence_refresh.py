"""Refresh a small number of consented farms from the real environmental adapters.

The existing environmental service acquires Open-Meteo / SoilGrids evidence. No
agronomic alert is constructed here; the current, provenance-gated alert evaluator
remains authoritative. Never call providers for a farm without active opt-in.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select

log = logging.getLogger("terrapulse.farmer_alerts.refresh")


async def refresh_subscribed_evidence(
    session_factory: Callable, *, now: datetime, max_plots: int = 2,
) -> dict[str, int]:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not 1 <= max_plots <= 5:
        raise ValueError("max_plots must be between 1 and 5")

    from app.models import EnvironmentalProvenance, EnvironmentalSnapshot, Farm, Plot
    from app.services.environmental.service import EnvironmentalInputService
    from app.services.farmer_alerts.models import TelegramSubscription
    from app.services.onboarding import _parse_point_coordinates

    # Oldest evidence first. A fresh snapshot avoids duplicate provider traffic;
    # DB opt-in is checked again immediately before the stored snapshot is committed.
    latest = select(
        EnvironmentalSnapshot.plot_id.label("plot_id"),
        func.max(EnvironmentalSnapshot.created_at).label("latest_at"),
    ).group_by(EnvironmentalSnapshot.plot_id).subquery()
    subscribed = exists(select(TelegramSubscription.id).where(
        TelegramSubscription.farm_id == Farm.id,
        TelegramSubscription.active.is_(True),
    ))
    async with session_factory() as session:
        rows = (await session.execute(select(Farm, Plot, latest.c.latest_at)
            .join(Plot, Plot.farm_id == Farm.id)
            .outerjoin(latest, latest.c.plot_id == Plot.id)
            .where(subscribed)
            .order_by(latest.c.latest_at.asc().nullsfirst(), Plot.id)
            .limit(max_plots))).all()

    refreshed = skipped = failed = 0
    service = EnvironmentalInputService()
    for farm, plot, last_at in rows:
        if last_at is not None:
            comparable = last_at if last_at.tzinfo else last_at.replace(tzinfo=timezone.utc)
            if now - comparable < timedelta(hours=20):
                skipped += 1
                continue
        try:
            local_date = now.astimezone(ZoneInfo(farm.timezone)).date()
            location = _parse_point_coordinates(farm.location)
            result = await service.prepare(
                farm_id=farm.id,
                plot_id=plot.id,
                latitude=location.latitude,
                longitude=location.longitude,
                start_date=local_date,
                end_date=local_date + timedelta(days=2),
                timezone=farm.timezone,
                crop_id=plot.crop_id,
                requested_outputs=[],
                include_ensemble=False,
                soil_target_depth_cm=30,
                require_quantitative_simulation=False,
            )
            if result.status.value != "available":
                skipped += 1
                continue
            data = result.model_dump(by_alias=True, mode="json")
            c1 = data.get("c1Input") or {}
            if c1.get("availability", {}).get("status") != "available":
                skipped += 1
                continue
            data["retrievedAt"] = c1.get("retrievedAt")
            data["provenance"] = c1.get("provenance", [])
            # A live source has to provide provenance and actual dated weather.
            if not (c1.get("dailyWeather") and c1.get("provenance") and c1.get("dataSourceIds")):
                skipped += 1
                continue
            async with session_factory() as session:
                async with session.begin():
                    active = await session.scalar(select(TelegramSubscription.id).where(
                        TelegramSubscription.farm_id == farm.id,
                        TelegramSubscription.active.is_(True),
                    ).limit(1))
                    if active is None:
                        continue
                    record = EnvironmentalSnapshot(
                        farm_id=farm.id, plot_id=plot.id, payload=data,
                        availability=result.status.value,
                        input_hash=result.input_hash or
                            f"{farm.id}:{plot.id}:{local_date}:{local_date + timedelta(days=2)}",
                    )
                    session.add(record)
                    await session.flush()
                    for source in data["provenance"]:
                        session.add(EnvironmentalProvenance(
                            snapshot_id=record.id,
                            source_id=source["sourceId"],
                            source_version=source.get("sourceVersion"),
                            retrieved_at=datetime.fromisoformat(source["retrievedAt"]),
                            payload=source,
                        ))
            refreshed += 1
        except Exception as exc:
            # Provider failure cannot stop other subscribed farms or the cron.
            log.warning("Evidence refresh unavailable: %s", type(exc).__name__)
            failed += 1
    return {"refreshed": refreshed, "skipped": skipped, "failed": failed}
