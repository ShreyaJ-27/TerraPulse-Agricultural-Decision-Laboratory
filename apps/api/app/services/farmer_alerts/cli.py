"""Run a self-hosted Telegram alerts worker. No subscriptions or paid providers."""
from __future__ import annotations
import argparse
import asyncio
import json
import os

from app.core.event_loop import new_event_loop

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
    if args.live and os.environ.get("TERRAPULSE_TELEGRAM_ENABLED") != "1":
        parser.error("Set TERRAPULSE_TELEGRAM_ENABLED=1 after verifying the bot and recipient consent.")
    telegram = TelegramClient() if args.live else None
    with asyncio.Runner(loop_factory=new_event_loop) as runner:
        if args.once:
            print(json.dumps(runner.run(run_cycle(SessionFactory, telegram, live=args.live, profiles=profiles))))
        else:
            runner.run(forever(SessionFactory, telegram, live=args.live, interval_seconds=args.interval, profiles=profiles))


if __name__ == "__main__":
    main()
