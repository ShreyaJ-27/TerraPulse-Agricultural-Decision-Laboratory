"""Telegram Bot API transport and bounded one-time onboarding commands.

A farmer links through https://t.me/<bot>?start=<opaque-token> after registration.
Telegram requires that first button press; no subsequent bot command is needed.
The bot is NOT a chat assistant or a replacement for TerraPulse.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    message_id: int | None = None
    retry_after: int | None = None
    error_code: str | None = None


class TelegramClient:
    """Small injectable HTTP gateway. Never put the token in logs/errors."""

    def __init__(self, token: str | None = None, *, opener=urlopen):
        self._token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not self._token or any(ch.isspace() for ch in self._token):
            raise ValueError("Set TELEGRAM_BOT_TOKEN in the worker environment")
        self._url = "https://api.telegram.org/bot" + self._token + "/"
        self._opener = opener

    def _call_sync(self, method: str, data: dict, *, timeout: int = 15) -> tuple[int, dict]:
        request = Request(
            self._url + method,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=timeout) as response:
                content = json.load(response)
                return response.status, content if isinstance(content, dict) else {}
        except HTTPError as exc:
            try:
                parsed = json.loads(exc.read().decode("utf-8"))
                parsed = parsed if isinstance(parsed, dict) else {}
            except (ValueError, UnicodeError):
                parsed = {}
            return exc.code, parsed
        except (URLError, TimeoutError, OSError):
            return 0, {}

    async def _call(self, method: str, data: dict, *, timeout: int = 15) -> tuple[int, dict]:
        return await asyncio.to_thread(self._call_sync, method, data, timeout=timeout)

    async def get_updates(self, *, offset: int, limit: int = 50, timeout: int = 15) -> list[dict[str, Any]]:
        if not 0 <= timeout <= 25:
            raise ValueError("Telegram long-poll timeout must be 0..25 seconds")
        status, response = await self._call("getUpdates", {
            "offset": offset, "limit": limit, "timeout": timeout, "allowed_updates": ["message"]
        }, timeout=timeout + 12)
        if status != 200 or response.get("ok") is not True:
            raise RuntimeError("Telegram polling unavailable; will retry later")
        updates = response.get("result")
        if not isinstance(updates, list):
            raise RuntimeError("Unexpected Telegram update response")
        return [item for item in updates if isinstance(item, dict)]

    async def send(self, chat_id: int, message: str) -> DeliveryResult:
        if not isinstance(chat_id, int) or chat_id <= 0:
            return DeliveryResult(False, error_code="INVALID_CHAT")
        status, body = await self._call("sendMessage", {
            "chat_id": chat_id,
            "text": message[:4000],
            "disable_web_page_preview": True,
        })
        if status == 200 and body.get("ok") is True:
            result = body.get("result") or {}
            mid = result.get("message_id") if isinstance(result, dict) else None
            if isinstance(mid, int):
                return DeliveryResult(True, message_id=mid)
            return DeliveryResult(False, retry_after=60, error_code="UNCONFIRMED_SEND")
        if status == 429:
            wait = (body.get("parameters") or {}).get("retry_after", 60)
            return DeliveryResult(False, retry_after=max(1, min(int(wait), 3600)), error_code="RATE_LIMIT")
        if status in (400, 403):
            # No retry after the user blocked the bot; a bad request stays failed.
            return DeliveryResult(False, error_code="BOT_BLOCKED" if status == 403 else "BAD_REQUEST")
        return DeliveryResult(False, retry_after=60, error_code="TEMPORARY_FAILURE")


def create_deep_link(bot_username: str, token: str) -> str:
    """Offer one tap in TerraPulse's registration success screen."""
    if not bot_username or not bot_username.lstrip("@").replace("_", "").isalnum():
        raise ValueError("Invalid Telegram bot username")
    if not token or len(token) > 64 or not all(ch.isalnum() or ch in "_-" for ch in token):
        raise ValueError("Invalid Telegram start token")
    return f"https://t.me/{bot_username.lstrip('@')}?start={token}"


def command_from_update(update: dict) -> tuple[int, int, str, str] | None:
    """Return (chatId, userId, language, command) for private messages only."""
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    author = message.get("from") or {}
    chat_id, user_id = chat.get("id"), author.get("id")
    if chat.get("type") != "private" or not isinstance(chat_id, int) or not isinstance(user_id, int):
        return None
    if chat_id <= 0 or user_id <= 0 or author.get("is_bot"):
        return None
    content = message.get("text")
    if not isinstance(content, str) or not content.strip().startswith("/"):
        return None
    language = (author.get("language_code") or "en").lower().split("-", 1)[0]
    return chat_id, user_id, language if language in {"en", "hi", "kn"} else "en", content.strip()
