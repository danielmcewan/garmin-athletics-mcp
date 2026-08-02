from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    day TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    day TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id TEXT PRIMARY KEY,
                    start_time_local TEXT,
                    sport TEXT,
                    data_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_activities_start ON activities(start_time_local);
                CREATE INDEX IF NOT EXISTS idx_activities_sport ON activities(sport);
                """
            )

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()

    def upsert_daily(self, day: str, data: dict[str, Any]) -> None:
        self._upsert_keyed("daily_metrics", "day", day, data)

    def upsert_performance(self, day: str, data: dict[str, Any]) -> None:
        self._upsert_keyed("performance_metrics", "day", day, data)

    def _upsert_keyed(self, table: str, key_column: str, key: str, data: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute(
                f"INSERT INTO {table} ({key_column}, data_json, fetched_at) VALUES (?, ?, ?) "
                f"ON CONFLICT({key_column}) DO UPDATE SET data_json=excluded.data_json, "
                "fetched_at=excluded.fetched_at",
                (key, json.dumps(data, separators=(",", ":")), self.now()),
            )

    def get_daily(self, day: str) -> dict[str, Any] | None:
        return self._get_keyed("daily_metrics", "day", day)

    def get_performance(self, day: str) -> dict[str, Any] | None:
        return self._get_keyed("performance_metrics", "day", day)

    def _get_keyed(self, table: str, key_column: str, key: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                f"SELECT data_json, fetched_at FROM {table} WHERE {key_column}=?", (key,)
            ).fetchone()
        if row is None:
            return None
        data = json.loads(row["data_json"])
        data["fetched_at"] = row["fetched_at"]
        return data

    def upsert_activity(self, activity: dict[str, Any]) -> None:
        activity_id = activity.get("activity_id")
        if not activity_id:
            return
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO activities
                    (activity_id, start_time_local, sport, data_json, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(activity_id) DO UPDATE SET
                    start_time_local=excluded.start_time_local,
                    sport=excluded.sport,
                    data_json=excluded.data_json,
                    fetched_at=excluded.fetched_at
                """,
                (
                    str(activity_id),
                    activity.get("start_time_local"),
                    str(activity.get("sport") or "unknown"),
                    json.dumps(activity, separators=(",", ":")),
                    self.now(),
                ),
            )

    def get_activity(self, activity_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT data_json, fetched_at FROM activities WHERE activity_id=?", (activity_id,)
            ).fetchone()
        if row is None:
            return None
        data = json.loads(row["data_json"])
        data["fetched_at"] = row["fetched_at"]
        return data

    def list_activities(self, start: str, end: str, limit: int) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT data_json, fetched_at FROM activities
                WHERE substr(start_time_local, 1, 10) BETWEEN ? AND ?
                ORDER BY start_time_local DESC LIMIT ?
                """,
                (start, end, limit),
            ).fetchall()
        result = []
        for row in rows:
            item = json.loads(row["data_json"])
            item["fetched_at"] = row["fetched_at"]
            result.append(item)
        return result

    def daily_range(self, start: str, end: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT data_json FROM daily_metrics WHERE day BETWEEN ? AND ? ORDER BY day",
                (start, end),
            ).fetchall()
        return [json.loads(row["data_json"]) for row in rows]

    def performance_range(self, start: str, end: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT data_json FROM performance_metrics WHERE day BETWEEN ? AND ? ORDER BY day",
                (start, end),
            ).fetchall()
        return [json.loads(row["data_json"]) for row in rows]
