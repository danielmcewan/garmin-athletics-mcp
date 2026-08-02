from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Resolved local paths and conservative upstream limits."""

    home: Path
    token_dir: Path
    database_path: Path
    coalesce_seconds: int = 60
    max_query_days: int = 366
    max_workouts: int = 100

    @classmethod
    def load(cls) -> Settings:
        override = os.getenv("GARMIN_MCP_HOME")
        if override:
            home = Path(override).expanduser()
        else:
            local_app_data = Path(
                os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            )
            home = local_app_data / "GarminAthleticsMCP"
        return cls(
            home=home,
            token_dir=home / "tokens",
            database_path=home / "garmin.sqlite3",
        )

    def ensure_directories(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.token_dir.mkdir(parents=True, exist_ok=True)
