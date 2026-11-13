"""HTTP regressions for secured webhook, daily cron, and one-bot activation."""
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.core.db import get_session
from app.routers import telegram_integration as telegram

WEBHOOK_HEADERS = {"X-Telegram-Bot-Api-Secret-Token": "safe_test_webhook_secret_12345"}
PRIVATE_COMMAND = {
    "chat": {"type": "private", "id": 123},
    "from": {"id": 123, "language_code": "en", "is_bot": False},
    "text": "/start SECURE-ONETIME-CODE",
}


@asynccontextmanager
async def transaction():
    yield

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TERRAPULSE_TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "safe_test_webhook_secret_12345")
    monkeypatch.setenv("CRON_SECRET", "safe_test_cron_secret_67890")
    app = FastAPI()
    app.include_router(telegram.router)
    app.dependency_overrides[get_session] = lambda: SimpleNamespace(begin=transaction)
    with TestClient(app) as test_client:
        yield test_client


def test_webhook_requires_secret_and_does_not_echo_sensitive_data(client):
    payload = {"update_id": 10, "message": {"text": "/start SOME-SENSITIVE-CODE"}}
    response = client.post("/api/v1/telegram/webhook", json=payload)
    assert response.status_code == 403
    assert "SOME-SENSITIVE-CODE" not in response.text
    response = client.post("/api/v1/telegram/webhook", json=payload,
                           headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"})
    assert response.status_code == 403


def test_webhook_ignored_replay_is_idempotent(client, monkeypatch):
    claim = AsyncMock(return_value=False)
    command = AsyncMock()
    monkeypatch.setattr(telegram, "claim_webhook_update", claim)
    monkeypatch.setattr(telegram, "handle_command", command)
    response = client.post("/api/v1/telegram/webhook", headers=WEBHOOK_HEADERS,
                           json={"update_id": 41, "message": PRIVATE_COMMAND})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "duplicate": True}
    claim.assert_awaited_once()
    command.assert_not_awaited()


def test_webhook_consumes_one_update_and_replies(client, monkeypatch):
    claim = AsyncMock(side_effect=[True, False, True])
    command = AsyncMock(return_value="🌱 Connected")
    sends = []

    class FakeTelegram:
        async def send(self, chat_id, message):
            sends.append((chat_id, message))
            return SimpleNamespace(success=True)

    monkeypatch.setattr(telegram, "claim_webhook_update", claim)
    monkeypatch.setattr(telegram, "handle_command", command)
    monkeypatch.setattr(telegram, "TelegramClient", FakeTelegram)
    update = {"update_id": 42, "message": PRIVATE_COMMAND}
    response = client.post("/api/v1/telegram/webhook", json=update,
                           headers={"X-Telegram-Bot-Api-Secret-Token": "safe_test_webhook_secret_12345"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "duplicate": False}
    command.assert_awaited_once()
    assert sends == [(123, "🌱 Connected")]
    assert "SECURE-ONETIME-CODE" not in response.text
    replay = client.post("/api/v1/telegram/webhook", json=update, headers=WEBHOOK_HEADERS)
    assert replay.json() == {"ok": True, "duplicate": True}
    lower = client.post("/api/v1/telegram/webhook", headers=WEBHOOK_HEADERS,
                        json={**update, "update_id": 17})
    assert lower.json() == {"ok": True, "duplicate": False}
    assert sends == [(123, "🌱 Connected")] * 2


def test_webhook_bounds_input_and_rejects_ambiguous_auth(client, monkeypatch):
    claim = AsyncMock()
    monkeypatch.setattr(telegram, "claim_webhook_update", claim)
    url = "/api/v1/telegram/webhook"
    name, secret = next(iter(WEBHOOK_HEADERS.items()))
    assert client.post(url, headers=[(name, secret), (name, secret)]).status_code == 403
    assert client.post(url, headers=[(name.encode(), b"\xff")]).status_code == 403
    assert client.post(url, headers=WEBHOOK_HEADERS,
                       content=b" " * (telegram.MAX_UPDATE_BYTES + 1)).status_code == 413
    assert client.post(url, headers=WEBHOOK_HEADERS,
                       json={"update_id": 2**63}).status_code == 400
    assert client.post(url, headers=WEBHOOK_HEADERS,
                       json={"update_id": 2, "message": ["bad"]}).status_code == 200
    claim.assert_not_awaited()


def test_webhook_disabled_and_malformed(client, monkeypatch):
    monkeypatch.setenv("TERRAPULSE_TELEGRAM_ENABLED", "0")
    response = client.post("/api/v1/telegram/webhook", json={"update_id": 1},
                           headers={"X-Telegram-Bot-Api-Secret-Token": "safe_test_webhook_secret_12345"})
    assert response.status_code == 503
    monkeypatch.setenv("TERRAPULSE_TELEGRAM_ENABLED", "1")
    response = client.post("/api/v1/telegram/webhook", content="not-json",
                           headers={"X-Telegram-Bot-Api-Secret-Token": "safe_test_webhook_secret_12345"})
    assert response.status_code == 400


def test_cron_requires_authorization(client):
    assert client.get("/api/v1/telegram/cron").status_code == 403
    assert client.get("/api/v1/telegram/cron", headers={"Authorization": "Bearer wrong"}).status_code == 403


def test_cron_only_uses_existing_persisted_evidence(client, monkeypatch):
    class SessionFactory:
        async def __aenter__(self):
            return object()
        async def __aexit__(self, *_):
            return False

    monkeypatch.setattr(telegram, "SessionFactory", SessionFactory)
    monkeypatch.setattr(telegram, "TelegramClient", lambda: object())
    monkeypatch.setattr(telegram, "load_profiles_file", lambda p: {})
    evaluate = AsyncMock(return_value=(2, 1))
    send = AsyncMock(return_value={"claimed": 1, "sent": 1, "failed": 0, "dryRun": 0})
    monkeypatch.setattr(telegram, "evaluate_registered_farms", evaluate)
    monkeypatch.setattr(telegram, "deliver_queued", send)
    response = client.get("/api/v1/telegram/cron", headers={"Authorization": "Bearer safe_test_cron_secret_67890"})
    assert response.status_code == 200
    assert response.json()["delivery"]["sent"] == 1
    evaluate.assert_awaited_once()
    send.assert_awaited_once()


@pytest.mark.parametrize("status", [401, 403])
def test_activation_refuses_protected_preview(client, monkeypatch, status):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL_URL", "preview.example.vercel.app")
    class Response:
        status_code = status

        def json(self):
            return {"detail": "Edge access denied"}
    class FakeHttp:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_): pass
        async def post(self, *_args, **_kwargs): return Response()
    monkeypatch.setattr(telegram.httpx, "AsyncClient", FakeHttp)
    response = client.post("/api/v1/telegram/activate-webhook", headers={"Authorization": "Bearer safe_test_cron_secret_67890"})
    assert response.status_code == 409


def test_activation_requires_public_webhook_and_sets_single_connection(client, monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL_URL", "preview.example.vercel.app")
    class Response:
        status_code = 403

        def json(self):
            return {"detail": "Telegram webhook authentication failed"}
    class FakeHttp:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_): pass
        async def post(self, *_args, **_kwargs): return Response()
    called = []
    class FakeTelegram:
        async def _call(self, method, data):
            called.append((method, data))
            return 200, {"ok": True, "result": True}
    monkeypatch.setattr(telegram.httpx, "AsyncClient", FakeHttp)
    monkeypatch.setattr(telegram, "TelegramClient", FakeTelegram)
    response = client.post("/api/v1/telegram/activate-webhook", headers={"Authorization": "Bearer safe_test_cron_secret_67890"})
    assert response.status_code == 200
    assert called[0][0] == "setWebhook"
    assert called[0][1]["max_connections"] == 1
    assert called[0][1]["url"].startswith("https://preview.example.vercel.app/")
    assert "safe_test_webhook_secret_12345" not in response.text
