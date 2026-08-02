from garmin_mcp.database import Database


def test_database_roundtrip(tmp_path) -> None:
    database = Database(tmp_path / "garmin.sqlite3")
    database.initialize()
    database.upsert_daily("2026-07-13", {"date": "2026-07-13", "steps": 100})
    database.upsert_performance("2026-07-13", {"date": "2026-07-13", "running_vo2_max": 50})
    database.upsert_activity(
        {
            "activity_id": "42",
            "start_time_local": "2026-07-13 07:00:00",
            "sport": "running",
            "distance_m": 5000,
        }
    )

    assert database.get_daily("2026-07-13")["steps"] == 100
    assert database.get_performance("2026-07-13")["running_vo2_max"] == 50
    assert database.get_activity("42")["distance_m"] == 5000
