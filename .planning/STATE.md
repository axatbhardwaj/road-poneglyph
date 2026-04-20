---
gsd_state_version: 1.0
milestone: v0.3.0
milestone_name: Satisfactory Support
status: active
last_updated: "2026-04-21T00:00:00Z"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# STATE: road-poneglyph v0.3.0

*Project memory — updated at phase transitions and session boundaries.*

## Project Reference

**Project:** road-poneglyph (multi-game dedicated server launcher CLI)
**Active Milestone:** v0.3.0 — Add Satisfactory dedicated server support
**Core Value:** One CLI, many games, zero sudo prompts — operators type `road-poneglyph <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box.
**Distribution name on PyPI:** `road-poneglyph`
**Granularity:** coarse (3 phases)
**Current Focus:** Phase 7 — Satisfactory GameSpec + Service Template

## Current Position

**Phase:** 7 — Satisfactory GameSpec + Service Template — NOT STARTED
**Plan:** TBD
**Status:** Active — ready for `/gsd-plan-phase 7` or `/gsd-autonomous --from 7`
**Progress:** [░░░░░░░░░░] 0%

**Next action:** `/gsd-autonomous --from 7` to execute all phases.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 0 / 3 |
| Phases complete | 0 / 3 |
| Plans complete | 0 |
| Requirements shipped | 0 / 24 |
| Byte-diff harness green | ✅ 6 tests passing (4 Palworld + 2 ARK) |

## Phase Completion

| Phase | Name | Status | Completed | Notes |
|-------|------|--------|-----------|-------|
| 7 | Satisfactory GameSpec + Service Template | Pending | — | SteamCMD native path + SIGINT systemd template |
| 8 | Settings Adapter + HTTPS API Client | Pending | — | INI editor + pre-shutdown save + API verbs |
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

### Prior Milestone (v0.2.0) — Shipped 2026-04-14

- Palworld + ARK both working
- GameSpec registry + Typer factory + merged polkit
- PyPI trusted publisher workflow
- Renamed to road-poneglyph
- 6-test byte-diff harness green

### Research Available

- `.planning/research/satisfactory-hosting.md` — comprehensive technical brief (ports, config, API, systemd, quirks)

## Session Continuity

**Last session:** 2026-04-21
**Resume instructions:** `/gsd-autonomous --from 7`

---
*State initialized: 2026-04-21*
