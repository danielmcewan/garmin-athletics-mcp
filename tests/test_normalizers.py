from garmin_mcp.normalizers import normalize_activity, normalize_daily

from .fakes import FakeGarminAdapter


def test_daily_normalizer_allowlists_expected_metrics() -> None:
    raw = FakeGarminAdapter().fetch_daily("2026-07-13")
    result = normalize_daily("2026-07-13", raw)
    assert result["steps"] == 12345
    assert result["resting_heart_rate"] == 49
    assert result["sleep_seconds"] == 28800
    assert result["source_device"] == "Garmin Forerunner 55"
    assert "password" not in result


def test_activity_and_route_normalization() -> None:
    fake = FakeGarminAdapter()
    activity = normalize_activity(fake.fetch_activities("2026-07-01", "2026-07-13")[0])
    assert activity["activity_id"] == "1002"
    assert activity["sport"] == "running"
