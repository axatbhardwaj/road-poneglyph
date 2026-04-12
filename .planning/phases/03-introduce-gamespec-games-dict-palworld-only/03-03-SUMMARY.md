---
phase: 03-introduce-gamespec-games-dict-palworld-only
plan: 03
subsystem: logpose.main (install command post-install hook wiring)
tags: [refactor, post-install-hooks, palworld, python]
requirements: [PAL-08]
dependency_graph:
  requires:
    - "03-introduce-gamespec-games-dict-palworld-only/01 (_palworld_sdk_hook + GAMES['palworld'].post_install_hooks list)"
    - "03-introduce-gamespec-games-dict-palworld-only/02 (spec = GAMES['palworld'] binding already in install())"
  provides:
    - "install() iterates spec.post_install_hooks instead of calling _fix_steam_sdk directly"
    - "_fix_steam_sdk invoked only via _palworld_sdk_hook closure — declaratively Palworld-only"
  affects:
    - "Phase 4 (factory pattern can iterate post_install_hooks uniformly across games; ARK's hook list will be empty since arkmanager handles SDK setup)"
tech_stack:
  added: []
  patterns:
    - "for hook in spec.post_install_hooks: hook() — the factory-uniform hook invocation pattern"
key_files:
  created:
    - .planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-03-SUMMARY.md
  modified:
    - logpose/main.py
decisions:
  - "Kept _fix_steam_sdk signature unchanged — the zero-arg closure pattern adapts the game-specific paths. Changing the helper to consume spec.steam_sdk_paths would couple it to the spec and introduce independent byte-diff risk."
  - "Left the empty blank line between _run_steamcmd_update and the for-loop gone (2-line insertion replacing a 4-line call). Byte-diff harness unaffected because the change is inside install(), not _render_service_file."
metrics:
  duration: "~3 min"
  completed: "2026-04-13"
  tasks: 2
  commits: 1
  files_modified: 1
---

# Phase 3 Plan 3: Wire _fix_steam_sdk as post_install_hook Summary

Replaced the direct `_fix_steam_sdk(Path.home() / ".steam/sdk64", STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so")` call inside `install()` with a two-line iteration `for hook in spec.post_install_hooks: hook()`. Palworld's hook list (registered as `[_palworld_sdk_hook]` in Plan 03-01) is now the sole driver of the steam SDK fix — PAL-08 closed.

## What Was Done

### Task 1: Replace _fix_steam_sdk direct call with hook iteration

- In `install()`, swapped the 4-line `_fix_steam_sdk(...)` block for a 2-line `for hook in spec.post_install_hooks: hook()` loop.
- No other changes — `_install_steamcmd()`, `_run_steamcmd_update(...)`, `_render_service_file(...)`, `_write_service_file(...)`, `_setup_polkit(...)`, and the post-install console output are byte-identical to Plan 03-02's output.

### Task 2: Byte-diff exit gate + final Phase 3 audit + commit

- `pytest tests/test_palworld_golden.py -x`: 3 passed.
- `python tests/test_palworld_golden.py`: exit 0.
- Final Phase 3 audit (all expected): 0 module-level PAL_* assignments, exactly 1 `2394010` literal, exactly 1 `for hook in spec.post_install_hooks` iteration, exactly 1 `"palserver.service.template"` literal, GameSpec has 15 fields, `_fix_steam_sdk` is referenced exactly twice (its `def` and inside `_palworld_sdk_hook`).
- Single atomic commit: `b6003bf`.
- `git log --oneline -3` shows the three Phase 3 commits in order: `c844030` (03-01), `157baf7` (03-02), `b6003bf` (03-03).

## Acceptance Results

| Check | Expected | Actual |
| ----- | -------- | ------ |
| `install()` iterates `spec.post_install_hooks` | PASS | PASS |
| `install()` contains zero direct `_fix_steam_sdk` calls | PASS | PASS |
| `_fix_steam_sdk` referenced exactly twice (def + hook) | PASS | PASS |
| Module-level `PAL_SERVER_DIR` / `PAL_SETTINGS_PATH` / `DEFAULT_PAL_SETTINGS_PATH` | 0 | 0 |
| Literal `2394010` | 1 | 1 |
| `for hook in spec.post_install_hooks` | 1 | 1 |
| `"palserver.service.template"` literal | 1 | 1 |
| `GameSpec` field count | 15 | 15 |
| `pytest tests/test_palworld_golden.py -x` | 3 passed | 3 passed |
| `python tests/test_palworld_golden.py` | exit 0 | exit 0 |
| Commit `b6003bf` subject matches `refactor(03-03): …` | PASS | PASS |

## Requirements Closed

- PAL-08: `_fix_steam_sdk` wired as a Palworld-only `post_install_hook` via `_palworld_sdk_hook` zero-arg closure; `install()` iterates `spec.post_install_hooks`.

## Phase 3 Final Audit

With Plans 03-01 (ARCH-01/02/03), 03-02 (ARCH-04, PAL-05), and 03-03 (PAL-08), Phase 3 is complete:

| Phase 3 Success Criterion | Status |
| ------------------------- | ------ |
| #1 `GameSpec` frozen dataclass with 14 named fields (15 total) + `SettingsAdapter` frozen with parse+save | PASS |
| #2 `GAMES: dict[str, GameSpec]` at module scope with exactly one entry; no PAL_* module globals | PASS |
| #3 Every game-aware helper/command reads Palworld values from `GAMES["palworld"]` (no hardcoded `palserver`/`PalWorld`/`2394010` in helper/command bodies) | PASS |
| #4 Section-rename via `GameSpec.settings_section_rename`; `_fix_steam_sdk` as `post_install_hook` | PASS |
| #5 Byte-diff harness exits 0 against v0.1.19 golden | PASS |

## Handoff Note for Phase 4

- `_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)` inside `install()` still uses literal strings. Phase 4's merged polkit rule work targets them.
- The `for hook in spec.post_install_hooks: hook()` pattern is factory-ready — when Phase 4's `_build_game_app(spec)` factory rolls out, the same loop body will be invoked inside a game-agnostic `install` template.
- ARK's `GAMES["ark"]` will provide an empty `post_install_hooks=[]` since arkmanager handles steam SDK setup internally (per ARK-12 / Phase 5 reference).

## Deviations from Plan

None — plan executed exactly as written.

## Deferred Items

None.

## Known Stubs

None introduced by this plan.

## Self-Check: PASSED

- logpose/main.py — FOUND (install() iterates post_install_hooks; no direct _fix_steam_sdk call)
- Commit `b6003bf` — FOUND on main
- `pytest tests/test_palworld_golden.py -x` — 3 passed
- `python tests/test_palworld_golden.py` — exit 0
- Final Phase 3 grep audits: all pass
