"""No live Telegram or network dependency: saved-farm one-tap access checks."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.services.farmer_alerts import workspace_links
from app.services.farmer_alerts.commands import handle_command
from app.core.config import Settings


def test_preview_and_production_always_require_farm_keys(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    assert Settings(app_env="development").require_workspace_key is True
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert Settings(app_env="development").require_workspace_key is True
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    assert Settings(app_env="development").require_workspace_key is False


def test_open_url_origin_cannot_be_controlled_by_request_host(monkeypatch):
    monkeypatch.setenv("TERRAPULSE_FARM_ORIGIN", "https://farm.example.org")
    assert workspace_links.workspace_origin() == "https://farm.example.org"
    monkeypatch.setenv("TERRAPULSE_FARM_ORIGIN", "https://farm.example.org.evil.test/recover")
    with pytest.raises(ValueError):
        workspace_links.workspace_origin()
    monkeypatch.setenv("TERRAPULSE_FARM_ORIGIN", "https://farm.example.org/?token=leak")
    with pytest.raises(ValueError):
        workspace_links.workspace_origin()
    monkeypatch.delenv("TERRAPULSE_FARM_ORIGIN")
    monkeypatch.setenv("VERCEL_BRANCH_URL", "terrapulse-branch.vercel.app")
    assert workspace_links.workspace_origin() == "https://terrapulse-branch.vercel.app"


@pytest.mark.asyncio
async def test_open_link_only_for_existing_active_matching_subscription(monkeypatch):
    monkeypatch.setenv("TERRAPULSE_FARM_ORIGIN", "https://farm.example.org")
    added = []
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[uuid4(), 0]), add=added.append)
    url = await workspace_links.issue_one_tap_link(session, chat_id=123, user_id=123)
    assert url.startswith("https://farm.example.org/recover#open=")
    token = url.split("#open=", 1)[1]
    assert len(token) == 43
    assert token not in repr(added[0].__dict__)
    assert added[0].token_hash == workspace_links.token_digest(token)
    assert added[0].approved_chat_id == 123
    assert added[0].approved_user_id == 123
    assert added[0].approved_at is not None
    assert added[0].farm_id is None  # a single link restores all connected farms
    assert len(added) == 1
    session.scalar = AsyncMock(return_value=None)
    assert await workspace_links.issue_one_tap_link(session, chat_id=123, user_id=123) is None
    assert await workspace_links.issue_one_tap_link(session, chat_id=123, user_id=124) is None
    assert len(added) == 1


@pytest.mark.asyncio
async def test_open_link_issue_is_rate_limited(monkeypatch):
    monkeypatch.setenv("TERRAPULSE_FARM_ORIGIN", "https://farm.example.org")
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[uuid4(), 12]), add=lambda _: pytest.fail("unexpected write"))
    with pytest.raises(HTTPException) as exc:
        await workspace_links.issue_one_tap_link(session, chat_id=456, user_id=456)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_redeem_grants_all_active_farms_only_once():
    farm1, farm2 = uuid4(), uuid4()
    row = SimpleNamespace(redeemed_at=None, approved_at=datetime.now(timezone.utc),
                          expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                          approved_chat_id=123, approved_user_id=123, farm_id=None,
                          client_hash=workspace_links._chat_hash(123))
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=row),
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [farm1, farm2, farm1])),
        execute=AsyncMock(),
    )
    result = await workspace_links.redeem_one_tap_link(session, token="x" * 43, browser_digest="a" * 64)
    assert set(result) == {str(farm1), str(farm2)}
    assert row.redeemed_at is not None
    stmt = session.execute.await_args.args[0]
    statement = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT" in statement and "DO NOTHING" in statement
    assert stmt._multi_values  # bulk insert, not N+1 inserts
    with pytest.raises(HTTPException) as exc:
        await workspace_links.redeem_one_tap_link(session, token="x" * 43, browser_digest="a" * 64)
    assert exc.value.status_code == 404
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_expired_link_and_stopped_telegram_cannot_grant():
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    row = SimpleNamespace(redeemed_at=None, approved_at=past, expires_at=past,
                          approved_chat_id=123, approved_user_id=123, farm_id=None,
                          client_hash=workspace_links._chat_hash(123))
    session = SimpleNamespace(scalar=AsyncMock(return_value=row), scalars=AsyncMock(), execute=AsyncMock())
    with pytest.raises(HTTPException) as exc:
        await workspace_links.redeem_one_tap_link(session, token="a" * 43, browser_digest="b" * 64)
    assert exc.value.status_code == 404
    session.scalars.assert_not_awaited()
    session.execute.assert_not_awaited()
    row.expires_at = datetime.now(timezone.utc) + timedelta(minutes=3)
    session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: []))
    with pytest.raises(HTTPException):
        await workspace_links.redeem_one_tap_link(session, token="a" * 43, browser_digest="b" * 64)
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_that_expires_or_is_redeemed_while_waiting_cannot_grant():
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        approved_at=now, expires_at=now + timedelta(minutes=5), redeemed_at=None,
        approved_chat_id=123, approved_user_id=123, farm_id=None,
        client_hash=workspace_links._chat_hash(123),
    )
    claimed = SimpleNamespace(redeemed_at=now, expires_at=row.expires_at)
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[row, claimed]),
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [uuid4()])),
        execute=AsyncMock(),
    )
    with pytest.raises(HTTPException) as exc:
        await workspace_links.redeem_one_tap_link(session, token="a" * 43, browser_digest="b" * 64)
    assert exc.value.status_code == 404
    lock = str(session.scalar.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in lock
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_farm_key_and_granted_browser_access_stay_scoped():
    from app.core.access import require_farm_access
    session = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(workspace_key_hash="a" * 64)),
                              scalar=AsyncMock(return_value=None))
    await require_farm_access(session, uuid4(), "a" * 64)
    session.scalar.assert_not_awaited()
    with pytest.raises(HTTPException) as exc:
        await require_farm_access(session, uuid4(), "b" * 64)
    assert exc.value.status_code == 404
    session.scalar = AsyncMock(return_value=uuid4())
    await require_farm_access(session, uuid4(), "b" * 64)


@pytest.mark.asyncio
async def test_telegram_open_command_requires_existing_subscription(monkeypatch):
    linked = [SimpleNamespace(active=True)]
    operations = SimpleNamespace(subscriptions_for_chat=AsyncMock(return_value=linked))
    called = []
    async def issue(_, *, chat_id, user_id):
        called.append((chat_id, user_id))
        return "https://farm.example.org/recover#open=opaque-token"
    monkeypatch.setattr(workspace_links, "issue_one_tap_link", issue)
    result = await handle_command(None, chat_id=123, user_id=123, language="en", text="/open", operations=operations)
    assert "https://farm.example.org/recover" in result
    assert called == [(123, 123)]
    operations.subscriptions_for_chat = AsyncMock(return_value=[])
    result = await handle_command(None, chat_id=123, user_id=123, language="en", text="/open", operations=operations)
    assert "link your farm" in result
    assert called == [(123, 123)]
