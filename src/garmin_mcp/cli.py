from __future__ import annotations

import argparse
import getpass
import shutil
import sys
import time
from datetime import date, timedelta

from .adapter import GarminConnectAdapter
from .config import Settings
from .database import Database
from .service import AthleticsService


def _service(settings: Settings) -> AthleticsService:
    settings.ensure_directories()
    return AthleticsService(
        settings,
        Database(settings.database_path),
        GarminConnectAdapter(settings.token_dir),
    )


def login(settings: Settings) -> int:
    print("Garmin credentials are used only for this local interactive login and are not saved.")
    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")
    GarminConnectAdapter.interactive_login(
        settings.token_dir,
        email,
        password,
        lambda: getpass.getpass("Garmin MFA code: ").strip(),
    )
    print(f"Login succeeded. Tokens saved under: {settings.token_dir}")
    return 0


def backfill(settings: Settings, days: int, delay: float, force: bool = False) -> int:
    service = _service(settings)
    database = service.database
    end = date.today()
    start = end - timedelta(days=days - 1)
    print(f"Backfilling {start.isoformat()} through {end.isoformat()}.")
    service.workouts(start.isoformat(), end.isoformat(), settings.max_workouts)
    current = start
    failures = 0
    skipped_existing = 0
    while current <= end:
        day = current.isoformat()
        if not force and database.get_daily(day) and database.get_performance(day):
            skipped_existing += 1
            current += timedelta(days=1)
            continue
        try:
            service.daily_health(day)
            service.performance(day)
            print(f"  imported {day}")
        except Exception as exc:
            failures += 1
            print(f"  skipped {day}: {exc}", file=sys.stderr)
        current += timedelta(days=1)
        if current <= end:
            time.sleep(delay)
    print(
        f"Backfill complete: {skipped_existing} existing day(s) preserved, "
        f"{failures} day(s) failed. Re-run to retry failed days."
    )
    return 0 if failures == 0 else 2


def doctor(settings: Settings) -> int:
    adapter = GarminConnectAdapter(settings.token_dir)
    token_source = adapter.token_source()
    print(f"Data directory: {settings.home}")
    database_status = "present" if settings.database_path.exists() else "missing"
    print(f"Database: {settings.database_path} ({database_status})")
    token_files = list(token_source.glob("*")) if token_source.exists() else []
    print(f"Token store: {token_source} ({len(token_files)} file(s))")
    if not token_files:
        print("Next step: run `garmin-athletics-admin login`.")
        return 1
    try:
        today = date.today().isoformat()
        result = _service(settings).daily_health(today)
        print(f"Garmin connection: OK ({result['source']})")
        return 0
    except Exception as exc:
        print(f"Garmin connection: FAILED: {exc}", file=sys.stderr)
        return 2


def erase(settings: Settings, confirmed: bool) -> int:
    if not confirmed:
        print("Refusing to erase data without --yes.", file=sys.stderr)
        return 2
    if settings.home.exists():
        shutil.rmtree(settings.home)
    print(f"Deleted local Garmin MCP data and tokens from {settings.home}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Administer the local Garmin Athletics MCP server."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("login", help="Interactively authenticate and store Garmin tokens.")
    fill = sub.add_parser("backfill", help="Import historical wellness, performance and workouts.")
    fill.add_argument("--days", type=int, default=245, help="Days to import (default: 245).")
    fill.add_argument("--delay", type=float, default=2.0, help="Delay between days (default: 2s).")
    fill.add_argument("--force", action="store_true", help="Re-fetch already cached days.")
    sub.add_parser("doctor", help="Check paths, tokens and Garmin connectivity.")
    wipe = sub.add_parser(
        "erase", help="Delete local database and tokens; never exposed through MCP."
    )
    wipe.add_argument("--yes", action="store_true", help="Confirm destructive local deletion.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.load()
    if args.command == "login":
        code = login(settings)
    elif args.command == "backfill":
        if not 1 <= args.days <= 3660 or not 0 <= args.delay <= 60:
            raise SystemExit("--days must be 1..3660 and --delay must be 0..60")
        code = backfill(settings, args.days, args.delay, args.force)
    elif args.command == "doctor":
        code = doctor(settings)
    else:
        code = erase(settings, args.yes)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
