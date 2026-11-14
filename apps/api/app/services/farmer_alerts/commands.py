"""Short bot interactions. Connecting is a one-time registration step.

Farmer does not have to use commands to receive future notifications.
"""
from __future__ import annotations
from typing import Any
from fastapi import HTTPException


WELCOME = {
    "en": "🌱 TerraPulse is connected!\nCrop and weather updates will arrive here automatically. Send /stop to unsubscribe.",
    "hi": "🌱 TerraPulse जुड़ गया है!\nफसल और मौसम के संदेश अब अपने आप आएँगे। बंद करने के लिए /stop भेजें।",
    "kn": "🌱 TerraPulse ಸಂಪರ್ಕಗೊಂಡಿದೆ!\nಬೆಳೆ ಮತ್ತು ಹವಾಮಾನ ಸಂದೇಶಗಳು ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಬರುತ್ತವೆ. ನಿಲ್ಲಿಸಲು /stop ಕಳುಹಿಸಿ.",
}

HELP = ("TerraPulse 🌱\n"
        "Alerts arrive automatically after your farm is connected.\n"
        "/status · show connection\n"
        "/open · open your saved farms on this device\n"
        "/alerts calendar|weather|science on|off · choose alerts\n"
        "/language en|hi|kn · message language\n"
        "/stop · turn off all alerts\n"
        "/start · resume if already connected")


async def handle_command(session: Any, *, chat_id: int, user_id: int, language: str,
                         text: str, operations: Any = None) -> str:
    """Apply a command within the caller's transaction."""
    if operations is None:
        from . import persistence as operations
    db = operations
    parts = text.strip().split()
    command = parts[0].split("@", 1)[0].lower() if parts else ""
    if command == "/start" and len(parts) == 2:
        linked = await db.consume_link(session, token=parts[1], chat_id=chat_id,
                                       user_id=user_id, locale=language)
        if linked is None:
            return "That connection link has expired. Please reopen Connect Telegram from TerraPulse."
        return WELCOME.get(language, WELCOME["en"])
    if command == "/start":
        count = await db.resume_subscriptions(session, chat_id)
        return ("🌱 TerraPulse alerts are on again." if count else
                "Open the Connect Telegram button after registering your farm in TerraPulse.")
    if command == "/stop":
        count = await db.unsubscribe(session, chat_id)
        return ("Alerts stopped. Send /start if you change your mind." if count else
                "No active TerraPulse alerts for this chat.")
    if command in ("/help", "/settings"):
        return HELP
    linked = await db.subscriptions_for_chat(session, chat_id)
    if not any(sub.active for sub in linked):
        return "Open Connect Telegram in TerraPulse to link your farm first."
    if command == "/open":
        # The existing authenticated private Telegram chat issues the link.
        from .workspace_links import issue_one_tap_link
        try:
            url = await issue_one_tap_link(session, chat_id=chat_id, user_id=user_id)
        except ValueError:
            return "Opening your farms is temporarily unavailable. Please try again later."
        except HTTPException as exc:
            if exc.status_code == 429:
                return "Too many links requested. Please try again in an hour."
            raise
        if not url:
            return "No active farms are linked to this Telegram chat."
        return ("🌱 Open your saved TerraPulse farms:\n" + url
                + "\n\nThis link works once and expires in 10 minutes.")
    if command == "/status":
        count = sum(1 for item in linked if item.active)
        return f"🌱 TerraPulse is connected to {count} farm(s). Alerts arrive automatically. /settings"
    if command in ("/alerts", "/prefs") and len(parts) == 3 and parts[2] in ("on", "off"):
        try:
            changed = await db.change_preference(session, chat_id,
                category=parts[1], enabled=parts[2] == "on")
        except ValueError:
            changed = 0
        return (f"{parts[1]} alerts {'on' if parts[2] == 'on' else 'off'}." if changed
                else "Choose calendar, weather, or science: /alerts calendar on")
    if command == "/language" and len(parts) == 2:
        try:
            count = await db.change_preference(session, chat_id, locale=parts[1])
        except ValueError:
            count = 0
        return "Language updated." if count else "Available languages: en, hi, kn"
    return "Your TerraPulse alerts arrive automatically. /settings shows optional controls."
