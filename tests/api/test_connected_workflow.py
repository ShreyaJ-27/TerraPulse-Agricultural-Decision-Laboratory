"""Connected workflow against a migrated, disposable PostgreSQL/PostGIS database."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.event_loop import new_event_loop
from app.core.db import SessionFactory, engine
from app.main import app
from app.models import BranchDecision, DecisionBranch, EnvironmentalSnapshot, Farm, TimelineEvent
from app.routers.farms import get_onboarding_service
from app.services.farmer_alerts import persistence
from app.services.farmer_alerts.models import TelegramDelivery, TelegramSubscription, TelegramUpdateCursor
from app.services.farmer_alerts.telegram import DeliveryResult
from app.services.farmer_alerts.worker import run_cycle

pytestmark = pytest.mark.skipif(
    os.environ.get("TERRAPULSE_RUN_DB_TESTS") != "1",
    reason="Requires an explicitly selected disposable PostgreSQL/PostGIS database.",
)


def test_registered_farm_calendar_advisory_and_telegram(monkeypatch):
    with asyncio.Runner(loop_factory=new_event_loop) as runner:
        runner.run(check_workflow(monkeypatch))


async def check_workflow(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setenv("TERRAPULSE_TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "terrapulse_example_bot")
    monkeypatch.delitem(app.dependency_overrides, get_onboarding_service, raising=False)
    clock = datetime.now(UTC).replace(hour=6, minute=0, second=0, microsecond=0)
    monkeypatch.setattr(persistence, "now_utc", lambda: clock)
    headers = {"Authorization": "Bearer " + uuid4().hex + uuid4().hex}
    outsider = {"Authorization": "Bearer " + uuid4().hex + uuid4().hex}
    chat_id = 87654321
    farm_id = None
    cursor_id = None

    class Bot:
        def __init__(self):
            self.updates = []
            self.replies = []
            self.alerts = []

        async def get_updates(self, **kwargs):
            return [row for row in self.updates if row["update_id"] >= kwargs["offset"]]

        async def send(self, recipient, message):
            assert recipient == chat_id
            if "planting" in message:
                self.alerts.append(message)
                if len(self.alerts) == 1:
                    return DeliveryResult(False, retry_after=90, error_code="RATE_LIMIT")
                return DeliveryResult(True, message_id=2001)
            self.replies.append(message)
            return DeliveryResult(True, message_id=1001)

        def command(self, update_id, text):
            self.updates.append({
                "update_id": update_id,
                "message": {
                    "chat": {"id": chat_id, "type": "private"},
                    "from": {"id": chat_id, "language_code": "en"},
                    "text": text,
                },
            })

    bot = Bot()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://terrapulse.test"
    ) as client:
        try:
            assert (await client.get("/api/v1/farms")).status_code == 401
            response = await client.post("/api/v1/farms", headers=headers, json={
                "name": "Integration test farm",
                "timezone": "UTC",
                "location": {"latitude": 30.9, "longitude": 75.8, "crs": "EPSG:4326"},
                "locationConfirmed": True,
            })
            assert response.status_code == 201, response.text
            data = response.json()["data"]
            farm_id = data["farmId"]
            farm_path = f"/api/v1/farms/{farm_id}"
            calendar_path = f"/api/v1/agri-calendar/farms/{farm_id}"
            token = data["telegramConnectUrl"].split("start=")[1]
            assert (await client.get(farm_path, headers=outsider)).status_code == 404
            assert (await client.get(calendar_path, headers=outsider)).status_code == 404
            assert (await client.post(f"{farm_path}/telegram-link", headers=outsider)).status_code == 404
            assert (await client.get("/api/v1/farms", headers=outsider)).json()["data"]["farms"] == []
            assert (await client.get(farm_path, headers=headers)).json()["data"]["location"]["latitude"] == 30.9

            crop_id = "00000000-0000-0000-0000-000000000010"
            planting = datetime.now(UTC).date() + timedelta(days=1)
            response = await client.post(f"{farm_path}/plots", headers=headers, json={
                "areaM2": {"value": 1500, "unit": "m2"},
                "cropId": crop_id,
                "plantingDate": planting.isoformat(),
                "management": {"regionId": "IN-PB", "plotName": "North", "plantingDateCertainty": "estimated"},
            })
            assert response.status_code == 201, response.text
            plot_id = response.json()["data"]["plotId"]
            calendar = (await client.get(calendar_path, headers=headers)).json()["data"]["plots"][0]
            assert calendar["plotName"] == "North"
            assert calendar["next31Days"][0]["date"] == planting.isoformat()
            assert calendar["next31Days"][0]["certainty"] == "estimated"
            assert calendar["regionalSource"] == "Punjab Agricultural University"
            assert calendar["undatedActivities"]
            advisory = await client.get(f"/api/v1/advisory/regions/IN-PB/crops/{crop_id}")
            assert advisory.json()["data"]["status"] == "regional_context_available"
            analysis = await client.post("/api/v1/analysis", headers=headers, json={
                "farmId": farm_id, "plotId": plot_id, "question": "What crop evidence is available?",
                "language": "en", "includeWeather": False, "includeSoil": False,
                "includeCrop": True, "includeSimulation": False, "includeComparison": False,
            })
            assert analysis.status_code == 200, analysis.text
            assert analysis.json()["data"]["evidenceSummary"]["cropCanonicalName"] == "Maize"

            async with SessionFactory() as session:
                snapshot = EnvironmentalSnapshot(
                    farm_id=UUID(farm_id), plot_id=UUID(plot_id), payload={},
                    availability="unavailable", input_hash=uuid4().hex,
                )
                session.add(snapshot)
                await session.commit()
                snapshot_id = str(snapshot.id)
            plot_path = f"{farm_path}/plots/{plot_id}"
            decision = await client.post(f"{plot_path}/branches", headers=headers, json={
                "plotId": plot_id, "environmentalSnapshotId": snapshot_id,
                "effectiveDate": planting.isoformat(), "decisionType": "planting_date",
                "decisionDiff": {"plantingDate": planting.isoformat()},
            })
            assert decision.status_code == 201, decision.text
            timeline = await client.get(f"{plot_path}/timeline", headers=headers)
            assert timeline.json()["data"]["events"][0]["payload"]["decisionType"] == "planting_date"

            async with SessionFactory() as session:
                existing_cursor = await session.get(TelegramUpdateCursor, 1)
                cursor_id = existing_cursor.next_update_id if existing_cursor else None
            update_id = cursor_id or 1
            bot.command(update_id, f"/start {token}")
            dry = await run_cycle(SessionFactory, bot, live=False)
            assert dry["commandsProcessed"] == 0 and bot.replies == []
            first = await run_cycle(SessionFactory, bot, live=True)
            assert first["newAlerts"] == 1 and first["newDeliveries"] == 1
            assert first["delivery"]["claimed"] == 0  # 06:00 UTC is quiet time.
            bot.command(update_id + 1, f"/start {token}")
            clock += timedelta(hours=1)
            retry = await run_cycle(SessionFactory, bot, live=True)
            assert "expired" in bot.replies[-1]
            assert retry["newAlerts"] == 0 and retry["newDeliveries"] == 0
            assert retry["delivery"]["failed"] == 1
            async with SessionFactory() as session:
                delivery = await session.scalar(select(TelegramDelivery).join(TelegramSubscription)
                    .where(TelegramSubscription.farm_id == farm_id))
                assert delivery.status == "pending" and delivery.attempts == 1
                assert delivery.next_attempt_at == clock + timedelta(seconds=90)
            clock += timedelta(seconds=91)
            delivered = await run_cycle(SessionFactory, bot, live=True)
            assert delivered["delivery"]["sent"] == 1
            async with SessionFactory() as session:
                delivery = await session.scalar(select(TelegramDelivery).join(TelegramSubscription)
                    .where(TelegramSubscription.farm_id == farm_id))
                assert delivery.telegram_message_id == 2001 and delivery.attempts == 2

            bot.command(update_id + 2, "/stop")
            stopped = await run_cycle(SessionFactory, bot, live=True)
            assert stopped["delivery"]["sent"] == 0
            async with SessionFactory() as session:
                subscription = await session.scalar(select(TelegramSubscription)
                    .where(TelegramSubscription.farm_id == farm_id))
                assert subscription.active is False
        finally:
            async with SessionFactory() as session:
                if farm_id:
                    branches = select(DecisionBranch.id).where(DecisionBranch.farm_id == farm_id)
                    await session.execute(delete(TimelineEvent).where(TimelineEvent.farm_id == farm_id))
                    await session.execute(delete(BranchDecision).where(BranchDecision.branch_id.in_(branches)))
                    await session.execute(delete(DecisionBranch).where(DecisionBranch.farm_id == farm_id))
                    await session.execute(delete(EnvironmentalSnapshot).where(EnvironmentalSnapshot.farm_id == farm_id))
                    await session.execute(delete(Farm).where(Farm.id == farm_id))
                cursor = await session.get(TelegramUpdateCursor, 1)
                if cursor and cursor_id is None:
                    await session.delete(cursor)
                elif cursor:
                    cursor.next_update_id = cursor_id
                await session.commit()
            await engine.dispose()
