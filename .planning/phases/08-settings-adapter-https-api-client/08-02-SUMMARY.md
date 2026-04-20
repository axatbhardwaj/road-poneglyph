---
phase: 08-settings-adapter-https-api-client
plan: 02
subsystem: api
tags: [https, urllib, ssl, bearer-token, rest-api, satisfactory]

requires:
  - phase: 08-01
    provides: "INI adapter wired into GAMES['satisfactory']"
provides:
  - "road_poneglyph/satisfactory_api.py HTTPS API client module"
  - "save command for Satisfactory (road-poneglyph satisfactory save)"
  - "Enhanced status with API health check"
  - "Token caching at ~/.config/road-poneglyph/satisfactory-api-token (0600)"
affects: [08-03, 09-release]

tech-stack:
  added: []
  patterns: ["stdlib-only HTTPS client: urllib.request + ssl + json", "ssl.create_default_context() with check_hostname=False for self-signed certs", "lazy imports in Typer commands to avoid import-time side effects"]

key-files:
  created: [road_poneglyph/satisfactory_api.py, tests/test_satisfactory_api.py]
  modified: [road_poneglyph/main.py]

key-decisions:
  - "stdlib only (urllib.request + ssl + json) -- no new pip dependencies"
  - "Self-signed cert accepted via ssl.create_default_context() with check_hostname=False + verify_mode=CERT_NONE"
  - "Token file at ~/.config/road-poneglyph/satisfactory-api-token with mode 0600"
  - "Lazy imports inside command functions to avoid import-time network dependencies"

patterns-established:
  - "HTTPS API client pattern: _build_request helper + _ssl_context for self-signed certs"
  - "Token caching pattern: save_token/load_token with 0600 permissions"

requirements-completed: [API-02, API-03, API-04, API-05]

duration: 3min
completed: 2026-04-20
---

# Phase 8 Plan 02: HTTPS API client + save verb + enhanced status Summary

**Minimal stdlib HTTPS API client for Satisfactory server with PasswordLogin token caching, save command, and health check in status**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-20T21:01:51Z
- **Completed:** 2026-04-20T21:04:51Z
- **Tasks:** 2 (Task 1 TDD, Task 2 auto)
- **Files modified:** 3

## Accomplishments
- Created road_poneglyph/satisfactory_api.py with health_check, password_login, save_game
- Token caching at ~/.config/road-poneglyph/satisfactory-api-token with 0600 permissions
- Added `road-poneglyph satisfactory save [name]` command with interactive PasswordLogin flow
- Enhanced `road-poneglyph satisfactory status` with API health check (graceful fallback)
- 6 unit tests for request construction and token caching

## Task Commits

Each task was committed atomically:

1. **Task 1 + Task 2: API client + save + enhanced status** - `d90786e` (feat)

## Files Created/Modified
- `road_poneglyph/satisfactory_api.py` - HTTPS API client (health_check, password_login, save_game, token caching)
- `road_poneglyph/main.py` - save command + enhanced status with health check
- `tests/test_satisfactory_api.py` - 6 unit tests for pure helpers

## Decisions Made
- Used stdlib only (urllib.request + ssl + json) per project rules -- no new dependencies
- Self-signed cert handling via ssl.create_default_context() with disabled verification
- Lazy imports inside Typer command functions to avoid import-time failures
- Timeouts: 5s for health_check, 10s for login, 30s for save_game

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - token is obtained interactively on first `save` command via PasswordLogin.

## Next Phase Readiness
- API client ready for ExecStop wiring in 08-03
- save_game function available for pre-shutdown save call

---
*Phase: 08-settings-adapter-https-api-client*
*Completed: 2026-04-20*
