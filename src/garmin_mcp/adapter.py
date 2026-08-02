from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

from garminconnect import Garmin

from .errors import AuthenticationRequired, UpstreamUnavailable


class GarminAdapter(Protocol):
    def fetch_daily(self, day: str) -> dict[str, Any]: ...

    def fetch_performance(self, day: str) -> dict[str, Any]: ...

    def fetch_activities(self, start: str, end: str) -> list[dict[str, Any]]: ...

    def fetch_activity_details(self, activity_id: str) -> dict[str, Any]: ...


class GarminConnectAdapter:
    """Read-only boundary around the unofficial Garmin Connect package."""

    def __init__(self, token_dir: Path):
        self.token_dir = token_dir
        self._client: Garmin | None = None

    def token_source(self) -> Path:
        if self.token_dir.exists() and any(self.token_dir.iterdir()):
            return self.token_dir
        # platformdirs on older builds could create an appauthor/appname duplicate.
        # Read that legacy location once so an existing login is not discarded.
        legacy = self.token_dir.parent / self.token_dir.parent.name / self.token_dir.name
        if legacy.exists() and any(legacy.iterdir()):
            return legacy
        return self.token_dir

    @property
    def client(self) -> Garmin:
        if self._client is not None:
            return self._client
        token_source = self.token_source()
        if not token_source.exists() or not any(token_source.iterdir()):
            raise AuthenticationRequired(
                "Garmin tokens are missing. Run `garmin-athletics-admin login` locally."
            )
        client = Garmin()
        try:
            client.login(str(token_source))
        except Exception as exc:  # library exception hierarchy changes across releases
            raise self._translate(exc) from exc
        self._client = client
        return client

    @classmethod
    def interactive_login(
        cls,
        token_dir: Path,
        email: str,
        password: str,
        prompt_mfa: Callable[[], str],
    ) -> None:
        token_dir.mkdir(parents=True, exist_ok=True)
        client = Garmin(email, password, prompt_mfa=prompt_mfa)
        try:
            client.login(str(token_dir))
        except Exception as exc:
            raise cls._translate(exc) from exc

    @staticmethod
    def _translate(exc: Exception) -> Exception:
        name = type(exc).__name__.casefold()
        message = str(exc)
        if "authentication" in name or "credential" in name or "unauthorized" in message.casefold():
            return AuthenticationRequired(
                "Garmin authentication failed. Re-run `garmin-athletics-admin login` locally."
            )
        return UpstreamUnavailable(f"Garmin Connect request failed: {message}")

    @staticmethod
    def _optional(name: str, call: Callable[[], Any]) -> tuple[str, Any]:
        try:
            return name, call()
        except Exception as exc:
            return name, {"availability": "unavailable", "reason": type(exc).__name__}

    def fetch_daily(self, day: str) -> dict[str, Any]:
        calls: list[tuple[str, Callable[[], Any]]] = [
            ("stats", lambda: self.client.get_stats(day)),
            ("sleep", lambda: self.client.get_sleep_data(day)),
            ("heart_rate", lambda: self.client.get_heart_rates(day)),
            ("stress", lambda: self.client.get_stress_data(day)),
            ("body_battery", lambda: self.client.get_body_battery(day, day)),
            ("hrv", lambda: self.client.get_hrv_data(day)),
            ("training_readiness", lambda: self.client.get_training_readiness(day)),
        ]
        result = dict(self._optional(name, call) for name, call in calls)
        if not isinstance(result.get("stats"), Mapping):
            raise UpstreamUnavailable("Garmin daily summary was unavailable.")
        return result

    def fetch_performance(self, day: str) -> dict[str, Any]:
        calls: list[tuple[str, Callable[[], Any]]] = [
            ("max_metrics", lambda: self.client.get_max_metrics(day)),
            ("training_status", lambda: self.client.get_training_status(day)),
            ("fitness_age", lambda: self.client.get_fitnessage_data(day)),
            ("race_predictions", lambda: self.client.get_race_predictions()),
        ]
        return dict(self._optional(name, call) for name, call in calls)

    def fetch_activities(self, start: str, end: str) -> list[dict[str, Any]]:
        try:
            return self.client.get_activities_by_date(start, end, sortorder="desc")
        except Exception as exc:
            raise self._translate(exc) from exc

    def fetch_activity_details(self, activity_id: str) -> dict[str, Any]:
        calls: list[tuple[str, Callable[[], Any]]] = [
            # maxpoly=0 deliberately prevents downloading GPS polyline data.
            ("details", lambda: self.client.get_activity_details(activity_id, maxpoly=0)),
            ("splits", lambda: self.client.get_activity_splits(activity_id)),
            ("typed_splits", lambda: self.client.get_activity_typed_splits(activity_id)),
            ("heart_rate_zones", lambda: self.client.get_activity_hr_in_timezones(activity_id)),
            ("power_zones", lambda: self.client.get_activity_power_in_timezones(activity_id)),
            ("weather", lambda: self.client.get_activity_weather(activity_id)),
            ("gear", lambda: self.client.get_activity_gear(activity_id)),
        ]
        result = dict(self._optional(name, call) for name, call in calls)
        if not isinstance(result.get("details"), Mapping):
            raise UpstreamUnavailable(f"Garmin activity {activity_id} was unavailable.")
        return result
