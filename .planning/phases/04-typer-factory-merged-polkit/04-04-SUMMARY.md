---
phase: 04-typer-factory-merged-polkit
plan: 04
subsystem: cli+docs
tags: [typer-exit, readme, cli-examples]
requires:
  - Plan 04-03 polkit merge
provides:
  - Zero sys.exit in logpose/main.py
  - README with game-first CLI examples
affects:
  - logpose/main.py
  - README.md
tech-stack:
  added: []
  patterns:
    - typer.Exit(code=1) for error paths; typer.Exit() for clean quit
key-files:
  created: []
  modified:
    - logpose/main.py
    - README.md
decisions:
  - _interactive_edit_loop quit uses typer.Exit() (no code) per Pitfall 6.
  - import sys retained (sys.stderr still referenced by 9 rich.print sites).
  - README kept minimal — ARK examples and migration note deferred to Phase 5/6.
metrics:
  duration_minutes: 5
  completed_at: 2026-04-13
commit: 822dc4f
---

# Phase 04 Plan 04: sys.exit → typer.Exit + README Palworld Examples Summary

Converted the last four `sys.exit(...)` call sites in `logpose/main.py`:
1. `_get_template` FileNotFoundError → `raise typer.Exit(code=1)`
2. `_run_command` CalledProcessError/FileNotFoundError → `raise typer.Exit(code=1)`
3. `_create_settings_from_default` missing default → `raise typer.Exit(code=1)`
4. `_interactive_edit_loop` quit path → `raise typer.Exit()` (clean quit, no code)

`import sys` is retained because `sys.stderr` is still referenced by nine `rich.print(..., file=sys.stderr)` sites.

Updated `README.md` to use the `logpose palworld <verb>` CLI shape (install/start/stop/restart/status/enable/disable/update/edit-settings) and the `pip install logpose-launcher` distribution name. Added `logpose --version` example. ARK examples, migration notes, and per-game firewall port reference remain Phase 5/6 scope.

## Final sys.exit → typer.Exit inventory

| Site                                    | Previous           | Now                      |
| --------------------------------------- | ------------------ | ------------------------ |
| `_get_template` (template missing)      | `sys.exit(1)`      | `raise typer.Exit(code=1)` |
| `_run_command` (subprocess error)       | `sys.exit(1)`      | `raise typer.Exit(code=1)` |
| `_create_settings_from_default` (no default) | `sys.exit(1)` | `raise typer.Exit(code=1)` |
| `_interactive_edit_loop` (user quit)    | `sys.exit(0)`      | `raise typer.Exit()`      |
| Factory `install` root check            | (already `typer.Exit(code=1)` from Plan 04-01) | unchanged |
| Factory `edit-settings` default-fallback parse | (already `typer.Exit(code=1)` from Plan 04-01) | unchanged |
| Factory `edit-settings` outer save try | (already `typer.Exit(code=1)` from Plan 04-01) | unchanged |

Total `raise typer.Exit` count in `logpose/main.py`: 7 (1 clean-quit `Exit()` + 6 error `Exit(code=1)`).

## README edits

- Title + first paragraph rewritten to describe `logpose` as a multi-game launcher; Palworld as the supported v0.2.0 target.
- All 9 verb examples switched from `palworld-server-launcher <verb>` to `logpose palworld <verb>`.
- Install instructions: `pip install palworld-server-launcher` → `pip install logpose-launcher`; distribution-name vs CLI-binary-name note added.
- New `logpose --version` example block.
- Polkit feature description updated to reference merged `40-logpose.rules`.

## End-of-phase grep audit results

| Check                                                | Expected | Actual |
| ---------------------------------------------------- | -------- | ------ |
| `sys.exit` in `logpose/main.py`                      | 0        | 0      |
| `^@app\.command` decorators                          | 0        | 0      |
| `@app.callback(`                                     | 1        | 1      |
| `def _build_game_app(`                               | 1        | 1      |
| `app.add_typer(`                                     | 1        | 1      |
| `_setup_polkit(Path.home().name)` call-site          | present  | present |
| `palserver.rules.template`/`40-palserver.rules` refs | 0        | 0      |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `pytest tests/test_palworld_golden.py -x` → 4 passed.
- `python tests/test_palworld_golden.py` exits 0.
- Commit `822dc4f` touches exactly `logpose/main.py` + `README.md`.
