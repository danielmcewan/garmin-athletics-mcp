from __future__ import annotations

from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

from .adapter import GarminConnectAdapter
from .config import Settings
from .database import Database
from .service import AthleticsService


def create_service() -> AthleticsService:
    settings = Settings.load()
    settings.ensure_directories()
    return AthleticsService(
        settings,
        Database(settings.database_path),
        GarminConnectAdapter(settings.token_dir),
    )


service = create_service()
mcp = FastMCP(
    "Garmin Athletics",
    instructions=(
        "Read-only access to one user's local Garmin Forerunner 55 athletics data. "
        "Never claim unsupported metrics are available. Treat recovery outputs as "
        "training context, "
        "not medical advice. GPS routes are not fetched or exposed."
    ),
    json_response=True,
)


@mcp.tool()
def get_daily_health(day: str = "today") -> dict:
    """Fetch sleep, heart rate, Body Battery, stress, steps, calories and related data for a day."""
    resolved = date.today().isoformat() if day == "today" else day
    return service.daily_health(resolved)


@mcp.tool()
def get_recovery_snapshot(day: str = "today") -> dict:
    """Fetch daily recovery and available performance context. Not medical advice."""
    resolved = date.today().isoformat() if day == "today" else day
    return service.recovery_snapshot(resolved)


@mcp.tool()
def get_performance_metrics(day: str = "today") -> dict:
    """Fetch available VO2 max, recovery, race-prediction and training-status metrics."""
    resolved = date.today().isoformat() if day == "today" else day
    return service.performance(resolved)


@mcp.tool()
def list_workouts(start_date: str, end_date: str, limit: int = 50) -> dict:
    """List read-only normalized workout summaries in a bounded date range."""
    return service.workouts(start_date, end_date, limit)


@mcp.tool()
def get_workout_details(activity_id: str) -> dict:
    """Fetch workout splits and details without downloading GPS route data."""
    return service.workout_details(activity_id)


@mcp.tool()
def compare_latest_workout(lookback_days: int = 90) -> dict:
    """Compare the latest workout with median values from similar workouts."""
    return service.compare_latest(lookback_days)


@mcp.tool()
def get_athletics_trends(start_date: str, end_date: str) -> dict:
    """Summarize training volume, pace, wellness coverage, and available VO2 max history."""
    return service.trends(start_date, end_date)


@mcp.tool()
def get_recent_athletics_trends(days: int = 30) -> dict:
    """Convenience trend summary for the last 7 to 366 days."""
    if not 7 <= days <= 366:
        raise ValueError("days must be between 7 and 366")
    end = date.today()
    start = end - timedelta(days=days)
    return service.trends(start.isoformat(), end.isoformat())


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
