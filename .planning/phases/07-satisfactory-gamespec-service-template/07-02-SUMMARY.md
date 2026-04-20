---
phase: 07-satisfactory-gamespec-service-template
plan: 02
subsystem: satisfactory-games-registry
tags: [satisfactory, games-dict, polkit, factory, verbs]
dependency_graph:
  requires: [07-01]
  provides: [GAMES["satisfactory"], satisfactory-verbs, polkit-v0_3_0-golden]
  affects: [road_poneglyph/main.py, tests/test_palworld_golden.py]
tech_stack:
  added: []
  patterns: [elif-branch-in-factory, atomic-polkit-recapture]
key_files:
  created:
    - tests/golden/40-road-poneglyph.rules.v0_3_0
  modified:
    - road_poneglyph/main.py
    - tests/test_palworld_golden.py
decisions:
  - settings_adapter placeholder uses _palworld_parse/_palworld_save -- Phase 8 replaces with INI adapter (SAT-01 maps to SET-05)
  - Satisfactory install verb uses --auto-update flag for opt-in ExecStartPre SteamCMD update (SAT-08)
  - Polkit golden v0_3_0 captured from actual GAMES dict iteration order (palworld, ark, satisfactory)
metrics:
  duration: 80s
  completed: "2026-04-20T20:47:20Z"
---

# Phase 7 Plan 02: GAMES["satisfactory"] + Factory Branches + Polkit Golden Summary

GAMES["satisfactory"] wired with app_id=1690800, all verbs dispatched via Satisfactory branch, polkit golden recaptured atomically for 3 games.

## What Was Done

### Task 1: GAMES entry + factory branch
- Added `_SAT_SERVER_DIR = Path.home() / "SatisfactoryDedicatedServer"` constant
- Added `GAMES["satisfactory"]` GameSpec entry with all required fields
- Added `elif spec.key == "satisfactory":` branch in `_build_game_app` with:
  - `install` command: --port, --reliable-port, --players, --auto-update, --start
  - Standard verbs: start, stop, restart, status, enable, disable, update (all systemctl)

### Task 2: Polkit golden recapture
- Generated `tests/golden/40-road-poneglyph.rules.v0_3_0` from GAMES dict (includes "satisfactory.service")
- Updated `test_palworld_golden.py`: renamed polkit test to v0_3_0, pointed at new golden
- Old v0_2_0 golden preserved on disk for git history reference

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1-2 | 692b757 | feat(07-02): wire GAMES["satisfactory"] + factory verbs + polkit golden v0_3_0 |

## Self-Check: PASSED
