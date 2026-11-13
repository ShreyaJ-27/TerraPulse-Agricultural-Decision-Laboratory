"""Run a self-hosted Telegram alerts worker. No subscriptions or paid providers."""
from __future__ import annotations
import argparse
import asyncio
import json
import os

from .telegram import TelegramClient
from .worker import forever, run_cycle


def main() -> None:
    parser = argparse.ArgumentParser(description="TerraPulse agricultural calendar + Telegram")
    parser.add_argument("--live", action="store_true", help="Actually send queued Telegram messages")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--interval", type=int, default=600, help="Seconds between cycles (60..3600)")
    args = parser.parse_args()
    from app.core.db import SessionFactory
    from .profile_loader import load_profiles_file
    profiles = load_profiles_file(os.environ.get("TERRAPULSE_CALENDAR_PROFILES_FILE"))
    telegram = TelegramClient()
    if args.once:
        print(json.dumps(asyncio.run(run_cycle(SessionFactory, telegram, live=args.live, profiles=profiles))))
    else:
        asyncio.run(forever(SessionFactory, telegram, live=args.live, interval_seconds=args.interval, profiles=profiles))


if __name__ == "__main__":
    main()
