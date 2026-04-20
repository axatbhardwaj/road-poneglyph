---
phase: 08-settings-adapter-https-api-client
plan: 03
subsystem: systemd
tags: [systemd, exec-stop, curl, pre-shutdown-save, golden-recapture]

requires:
  - phase: 08-02
    provides: "satisfactory_api.py with save_game + token caching"
provides:
  - "ExecStop in satisfactory.service.template calling SaveGame API before SIGINT"
  - "Recaptured golden file matching new template shape"
  - "Fault-tolerant pre-shutdown save (missing token or API failure gracefully handled)"
affects: [09-release]

tech-stack:
  added: []
  patterns: ["ExecStop curl one-liner with conditional token read and --max-time timeout", "Golden recapture workflow: update template -> update fixture -> recapture -> verify byte-identical"]

key-files:
  created: []
  modified: [road_poneglyph/templates/satisfactory.service.template, road_poneglyph/main.py, tests/golden/satisfactory.service.v0_3_0, tests/test_satisfactory_golden.py]

key-decisions:
  - "Use curl in ExecStop instead of Python (simpler, no dependency on road-poneglyph being installed for service user)"
  - "Conditional token read: if [ -f token_path ] -- skip save if no token cached"
  - "sleep 2 after save allows disk flush before systemd sends SIGINT"
  - "No kill -INT $MAINPID needed -- systemd sends KillSignal=SIGINT after ExecStop completes"
  - "Token path uses /home/{user}/... not ~ because systemd does not expand tilde"

patterns-established:
  - "ExecStop pre-action pattern: conditional API call before systemd KillSignal"

requirements-completed: [API-01, E2E-08]

duration: 2min
completed: 2026-04-20
---

# Phase 8 Plan 03: ExecStop pre-shutdown save + golden recapture Summary

**ExecStop curl one-liner in satisfactory.service calls SaveGame API before SIGINT, with golden recaptured to 899 bytes**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-20T21:04:51Z
- **Completed:** 2026-04-20T21:06:51Z
- **Tasks:** 2 (both auto)
- **Files modified:** 4

## Accomplishments
- Added ExecStop to satisfactory.service.template with curl SaveGame API call
- ExecStop is fault-tolerant: missing token skips save, API failure proceeds to SIGINT
- Updated _render_satisfactory_service to pass token_path placeholder
- Recaptured golden file (899 bytes) with ExecStop line
- All 19 tests green (Palworld + ARK goldens unaffected)

## Task Commits

Each task was committed atomically:

1. **Task 1 + Task 2: ExecStop + golden recapture** - `3c5bbf3` (feat)

## Files Created/Modified
- `road_poneglyph/templates/satisfactory.service.template` - Added ExecStop with curl SaveGame
- `road_poneglyph/main.py` - Added token_path to _render_satisfactory_service
- `tests/golden/satisfactory.service.v0_3_0` - Recaptured golden (899 bytes)
- `tests/test_satisfactory_golden.py` - Added token_path to FIXTURE

## Decisions Made
- curl in ExecStop (not Python) -- simpler, no install dependency for service user
- `if [ -f token_path ]` conditional -- graceful when no token cached
- `sleep 2` between save response and SIGINT -- allows disk flush
- systemd sends KillSignal=SIGINT after ExecStop completes, so no manual kill needed
- `/home/{user}/...` for token path since systemd does not expand `~`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - ExecStop automatically uses cached token from `road-poneglyph satisfactory save` flow.

## Next Phase Readiness
- Phase 8 fully complete
- All Satisfactory features (install, start/stop/restart, status, save, edit-settings) functional
- Ready for Phase 9: Release Polish + v0.3.0 Publish

---
*Phase: 08-settings-adapter-https-api-client*
*Completed: 2026-04-20*
