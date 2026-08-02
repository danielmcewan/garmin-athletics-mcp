# Garmin Athletics MCP

A private, read-only Model Context Protocol server that gives local Codex and Claude Desktop sessions access to athletics and wellness data from a Garmin Forerunner 55.

## Security model

- Runs locally over MCP `stdio`; it does not open a network port.
- Uses the unofficial `garminconnect` package and can require maintenance if Garmin changes its private endpoints.
- Accepts Garmin credentials only through the interactive admin login command.
- Stores Garmin session tokens under the current Windows user profile, never in MCP configuration.
- Exposes read-only MCP tools. Login, deletion, workout upload, scheduling, and account changes are not tools.
- Stores normalized records in SQLite and does not archive raw Garmin API responses.
- GPS routes are intentionally not fetched, stored, or exposed.

This project provides training context, not medical advice or diagnosis.

## What is implemented

The server exposes these read-only tools:

- `get_daily_health`
- `get_recovery_snapshot`
- `get_performance_metrics`
- `list_workouts`
- `get_workout_details` (splits and metrics only; no GPS)
- `compare_latest_workout`
- `get_athletics_trends`
- `get_recent_athletics_trends`

Every information request attempts a fresh Garmin fetch. Calls for the same data within 60 seconds are coalesced so a single agent response cannot hammer Garmin. If Garmin is unavailable, the response may use the timestamped local cache and includes a warning.

The Forerunner 55 provides running VO2 max, recovery time, race predictions, sleep, Body Battery, stress, heart rate, steps, calories, intensity minutes and workout data. Newer features such as HRV Status and Training Readiness are returned as unavailable when the account does not contain them; the server never fabricates substitutes.

## Installation

Python 3.12 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

This workspace already has Python 3.12, `.venv`, and the development dependencies installed.

## First local login

Close screen-sharing or recording software before entering credentials. From PowerShell in this directory, run:

```powershell
.\.venv\Scripts\garmin-athletics-admin.exe login
```

Enter the Garmin email, password and MFA code only in that local terminal. The command saves session tokens under:

```text
C:\Users\dan\AppData\Local\GarminAthleticsMCP\tokens
```

The password and MFA code are not saved. Do not paste either into Codex, Claude, source files, MCP configuration, or chat.

Check the connection:

```powershell
.\.venv\Scripts\garmin-athletics-admin.exe doctor
```

## Import all eight months of history

After login, run:

```powershell
.\.venv\Scripts\garmin-athletics-admin.exe backfill --days 245 --delay 2
```

The importer is conservative and resumable. Existing complete days are preserved, failures are reported, and rerunning the same command retries gaps. Use `--force` only when you intentionally want to re-fetch completed days.

## Codex configuration

The repository includes [`.codex/config.toml`](.codex/config.toml). It launches this server through the project virtual environment and points it at the shared Windows-local data directory.

After login:

1. Restart Codex or start a new task for this trusted workspace.
2. Confirm the `garmin_athletics` MCP server appears.
3. Ask: `Use Garmin Athletics to show today's health data.`

The OpenAI documentation MCP installer was blocked by Windows while this project was built, so the project configuration should be verified in the live Codex UI after restart.

## Claude Desktop configuration

An example entry is available at [`config/claude_desktop_config.example.json`](config/claude_desktop_config.example.json).

Your existing Claude configuration is:

```text
C:\Users\dan\AppData\Roaming\Claude\claude_desktop_config.json
```

Preserve its existing keys. Add the example's `mcpServers` object at the top level, then fully restart Claude Desktop. Do not replace the entire existing file with the example.

## Useful prompts

- `Use Garmin Athletics to assess my recovery context today. Separate observed data from interpretation.`
- `Compare my latest run with similar runs from the previous 90 days.`
- `Show my running volume, pace and VO2 max trends for the last eight months.`
- `Show the splits and heart-rate zones for workout 123456789.`

## Local administration

Check paths and authentication:

```powershell
.\.venv\Scripts\garmin-athletics-admin.exe doctor
```

Delete the local SQLite database and tokens:

```powershell
.\.venv\Scripts\garmin-athletics-admin.exe erase --yes
```

Deletion is intentionally unavailable through MCP. After erasing, rerun `login` to reconnect.

## Development verification

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -vv
```

The tests use mocked Garmin responses. They do not require credentials or contact Garmin.

## Troubleshooting

- **Authentication required:** rerun the local `login` command.
- **429 or throttling:** stop retrying and wait before using `doctor` again.
- **Unsupported metric:** confirm the Forerunner 55 actually records it; the server returns an availability marker.
- **Cached response:** inspect `source`, `served_at`, `fetched_at`, and `warning` in the tool result.
- **Client cannot start server:** verify the absolute Python path in the client configuration and restart the client.

See [SECURITY.md](SECURITY.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the data boundary and implementation layout.
