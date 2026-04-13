---
phase: 04-typer-factory-merged-polkit
plan: 01
subsystem: cli
tags: [typer, factory, additive, palworld]
requires:
  - GameSpec dataclass (from Phase 3)
  - GAMES["palworld"] registry (from Phase 3)
provides:
  - _build_game_app(spec) factory
  - `logpose palworld <verb>` dispatch path
affects:
  - logpose/main.py
tech-stack:
  added: []
  patterns:
    - typer add_typer closure-bound factory
key-files:
  created: []
  modified:
    - logpose/main.py
decisions:
  - Factory pattern (not decorator-in-loop) — each closure binds spec correctly.
  - _setup_polkit signature left unchanged (Plan 04-03 refactors).
  - Nine inner verbs mirror flat commands; install uses typer.Exit(code=1) for root-check (only new typer.Exit in this plan).
metrics:
  duration_minutes: 5
  completed_at: 2026-04-13
commit: 3b1ad4c
---

# Phase 04 Plan 01: Add `_build_game_app` Factory (additive) Summary

Added a `_build_game_app(spec: GameSpec) -> typer.Typer` factory to `logpose/main.py` and a registration loop `for _key, _spec in GAMES.items(): app.add_typer(...)` immediately before `if __name__ == "__main__":`. All nine verbs (install/start/stop/restart/status/enable/disable/update/edit-settings) live inside the factory's closure over `spec`. Existing flat `@app.command()` decorators were left untouched — both dispatch shapes work in parallel until Plan 04-02 deletes the flat commands.

## File State

- `logpose/main.py` — `+136` lines. Factory body between the `GAMES` dict (ends line ~367) and the first existing flat `@app.command()` (install). Registration loop appended at module scope above the `__main__` guard.

## Verification

- `pytest tests/test_palworld_golden.py -x` → 3 passed.
- `logpose --help` exit 0 — lists `palworld` sub-app.
- `logpose palworld --help` exit 0 — lists all nine verbs including `edit-settings`.
- `logpose palworld install --help` exit 0 — lists `--port`, `--players`, `--start`.
- Factory body grep audit: zero hardcoded `2394010` / `"palserver"` / `"palworld"` / `PalWorldSettings.ini` literals inside `_build_game_app`.

## Deviations from Plan

None — plan executed exactly as written.

## Handoff to Plan 04-02

- Flat `@app.command()` decorators still present in `logpose/main.py` (install L370, start L417, stop L424, restart L431, status L438, enable L445, disable L452, update L459, edit_settings L468). Plan 04-02 deletes them.
- Root `app = typer.Typer()` has no `help=` or `no_args_is_help=True` yet — Plan 04-02 upgrades it.
- No `@app.callback()` / `--version` yet — Plan 04-02 adds.
- `_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)` call-site inside the factory `install` retains v0.1.19 signature — Plan 04-03 refactors.

## Self-Check: PASSED

- `logpose/main.py` exists and imports cleanly on Python 3.13.
- Commit `3b1ad4c` on HEAD touches exactly `logpose/main.py`.
- Byte-diff harness green.
