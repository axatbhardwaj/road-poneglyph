---
phase: 03-introduce-gamespec-games-dict-palworld-only
plan: 01
subsystem: logpose.main (dataclass + registry layer)
tags: [refactor, dataclasses, registry, python, palworld]
requirements: [ARCH-01, ARCH-02, ARCH-03]
dependency_graph:
  requires:
    - "02-parameterize-helpers-no-games-dict-yet/* (parameterized helpers + byte-diff harness)"
  provides:
    - "SettingsAdapter + GameSpec frozen dataclasses"
    - "GAMES: dict[str, GameSpec] module-scope registry with single 'palworld' entry"
    - "_palworld_sdk_hook zero-arg closure over _fix_steam_sdk (prep for Plan 03-03)"
  affects:
    - "03-02 (call-site dissolution reads from GAMES added here)"
    - "03-03 (post_install_hooks list populated here is iterated by install())"
tech_stack:
  added: []
  patterns:
    - "frozen @dataclass for immutable per-game configuration (research/ARCHITECTURE.md)"
    - "field(default_factory=list/dict) for mutable-default dataclass fields"
    - "zero-arg closure for post-install hooks (closes over module-private _PAL_* helpers)"
key_files:
  created:
    - .planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-01-SUMMARY.md
  modified:
    - logpose/main.py
decisions:
  - "Callable imported from typing, not collections.abc — Python 3.8 floor (PKG-04) + from __future__ import annotations makes runtime cost zero."
  - "Dataclass definitions placed after module globals (line ~22) but GAMES construction placed after all helper function defs (before first @app.command()) to avoid NameError at import time."
  - "Underscore-prefixed _PAL_SERVER_DIR_LOCAL etc. distinguished from PAL_* module globals that still exist (dissolved in Plan 03-02)."
metrics:
  duration: "~5 min"
  completed: "2026-04-13"
  tasks: 3
  commits: 1
  files_modified: 1
---

# Phase 3 Plan 1: Add Dataclasses + GAMES Registry Summary

Landed `SettingsAdapter` and `GameSpec` frozen dataclasses plus a module-scope `GAMES: dict[str, GameSpec]` registry with a single `"palworld"` entry in `logpose/main.py`. All existing `PAL_*` module globals and command bodies remained untouched — this plan is purely additive so the byte-diff harness stayed green while subsequent plans flip call sites over.

## What Was Done

### Task 1: Imports + SettingsAdapter + GameSpec dataclass definitions

- Added `from dataclasses import dataclass, field` and extended `from typing import Optional` to `from typing import Callable, Optional`.
- Inserted `@dataclass(frozen=True) class SettingsAdapter` with `parse` + `save` callable fields.
- Inserted `@dataclass(frozen=True) class GameSpec` with the 15 named fields from ROADMAP Phase 3 Success Criterion #1 (`key`, `display_name`, `app_id`, `server_dir`, `binary_rel_path`, `settings_path`, `default_settings_path`, `settings_section_rename`, `service_name`, `service_template_name`, `settings_adapter`, `post_install_hooks`, `apt_packages`, `steam_sdk_paths`, `install_options`).
- Mutable defaults used `field(default_factory=list)` / `field(default_factory=dict)` to satisfy frozen dataclass constraints.

### Task 2: _palworld_sdk_hook closure + GAMES registry

- Added module-private `_PAL_SERVER_DIR_LOCAL`, `_PAL_STEAM_CLIENT_SO`, `_PAL_SDK64_DST` path constants immediately before the first `@app.command()`.
- Added `_palworld_sdk_hook()` zero-arg closure that calls `_fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)`.
- Built `GAMES["palworld"]` with all 15 fields matching v0.1.19 values (app_id 2394010, service_name "palserver", section-rename tuple, etc.).

### Task 3: Byte-diff exit gate + commit

- `pytest tests/test_palworld_golden.py -x`: 3 passed.
- `python tests/test_palworld_golden.py`: exit 0.
- Single atomic commit: `c844030`.

## Acceptance Results

| Check | Result |
| ----- | ------ |
| `SettingsAdapter` frozen dataclass with 2 callable fields | PASS |
| `GameSpec` frozen dataclass with 15 named fields | PASS |
| `GAMES: dict[str, GameSpec]` with single `"palworld"` key | PASS |
| `GAMES["palworld"]` populates all 15 fields correctly | PASS |
| Existing `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` still present | PASS |
| `pytest tests/test_palworld_golden.py -x` | 3 passed |
| `python tests/test_palworld_golden.py` | exit 0 |
| Commit `c844030` with subject matching `refactor(03-01): …` | PASS |

## Requirements Closed

- ARCH-01: `GameSpec` frozen dataclass defined with the ROADMAP-enumerated field set.
- ARCH-02: `SettingsAdapter` frozen dataclass defined with `parse` + `save` callables.
- ARCH-03: Module-scope `GAMES: dict[str, GameSpec]` registry with the single `"palworld"` entry.

## Handoff Note for Plan 03-02

All `@app.command()` bodies still read Palworld values from the old `PAL_*` module globals (`PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`) and the literal `2394010` / `"palserver"` strings. Plan 03-02 dissolves these globals, deletes `_install_palworld`, and rewrites every command body to bind `spec = GAMES["palworld"]` and read Palworld values exclusively via `spec.<field>`.

## Deviations from Plan

None — plan executed exactly as written.

## Deferred Items

None.

## Known Stubs

None introduced by this plan.

## Self-Check: PASSED

- logpose/main.py — FOUND (contains SettingsAdapter, GameSpec, GAMES registry)
- Commit `c844030` — FOUND on main
- `pytest tests/test_palworld_golden.py -x` — 3 passed
- `python tests/test_palworld_golden.py` — exit 0
