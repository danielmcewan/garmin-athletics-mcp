# Security and privacy

## Intended boundary

This project is for one person, on one Windows computer, using local MCP `stdio`. It must not be exposed through Streamable HTTP, SSE, a public port, tunnelling software, or a hosted service without a new threat assessment and explicit redesign.

## Secrets

- Garmin email, password and MFA codes are accepted only by the interactive admin login command.
- The MCP server has no login tool and no credential parameters.
- Only Garmin session tokens persist under the current Windows user profile.
- Tokens must be treated like passwords because they may allow broad Garmin account access.
- `.gitignore` excludes common token, database, environment and local-state files.
- Do not attach token files, databases, or real Garmin payloads to issues or AI chats.

## Data minimization

- Upstream responses are normalized into an allowlisted athletics schema.
- Raw API responses are processed transiently and are not intentionally archived.
- Normalized history is stored in local SQLite until the user runs the local erase command.
- GPS routes are not fetched, stored, normalized, or returned.

## Read-only enforcement

The MCP surface exposes no Garmin mutation operations. In particular, it cannot:

- upload, edit or delete activities;
- create, schedule or delete workouts;
- change devices, account details or privacy settings;
- authenticate or erase local data.

The dependency itself contains write-capable methods, so all Garmin access must continue to pass through `GarminConnectAdapter`. Do not expose the underlying client through a generic passthrough tool.

## Unofficial API risk

`garminconnect` uses undocumented Garmin endpoints. Garmin can change login behavior, schemas, rate limits or endpoint availability without notice. The application therefore:

- pins the tested wrapper version;
- coalesces repeated requests;
- bounds date ranges and result counts;
- uses a timestamped cache fallback;
- isolates optional metrics so one unsupported endpoint does not break daily data;
- requires manual reauthentication after token failure.

Stop repeated login attempts after a 429 or authentication challenge. Wait and retry manually rather than adding automated credential retries.

## Health interpretation

Garmin metrics and MCP outputs are training context, not medical advice or diagnosis. AI clients should distinguish observed measurements from inference and should not make high-stakes medical decisions from this data.

## Reporting an issue

Before sharing logs, remove names, account identifiers, activity IDs, GPS coordinates, timestamps, tokens, error URLs and raw Garmin responses.
