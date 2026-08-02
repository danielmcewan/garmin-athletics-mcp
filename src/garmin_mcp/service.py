from __future__ import annotations

import statistics
import threading
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from .adapter import GarminAdapter
from .config import Settings
from .database import Database
from .errors import InvalidRequest, UpstreamUnavailable
from .normalizers import (
    normalize_activity,
    normalize_daily,
    normalize_gear,
    normalize_performance,
    normalize_splits,
    normalize_weather,
    normalize_zones,
)


class AthleticsService:
    def __init__(self, settings: Settings, database: Database, adapter: GarminAdapter):
        self.settings = settings
        self.database = database
        self.adapter = adapter
        self._last_refresh: dict[str, datetime] = {}
        self._refresh_lock = threading.RLock()
        self.database.initialize()

    @staticmethod
    def _parse_day(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise InvalidRequest("Dates must use YYYY-MM-DD format.") from exc

    def _validate_range(self, start: str, end: str) -> tuple[date, date]:
        start_day, end_day = self._parse_day(start), self._parse_day(end)
        if end_day < start_day:
            raise InvalidRequest("end_date must be on or after start_date.")
        if (end_day - start_day).days > self.settings.max_query_days:
            raise InvalidRequest(
                f"A single query may span at most {self.settings.max_query_days} days."
            )
        return start_day, end_day

    def _recently_refreshed(self, key: str) -> bool:
        previous = self._last_refresh.get(key)
        if previous is None:
            return False
        return (datetime.now(UTC) - previous).total_seconds() < self.settings.coalesce_seconds

    def _mark_refreshed(self, key: str) -> None:
        self._last_refresh[key] = datetime.now(UTC)

    @staticmethod
    def _envelope(data: Any, source: str, warning: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "data": data,
            "source": source,
            "served_at": datetime.now(UTC).isoformat(),
        }
        if warning:
            result["warning"] = warning
        return result

    def daily_health(self, day: str) -> dict[str, Any]:
        self._parse_day(day)
        key = f"daily:{day}"
        with self._refresh_lock:
            if not self._recently_refreshed(key):
                try:
                    normalized = normalize_daily(day, self.adapter.fetch_daily(day))
                    self.database.upsert_daily(day, normalized)
                    self._mark_refreshed(key)
                    return self._envelope(normalized, "garmin_live")
                except Exception as exc:
                    cached = self.database.get_daily(day)
                    if cached is None:
                        raise
                    return self._envelope(cached, "local_cache", str(exc))
        cached = self.database.get_daily(day)
        return self._envelope(cached, "local_cache_coalesced")

    def performance(self, day: str) -> dict[str, Any]:
        self._parse_day(day)
        key = f"performance:{day}"
        with self._refresh_lock:
            if not self._recently_refreshed(key):
                try:
                    normalized = normalize_performance(day, self.adapter.fetch_performance(day))
                    self.database.upsert_performance(day, normalized)
                    self._mark_refreshed(key)
                    return self._envelope(normalized, "garmin_live")
                except Exception as exc:
                    cached = self.database.get_performance(day)
                    if cached is None:
                        raise
                    return self._envelope(cached, "local_cache", str(exc))
        return self._envelope(self.database.get_performance(day), "local_cache_coalesced")

    def workouts(self, start: str, end: str, limit: int = 50) -> dict[str, Any]:
        self._validate_range(start, end)
        if not 1 <= limit <= self.settings.max_workouts:
            raise InvalidRequest(f"limit must be between 1 and {self.settings.max_workouts}.")
        key = f"activities:{start}:{end}"
        warning = None
        source = "garmin_live"
        with self._refresh_lock:
            if not self._recently_refreshed(key):
                try:
                    for raw in self.adapter.fetch_activities(start, end):
                        self.database.upsert_activity(normalize_activity(raw))
                    self._mark_refreshed(key)
                except Exception as exc:
                    warning = str(exc)
                    source = "local_cache"
            else:
                source = "local_cache_coalesced"
        data = self.database.list_activities(start, end, limit)
        if not data and warning:
            raise UpstreamUnavailable(warning)
        return self._envelope(data, source, warning)

    def workout_details(self, activity_id: str) -> dict[str, Any]:
        if not activity_id.isdigit():
            raise InvalidRequest("activity_id must contain digits only.")
        key = f"activity:{activity_id}"
        warning = None
        source = "garmin_live"
        with self._refresh_lock:
            if not self._recently_refreshed(key):
                try:
                    raw = self.adapter.fetch_activity_details(activity_id)
                    current = self.database.get_activity(activity_id) or {
                        "activity_id": activity_id
                    }
                    normalized = {**current, **normalize_activity(raw), "activity_id": activity_id}
                    normalized["splits"] = normalize_splits(raw.get("splits"))
                    normalized["typed_splits"] = normalize_splits(raw.get("typed_splits"))
                    normalized["heart_rate_zones"] = normalize_zones(
                        raw.get("heart_rate_zones")
                    )
                    normalized["power_zones"] = normalize_zones(raw.get("power_zones"))
                    normalized["weather"] = normalize_weather(raw.get("weather"))
                    normalized["gear"] = normalize_gear(raw.get("gear"))
                    self.database.upsert_activity(normalized)
                    self._mark_refreshed(key)
                except Exception as exc:
                    warning = str(exc)
                    source = "local_cache"
            else:
                source = "local_cache_coalesced"
        activity = self.database.get_activity(activity_id)
        if activity is None:
            raise UpstreamUnavailable(warning or f"Workout {activity_id} was not found.")
        return self._envelope(activity, source, warning)

    def recovery_snapshot(self, day: str) -> dict[str, Any]:
        health = self.daily_health(day)
        performance = self.performance(day)
        return self._envelope(
            {
                "health": health["data"],
                "performance": performance["data"],
                "interpretation_note": (
                    "Use as training context only; this is not medical advice or a diagnosis."
                ),
            },
            "combined",
            health.get("warning") or performance.get("warning"),
        )

    @staticmethod
    def _median(items: Iterable[float | int | None]) -> float | None:
        values = [float(value) for value in items if value is not None]
        return statistics.median(values) if values else None

    def compare_latest(self, lookback_days: int = 90) -> dict[str, Any]:
        if not 7 <= lookback_days <= 366:
            raise InvalidRequest("lookback_days must be between 7 and 366.")
        end = date.today()
        start = end - timedelta(days=lookback_days)
        workouts = self.workouts(
            start.isoformat(), end.isoformat(), self.settings.max_workouts
        )["data"]
        if not workouts:
            return self._envelope({"latest": None, "comparison": None}, "local_cache")
        latest = workouts[0]
        comparable = [item for item in workouts[1:] if item.get("sport") == latest.get("sport")]
        fields = (
            "distance_m",
            "duration_seconds",
            "average_pace_seconds_per_km",
            "average_heart_rate",
            "elevation_gain_m",
            "aerobic_training_effect",
        )
        medians = {field: self._median(item.get(field) for item in comparable) for field in fields}
        deltas = {
            field: (float(latest[field]) - median)
            if latest.get(field) is not None and median is not None
            else None
            for field, median in medians.items()
        }
        return self._envelope(
            {
                "latest": latest,
                "comparison_group": {
                    "sport": latest.get("sport"),
                    "count": len(comparable),
                    "lookback_days": lookback_days,
                },
                "historical_medians": medians,
                "latest_minus_median": deltas,
            },
            "garmin_and_local_cache",
        )

    def trends(self, start: str, end: str) -> dict[str, Any]:
        self._validate_range(start, end)
        self.daily_health(end)
        self.performance(end)
        workouts = self.workouts(start, end, self.settings.max_workouts)["data"]
        daily = self.database.daily_range(start, end)
        performance = self.database.performance_range(start, end)
        run_workouts = [item for item in workouts if "run" in str(item.get("sport", "")).casefold()]
        return self._envelope(
            {
                "period": {"start": start, "end": end},
                "coverage": {
                    "daily_records": len(daily),
                    "workouts": len(workouts),
                    "running_workouts": len(run_workouts),
                },
                "totals": {
                    "steps": sum(item.get("steps") or 0 for item in daily),
                    "distance_m": sum(item.get("distance_m") or 0 for item in workouts),
                    "duration_seconds": sum(item.get("duration_seconds") or 0 for item in workouts),
                    "running_distance_m": sum(item.get("distance_m") or 0 for item in run_workouts),
                },
                "averages": {
                    "resting_heart_rate": self._median(
                        item.get("resting_heart_rate") for item in daily
                    ),
                    "sleep_seconds": self._median(item.get("sleep_seconds") for item in daily),
                    "stress": self._median(item.get("stress_average") for item in daily),
                    "running_pace_seconds_per_km": self._median(
                        item.get("average_pace_seconds_per_km") for item in run_workouts
                    ),
                },
                "vo2_max_series": [
                    {"date": item.get("date"), "running_vo2_max": item.get("running_vo2_max")}
                    for item in performance
                    if item.get("running_vo2_max") is not None
                ],
            },
            "garmin_and_local_cache",
        )
