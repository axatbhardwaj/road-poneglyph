---
gsd_state_version: 1.0
milestone: v0.3.0
milestone_name: Satisfactory Support
status: active
last_updated: "2026-04-20T21:06:51Z"
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
  percent: 67
---

# STATE: road-poneglyph v0.3.0

*Project memory — updated at phase transitions and session boundaries.*

## Project Reference

**Project:** road-poneglyph (multi-game dedicated server launcher CLI)
**Active Milestone:** v0.3.0 — Add Satisfactory dedicated server support
**Core Value:** One CLI, many games, zero sudo prompts — operators type `road-poneglyph <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box.
**Distribution name on PyPI:** `road-poneglyph`
**Granularity:** coarse (3 phases)
**Current Focus:** Phase 8 — Settings Adapter + HTTPS API Client

## Current Position

**Phase:** 8 — Settings Adapter + HTTPS API Client — COMPLETE
**Plan:** 3/3 complete
**Status:** Phase 8 complete — ready for Phase 9
**Progress:** [██████░░░░] 67%

**Next action:** `/gsd-plan-phase 9` or `/gsd-autonomous --from 9`

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 2 / 3 |
| Phases complete | 2 / 3 |
| Plans complete | 6 |
| Requirements shipped | 21 / 24 |
| Byte-diff harness green | 19 tests passing (4 Palworld + 2 ARK + 2 Satisfactory golden + 5 INI + 6 API) |

## Phase Completion

| Phase | Name | Status | Completed | Notes |
|-------|------|--------|-----------|-------|
| 7 | Satisfactory GameSpec + Service Template | Complete | 2026-04-20 | 3/3 plans, 8 tests green, 0 deviations |
| 8 | Settings Adapter + HTTPS API Client | Complete | 2026-04-20 | 3/3 plans, 19 tests green, 0 deviations |
| 9 | Release Polish + v0.3.0 Publish | Pending | — | README, version bump, tag → PyPI |

## Accumulated Context

### Decisions Locked

- Native SteamCMD path (no wrapper tool like arkmanager) — same as Palworld pattern.
- KillSignal=SIGINT for satisfactory.service (SIGTERM kills without cleanup).
- Pre-shutdown save via HTTPS API `SaveGame` call (server does NOT auto-save on any signal).
- Bearer token auth cached at `~/.config/road-poneglyph/satisfactory-api-token` (mode 0600).
- `vm.max_map_count=262144` sysctl tuning via post_install_hook.
- Ports: 7777 UDP (game) + 7777 TCP (API) + 8888 TCP (reliable messaging).
- INI adapter via stdlib configparser (same approach as research concluded).
- Config files only appear after first graceful stop (first-run quirk — document, don't work around).
- Server must be "claimed" in-game before API works (human step, cannot be automated).
- Section-qualified INI keys ([Section]/Key) to avoid collisions between Unreal Engine INI sections.
- stdlib-only HTTPS client (urllib.request + ssl + json) — no new pip dependencies.
- ExecStop uses curl (not Python) for pre-shutdown save — no road-poneglyph install dependency for service user.
- Token path in systemd uses /home/{user}/... not ~ because systemd does not expand tilde.

### Prior Milestone (v0.2.0) — Shipped 2026-04-14

- Palworld + ARK both working
- GameSpec registry + Typer factory + merged polkit
- PyPI trusted publisher workflow
- Renamed to road-poneglyph
- 6-test byte-diff harness green

### Research Available

- `.planning/research/satisfactory-hosting.md` — comprehensive technical brief (ports, config, API, systemd, quirks)

## Session Continuity

**Last session:** 2026-04-20
**Stopped at:** Completed Phase 8 (all 3 plans — INI adapter, API client, ExecStop)
**Resume instructions:** `/gsd-plan-phase 9` or `/gsd-autonomous --from 9`

---
*State initialized: 2026-04-21*
