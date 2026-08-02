from garmin_mcp.config import Settings
from garmin_mcp.database import Database
from garmin_mcp.service import AthleticsService

from .fakes import FakeGarminAdapter


def make_service(tmp_path, coalesce_seconds: int = 60):
    settings = Settings(
        home=tmp_path,
        token_dir=tmp_path / "tokens",
        database_path=tmp_path / "garmin.sqlite3",
        coalesce_seconds=coalesce_seconds,
    )
    fake = FakeGarminAdapter()
    return AthleticsService(settings, Database(settings.database_path), fake), fake


def test_daily_live_then_coalesced_cache(tmp_path) -> None:
    service, fake = make_service(tmp_path)
    first = service.daily_health("2026-07-13")
    second = service.daily_health("2026-07-13")
    assert first["source"] == "garmin_live"
    assert second["source"] == "local_cache_coalesced"
    assert fake.daily_calls == 1


def test_cache_fallback_is_timestamped(tmp_path) -> None:
    service, fake = make_service(tmp_path, coalesce_seconds=0)
    service.daily_health("2026-07-13")
    fake.fail = True
    result = service.daily_health("2026-07-13")
    assert result["source"] == "local_cache"
    assert "upstream offline" in result["warning"]
    assert result["data"]["fetched_at"]


def test_workout_details_exclude_route_data(tmp_path) -> None:
    service, _ = make_service(tmp_path)
    service.workouts("2026-07-01", "2026-07-13")
    result = service.workout_details("1002")
    assert "precise_route" not in result["data"]
    assert "location_privacy_notice" not in result["data"]


def test_latest_comparison_and_trends(tmp_path, monkeypatch) -> None:
    service, _ = make_service(tmp_path)
    comparison = service.compare_latest(90)
    assert comparison["data"]["comparison_group"]["count"] == 1
    assert comparison["data"]["latest_minus_median"]["average_pace_seconds_per_km"] == -12

    result = service.trends("2026-07-01", "2026-07-13")
    assert result["data"]["coverage"]["workouts"] == 2
    assert result["data"]["totals"]["distance_m"] == 10000
