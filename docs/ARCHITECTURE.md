# Architecture

```text
Garmin Connect
    |
    | unofficial, read-only requests on demand
    v
GarminConnectAdapter
    |
    | endpoint-isolated raw responses (transient)
    v
Allowlist normalizers
    |
    +--> SQLite normalized cache
    |
    v
AthleticsService
    |
    | bounded, timestamped results
    v
FastMCP stdio server
    |
    +--> Codex
    +--> Claude Desktop
```

## Components

- `adapter.py`: the only module allowed to call `garminconnect`. It contains no mutation methods.
- `normalizers.py`: converts Garmin-specific shapes to stable, allowlisted records.
- `database.py`: persists normalized daily, performance and workout records; GPS routes are excluded.
- `service.py`: validates ranges, refreshes on demand, coalesces calls, falls back to cache and calculates comparisons/trends.
- `server.py`: declares the read-only MCP tool surface and runs `stdio` transport.
- `cli.py`: local login, diagnostics, resumable backfill and destructive erase commands.

## Data states

Every metric can be represented as one of:

- available with a value;
- supported but absent for the requested period;
- unsupported or unavailable from the Forerunner 55/account;
- cached with a fetch timestamp because Garmin was unavailable.

The service must never infer a missing Garmin metric from another score while presenting it as Garmin-provided data.

## Refresh behavior

There is no scheduler or background worker. Information tools attempt on-demand Garmin refreshes. Identical requests within 60 seconds are coalesced. Completed historical records remain locally available for comparisons and trend calculations.
