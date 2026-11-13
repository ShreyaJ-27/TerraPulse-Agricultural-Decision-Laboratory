"""Single free Telegram polling worker and evidence-backed alert evaluator.

Reads TerraPulse's existing farm/plot/C1/C3 records. Never creates a parallel farm
registry or calls Open-Meteo as a side-effect of notification delivery.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Callable, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .calendar import CropCalendarProfile, PlantingDate
from .commands import handle_command
from .decision import evaluate_calendar, evaluate_science, evaluate_weather
from .messages import render
from .persistence import (ack_delivery, advance_cursor, claim_deliveries,
                          enqueue_events, get_cursor)
from .telegram import TelegramClient, command_from_update


async def process_updates(session_factory: Callable, telegram: TelegramClient) -> int:
    """Telegram's getUpdates must have only one polling worker per bot."""
    async with session_factory() as session:
        offset = await get_cursor(session)
    updates = await telegram.get_updates(offset=offset)
    processed = 0
    for update in sorted(updates, key=lambda row: row.get("update_id", -1)):
        update_id = update.get("update_id")
        if not isinstance(update_id, int) or update_id < offset:
            continue
        parsed = command_from_update(update)
        if parsed is not None:
            chat_id, user_id, locale, message = parsed
            async with session_factory() as session:
                reply = await handle_command(session, chat_id=chat_id, user_id=user_id,
                                             language=locale, text=message)
                await session.commit()
            # One-time linking is committed before the greeting is sent. If the
            # greeting fails, the subscription still works for future alerts.
            result = await telegram.send(chat_id, reply)
            if not result.success and result.error_code not in ("BOT_BLOCKED", "BAD_REQUEST"):
                raise RuntimeError("Telegram command reply temporarily failed")
            processed += 1
        async with session_factory() as session:
            await advance_cursor(session, update_id)
        offset = update_id + 1
    return processed


async def evaluate_registered_farms(session: AsyncSession, *, now: datetime,
                                    regional_profiles: Mapping[tuple[str, UUID], CropCalendarProfile] | None = None
                                    ) -> tuple[int, int]:
    """Generate notifications only for active linked farms and existing evidence.

    A missing planting date or regional profile never blocks a weather or science
    review. No synthetic crop stages, weather, or scientific states are made up.
    """
    from app.models import (CropIdentity, EnvironmentalSnapshot, Farm, Plot,
                            ScientificState, SimulationRun)
    from .models import TelegramSubscription

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    regional_profiles = regional_profiles or {}
    farm_ids = list((await session.scalars(select(TelegramSubscription.farm_id)
        .where(TelegramSubscription.active.is_(True)).distinct())).all())
    events = []
    for farm_id in farm_ids:
        farm = await session.get(Farm, farm_id)
        if farm is None:
            continue
        try:
            local_today = now.astimezone(ZoneInfo(farm.timezone)).date()
        except (ValueError, KeyError):
            local_today = now.date()
        plots = list((await session.scalars(select(Plot).where(Plot.farm_id == farm_id))).all())
        for plot in plots:
            meta = plot.management or {}
            crop = await session.get(CropIdentity, plot.crop_id) if plot.crop_id else None
            crop_name = crop.canonical_name if crop else "your crop"
            region_id = meta.get("regionId")
            profile = regional_profiles.get((region_id, plot.crop_id)) if isinstance(region_id, str) and plot.crop_id else None
            events += evaluate_calendar(farm_id=farm.id, plot_id=plot.id, crop_name=crop_name,
                planting=PlantingDate.from_plot(plot.planting_date, meta), on_date=local_today,
                profile=profile, crop_id=plot.crop_id, region_id=region_id)
            # Use already stored weather evidence, not a second provider request.
            snapshot = await session.scalar(select(EnvironmentalSnapshot).where(
                EnvironmentalSnapshot.farm_id == farm.id,
                EnvironmentalSnapshot.plot_id == plot.id,
                EnvironmentalSnapshot.availability == "available",
            ).order_by(EnvironmentalSnapshot.created_at.desc()).limit(1))
            if snapshot and isinstance(snapshot.payload, dict):
                c1 = snapshot.payload.get("c1Input")
                if isinstance(c1, dict):
                    events += evaluate_weather(farm_id=farm.id, plot_id=plot.id,
                        crop_name=crop_name, c1=c1, on_date=local_today, now=now)
            # Only a matching stored state, never a generic yield/crop prediction.
            row = await session.execute(select(ScientificState, SimulationRun).join(
                SimulationRun, ScientificState.simulation_run_id == SimulationRun.id).where(
                ScientificState.plot_id == plot.id,
                ScientificState.state_date == local_today,
                ScientificState.availability == "available",
                SimulationRun.status == "completed",
            ).order_by(SimulationRun.completed_at.desc()).limit(1))
            pair = row.first()
            if pair and isinstance(pair[0].payload, dict):
                events += evaluate_science(farm_id=farm.id, plot_id=plot.id,
                    crop_name=crop_name, c3=pair[0].payload,
                    on_date=local_today, run_id=pair[1].id)
    return await enqueue_events(session, events)


async def deliver_queued(session_factory: Callable, telegram: TelegramClient | None,
                         *, dry_run: bool = True, limit: int = 30) -> dict[str, int]:
    """Outbox with retries, duplicate suppression and quiet hours.

    Dry-run is safe by default. A real send is only possible with explicit --live.
    """
    if dry_run:
        return {"claimed": 0, "sent": 0, "failed": 0, "dryRun": 1}
    if telegram is None:
        raise ValueError("Live delivery requires a Telegram client")
    async with session_factory() as session:
        batch = await claim_deliveries(session, limit=limit)
    outcomes = {"claimed": len(batch), "sent": 0, "failed": 0, "dryRun": 0}
    for delivery_id, chat_id, locale, event in batch:
        result = await telegram.send(chat_id, render(event, locale))
        async with session_factory() as session:
            await ack_delivery(session, delivery_id,
                message_id=result.message_id if result.success else None,
                error_code=result.error_code if not result.success else None,
                retry_after=result.retry_after)
        outcomes["sent" if result.success else "failed"] += 1
    return outcomes


async def run_cycle(session_factory: Callable, telegram: TelegramClient | None,
                    *, live: bool, profiles: Mapping | None = None) -> dict:
    count = await process_updates(session_factory, telegram) if live and telegram is not None else 0
    async with session_factory() as session:
        alerts, deliveries = await evaluate_registered_farms(session,
            now=datetime.now(timezone.utc), regional_profiles=profiles)
    results = await deliver_queued(session_factory, telegram, dry_run=not live)
    return {"commandsProcessed": count, "newAlerts": alerts,
            "newDeliveries": deliveries, "delivery": results}


async def forever(session_factory: Callable, telegram: TelegramClient | None,
                  *, live: bool, interval_seconds: int = 600, profiles: Mapping | None = None) -> None:
    """Respond promptly to first Telegram Start; evaluate agricultural data less often.

    getUpdates uses free Telegram long polling (15 seconds), not high-frequency
    HTTP calls or a paid hosting/webhook provider. Only one process per bot.
    """
    if not 60 <= interval_seconds <= 3600:
        raise ValueError("agricultural evaluation interval must be 60..3600 seconds")
    loop = asyncio.get_running_loop()
    last_evaluation = -float("inf")
    while True:
        try:
            processed = await process_updates(session_factory, telegram) if live and telegram is not None else 0
            now = loop.time()
            if processed or now - last_evaluation >= interval_seconds:
                async with session_factory() as session:
                    alerts, new_deliveries = await evaluate_registered_farms(
                        session, now=datetime.now(timezone.utc), regional_profiles=profiles)
                last_evaluation = now
                if alerts or new_deliveries:
                    print("TerraPulse farm alerts queued:", alerts, new_deliveries, flush=True)
            if live:
                outcome = await deliver_queued(session_factory, telegram, dry_run=False)
                if outcome["claimed"]:
                    print("TerraPulse delivery counts:", outcome, flush=True)
            if not live:
                await asyncio.sleep(interval_seconds)
        except Exception as exc:
            print("TerraPulse alert worker error:", type(exc).__name__, flush=True)
            await asyncio.sleep(5)
