# Garmin Health MCP Server Brainstorm

## Session Metadata

* Date: 2026-07-13
* Project: Athletics
* Current goal: Define a secure MCP server that lets AI agents read Garmin health and workout data.
* Status: Discovery — single-user scope confirmed; access mechanism and freshness requirements remain open.

## Short Summary

The proposed system will expose selected Garmin-derived health and workout data to AI agents through read-only MCP tools. The smallest sensible first version is one user, local/private operation, a narrow set of metrics, and no write-back or coaching actions. Garmin data access may require Garmin Health API approval and OAuth credentials; alternative export or local-sync routes remain to be evaluated.

## Key Decisions

* Decision: Start with read-only MCP access.
* Reason: Health data is sensitive, and write/autonomous behavior is unnecessary for the first useful version.
* Confidence: Medium — inferred pending user confirmation.
* Dependencies: Intended users, deployment location, Garmin access route, desired metrics.
* Decision: Treat an export-driven proof of concept as the default until business/multi-user scope is confirmed.
* Reason: Garmin documents the official Connect Developer Program as business-only and approval-based, while official account, activity, and daily wellness exports are available to individual users.
* Confidence: High for the access distinction; final route still depends on the user's scope and freshness requirements.
* Dependencies: Whether the project is personal-only and whether automatic near-real-time sync is essential.
* Decision: Version one is for the user's personal Garmin account only.
* Reason: Direct user confirmation.
* Confidence: High.
* Dependencies: Personal-account authentication approach and acceptable reliability/security tradeoffs.
* Decision: The MCP server and consuming AI agents will run on the same Windows computer.
* Reason: Direct user confirmation.
* Confidence: High.
* Dependencies: MCP client configuration and Windows-local token storage.
* Decision: Both Codex and Claude Desktop must connect to the MCP server.
* Reason: Direct user confirmation.
* Confidence: High.
* Dependencies: Separate client configuration examples pointing to the same Python entry point and data directories.
* Decision: Version one should cover all available athletics-related Garmin data, including wellness/recovery metrics, workouts, training metrics, and VO2 max.
* Reason: Direct user confirmation.
* Confidence: High on desired scope; exact field availability depends on the watch and Garmin account data.
* Dependencies: Watch model, wrapper endpoint availability, normalized schemas, bounded queries, and location-data decision.
* Decision: The source device is a Garmin Forerunner 55.
* Reason: Direct user confirmation.
* Confidence: High.
* Dependencies: The MCP must return explicit unavailable/null results for metrics the Forerunner 55 does not produce.
* Decision: Precise workout GPS routes and coordinates may be exposed to Codex and Claude Desktop.
* Reason: Direct user confirmation after the location-privacy risk was explained.
* Confidence: High.
* Dependencies: Data remains local; route data should be isolated in explicit route/detail tools and omitted from ordinary summaries.
* Decision: Garmin data refreshes only when the user asks an AI client for Garmin information.
* Reason: Direct user confirmation.
* Confidence: High.
* Dependencies: On-demand request coalescing, conservative endpoint usage, and a stale-cache fallback when Garmin is unavailable.
* Decision: Initial setup will import all available Garmin history, currently approximately eight months.
* Reason: Direct user confirmation; the user has owned the watch for eight months.
* Confidence: High.
* Dependencies: Batched, resumable backfill with rate limiting and checkpointing.
* Decision: Garmin credentials and MFA codes are used only in an interactive local bootstrap; only resulting authentication tokens persist.
* Reason: Direct user confirmation after the security tradeoff was explained.
* Confidence: High.
* Dependencies: Token directory protected by the Windows user account, token path excluded from Git, and a manual reauthentication command.
* Decision: Retain normalized Garmin history indefinitely in local SQLite, do not archive raw API responses, and provide a local cache/token erase command.
* Reason: User accepted the recommended retention policy.
* Confidence: High.
* Dependencies: Git exclusions, documented storage paths, schema migrations, and an erase command unavailable to MCP clients.
* Decision: Optimize the MCP around three initial use cases: daily recovery/training guidance, comparison of the latest workout with similar history, and long-term fitness/training trends.
* Reason: User accepted the recommended use cases.
* Confidence: High.
* Dependencies: Daily summary aggregation, comparable-activity selection, trend calculations, provenance timestamps, and clear non-medical language.
* Decision: Discovery is complete and the specification is ready for implementation, pending explicit build approval.
* Reason: The important scope, deployment, data, authentication, retention, freshness, privacy, and outcome branches are resolved.
* Confidence: High.
* Dependencies: User authorization to implement.

## Current Understanding

The user owns a Garmin watch and wants AI agents to access health statistics and workouts. No existing application files or architecture are present in the workspace. A likely MVP would ingest Garmin exports or an approved Garmin API feed, normalize records, store/cache them privately, and expose explicit MCP tools such as recent workouts, daily health summary, sleep, heart rate, and trends.

Verified official access facts as of 2026-07-13:

* The Garmin Connect Developer Program provides separate Health and Activity APIs and is described by Garmin as business-only and approval-based.
* Program APIs use OAuth 2.0; Garmin's published authorization specification uses PKCE.
* The Health API covers daily metrics including steps, intensity minutes, sleep, calories, heart rate, stress, Pulse Ox, Body Battery, body composition, respiration, and blood pressure.
* The Activity API provides activity summaries/details and FIT, GPX, or TCX files.
* Garmin supports event-driven push/ping-pull integration after users consent and sync devices to Garmin Connect.
* For individuals, Garmin officially supports export of original activities (usually FIT), summary CSVs, daily wellness FIT data, and complete account data exports.

Official references:

* https://developer.garmin.com/gc-developer-program/overview/
* https://developer.garmin.com/gc-developer-program/program-faq/
* https://developer.garmin.com/gc-developer-program/health-api/
* https://developer.garmin.com/gc-developer-program/activity-api/
* https://developerportal.garmin.com/sites/default/files/OAuth2PKCE.pdf
* https://support.garmin.com/en-US/?faq=W1TvTPW8JZ6LfJSfK512Q8

Verified unofficial-wrapper facts as of 2026-07-13:

* The `garminconnect` PyPI package is actively maintained; version 0.3.6 was released on 2026-06-14 and requires Python 3.12 or newer.
* It exposes health, activity, workout, device, and historical-data methods through undocumented Garmin Connect endpoints.
* Initial authentication uses Garmin's mobile SSO flow and supports MFA.
* The package exchanges the login result for access/refresh tokens, stores them by default under `~/.garminconnect/garmin_tokens.json`, and refreshes them while the refresh token remains valid.
* A full credential login is needed again if the refresh token expires or is revoked.
* Source: https://pypi.org/project/garminconnect/

Provisional architecture if the unofficial route is accepted:

1. A separate interactive bootstrap command performs the first login and MFA locally.
2. The MCP runtime loads stored tokens only; Garmin credentials are never MCP tool arguments and are not exposed to the model.
3. The runtime uses a read-only allowlist of Garmin methods, strict date-range limits, request throttling, and a local SQLite cache.
4. MCP initially uses local stdio transport so no health-data service is exposed on the network.
5. GPS/location fields are omitted or reduced unless explicitly enabled.
6. Authentication failures stop safely and request local reauthentication rather than accepting secrets through chat.

Confirmed deployment boundary: Windows local-only, single user, stdio transport, no externally reachable service.

Verified Forerunner 55 capability notes from the January 2026 owner manual:

* Available: running VO2 max estimate, recovery time, predicted 5K/10K/half-marathon/marathon times, daily suggested running workouts, sleep duration/stages/movement, Body Battery, stress, wrist heart rate, steps, distance, calories, and intensity minutes.
* The manual does not list the newer Garmin features named `HRV Status` or `Training Readiness`; these should be represented as unsupported unless actual Garmin Connect responses prove otherwise.
* Body Battery internally uses heart-rate variability, but that does not imply the account exposes the separate newer HRV Status metric.
* Official manual: https://www8.garmin.com/manuals/webhelp/GUID-3A791586-B59F-4B37-B9C5-5A41F8C6BE0B/EN-GB/Forerunner_55_OM_EN-US.pdf

## Q&A Log

* Question: Is this only for your personal Garmin account, or should other people connect their accounts?
* Why it mattered: It determines whether a personal ingestion approach is sufficient or a multi-user, approved OAuth integration is required.
* Recommended/default answer: Personal account only for version one.
* User answer: Only for myself.
* Extracted decision or implication: Design a single-user private server; multi-user consent, tenancy, and Garmin business API onboarding are out of scope.
* Question: Will the AI agents and MCP server run on the same Windows computer, or must remote agents reach it?
* Why it mattered: Local-only operation avoids exposing Garmin tokens and health data through a hosted network service.
* Recommended/default answer: Run everything locally on the Windows computer for version one.
* User answer: Run on this same Windows computer.
* Extracted decision or implication: Use local stdio MCP transport, no public URL, no inbound port, and Windows-local token/data storage.
* Question: Which AI application should connect first: Codex, Claude Desktop, or both?
* Why it mattered: Each client has its own MCP configuration surface, even though they can share one server implementation.
* Recommended/default answer: Both, with Codex used for initial testing.
* User answer: Both.
* Extracted decision or implication: Build one stdio server and document/configure both clients against the same executable command.
* Question: Which Garmin data must version one expose?
* Why it mattered: The chosen data surface determines the Garmin endpoints, normalized schemas, caching policy, privacy boundary, and test fixtures.
* Recommended/default answer: Sleep, Body Battery, heart rate, HRV, stress, steps, calories, training readiness/status, and recent workout summaries/details.
* User answer: All recommended metrics plus workouts, VO2 max, and everything athletics-related.
* Extracted decision or implication: Provide broad read-only athletics coverage through grouped MCP tools, while excluding account administration and all write operations.
* Question: What exact Garmin watch model do you use?
* Why it mattered: Garmin metrics and workout fields vary significantly by watch model.
* Recommended/default answer: The full model name shown in Garmin Connect.
* User answer: Forerunner 55.
* Extracted decision or implication: Build schemas and tests around Forerunner 55 data, while handling unsupported metrics without errors or fabricated values.
* Question: Should Codex and Claude receive precise workout GPS routes and coordinates?
* Why it mattered: Route data can reveal the user's home, workplace, and routines.
* Recommended/default answer: Hide precise coordinates by default and expose non-location workout analytics.
* User answer: Yes.
* Extracted decision or implication: Permit precise coordinates in explicit route-level MCP responses while keeping them local and out of default workout summaries.
* Question: How fresh must Garmin data be after the watch syncs?
* Why it mattered: Fetching Garmin on every interaction affects latency, rate-limit risk, account challenges, and cache behavior.
* Recommended/default answer: Fifteen-minute health cache, workout checks on request, permanent completed-workout cache, and an explicit refresh tool.
* User answer: Refresh only when information is requested.
* Extracted decision or implication: No background jobs or scheduled polling; information tools perform an on-demand refresh and fall back to clearly timestamped cached data on upstream failure.
* Question: How much historical Garmin data should be imported during initial setup?
* Why it mattered: Historical depth controls initial API volume, cache size, trend coverage, and throttling risk.
* Recommended/default answer: All workout history and the latest 12 months of daily wellness data.
* User answer: All history; the watch has been owned for eight months.
* Extracted decision or implication: Backfill the complete available account history in conservative, resumable batches.
* Question: Is the user comfortable entering Garmin email, password, and MFA once locally, persisting only tokens, and manually reauthenticating when necessary?
* Why it mattered: This prevents Garmin credentials from entering MCP configuration, model context, source control, or long-lived project files.
* Recommended/default answer: Yes; store tokens only and require manual reauthentication.
* User answer: Yes.
* Extracted decision or implication: Implement separate interactive login and reauthentication commands; the stdio MCP process loads tokens and never accepts account credentials.
* Question: How should locally cached Garmin data be retained?
* Why it mattered: Long-term normalized history enables useful trends, while raw response archives duplicate sensitive health and location data.
* Recommended/default answer: Retain normalized history indefinitely, retain no raw response archive, and provide a local command to erase cache and tokens.
* User answer: Use the recommended policy.
* Extracted decision or implication: Persist normalized SQLite records until local deletion; process upstream JSON transiently; keep destructive cleanup outside the MCP tool surface.
* Question: What are the three most important questions the agents should answer?
* Why it mattered: Tool design should serve real decisions rather than mirror undocumented Garmin endpoints.
* Recommended/default answer: Daily recovery/training guidance; latest-workout comparison; fitness, VO2 max, pace, volume, and consistency trends.
* User answer: The recommended three are good.
* Extracted decision or implication: Center tools and normalized outputs on daily readiness context, comparable workout analysis, and longitudinal athletics trends.

## Assumptions

* Automatic/live freshness is likely important, based on the user's interest in an unofficial Garmin Connect wrapper, but is not yet confirmed.
* The MCP server should be read-only.
* The user wants health/workout analysis, not medical diagnosis.
* Local/private hosting is preferable unless remote agent access is required.

## Open Questions

* Which desired fields are available from the Forerunner 55 and which require a newer device or external sensor?
* Does the user already have Garmin developer/Health API approval?
* What retention, privacy, and deletion rules are required?
* Does the user want implementation to begin now?

## Risks / Flags

* Garmin may not issue unrestricted personal API keys; official access can require program approval and OAuth credentials.
* Unofficial Garmin Connect libraries can break, trigger authentication challenges, or conflict with service expectations.
* Health and location data are highly sensitive; broad agent access creates privacy and prompt-injection/exfiltration risk.
* “Health stats and workouts” hides several separate datasets and permission decisions.
* An export-only MVP is not automatically live; a separate authorized ingestion mechanism would be needed for continuous freshness.
* The unofficial wrapper imitates Garmin's app/web behavior and can fail when Garmin changes login flows, endpoints, schemas, or rate limits.
* Persisted tokens can provide broad account access and must be protected like passwords.
* The wrapper includes write-capable methods; the MCP layer must not expose upload, scheduling, update, or delete operations in version one.

## Action Items

* Verify current official Garmin API access and credential requirements.
* Confirm the exact MCP clients that must be configured.
* Select the smallest viable data set and deployment model.
* Define normalized athletics data groups and bounded MCP tools.
* On approval, scaffold the Python project, implement authentication bootstrap, Garmin adapter, SQLite cache, read-only MCP tools, tests, and Codex/Claude configuration guides.
* Produce an architecture and credential checklist only after these branches are resolved.

## Suggested Doc / Skill Updates

* Add a project README and security/data-handling guide after the design is approved.

## Implementation Checkpoint

* Build authorized by user on 2026-07-13.
* Python 3.12.10 installed because current `garminconnect` requires Python 3.12 or newer.
* Local virtual environment and pinned project dependencies installed.
* Read-only FastMCP stdio server implemented for Codex and Claude Desktop.
* Interactive login, doctor, resumable eight-month backfill, and local erase commands implemented outside the MCP surface.
* Garmin adapter, endpoint-isolated normalization, SQLite cache, on-demand refresh/coalescing, cache fallback, GPS opt-in, workout comparison, and trend aggregation implemented.
* Project Codex configuration, Claude Desktop merge example, README, security guide, and architecture guide created.
* Verification passed: dependency check, compilation, Ruff lint, eight unit/protocol tests, CLI startup, and secret scan.
* Real Garmin login and backfill remain intentionally user-interactive because credentials and MFA must not enter chat or automated tool calls.
* Follow-up decision: Remove GPS route functionality entirely because it is unnecessary and token-expensive. Workout detail requests now set `maxpoly=0`; the MCP does not accept or return route coordinates, and new route data is not stored.
