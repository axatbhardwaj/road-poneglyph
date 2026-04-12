---
phase: 03-introduce-gamespec-games-dict-palworld-only
plan: 02
subsystem: logpose.main (Typer commands + module globals)
tags: [refactor, dissolve-globals, call-sites, python, palworld]
requirements: [ARCH-04, PAL-05]
dependency_graph:
  requires:
    - "03-introduce-gamespec-games-dict-palworld-only/01 (GAMES registry + dataclasses)"
  provides:
    - "Every Typer command body reads Palworld values exclusively from GAMES['palworld']"
    - "No PAL_* module globals in logpose/main.py"
    - "_install_palworld wrapper removed — install() calls _run_steamcmd_update directly"
  affects:
    - "03-03 (install()'s direct _fix_steam_sdk call is the final thing to route through hooks)"
tech_stack:
  added: []
  patterns:
    - "spec = GAMES['palworld'] binding at top of each @app.command() body"
    - "f-string systemctl verb delegation: f'systemctl {verb} {spec.service_name}'"
    - "Settings I/O via spec.settings_adapter.parse/save instead of direct _palworld_parse/_palworld_save calls at command sites"
key_files:
  created:
    - .planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-02-SUMMARY.md
  modified:
    - logpose/main.py
decisions:
  - "Kept _fix_steam_sdk as a direct call inside install() in this plan — isolating the hook-iteration change as Plan 03-03's own atomic commit keeps PAL-08 verifiable in isolation."
  - "Kept _setup_polkit('40-palserver.rules', 'palserver.rules.template', ...) literal strings — Phase 4's merged polkit rule work targets them."
  - "Service file path rewritten as Path(f'/etc/systemd/system/{spec.service_name}.service') — renders to the same byte-identical path the direct literal produced."
metrics:
  duration: "~5 min"
  completed: "2026-04-13"
  tasks: 3
  commits: 1
  files_modified: 1
---

# Phase 3 Plan 2: Dissolve PAL_* Globals + Switch Call Sites Summary

Removed the three Palworld-specific module globals (`PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`) and the `_install_palworld` thin wrapper. Every `@app.command()` body now binds `spec = GAMES["palworld"]` at the top and reads Palworld values exclusively via `spec.<field>` — the `GAMES` registry added in Plan 03-01 became load-bearing.

## What Was Done

### Task 1: Dissolve PAL_* globals + delete _install_palworld wrapper

- Deleted lines `PAL_SERVER_DIR = …`, `PAL_SETTINGS_PATH = …`, `DEFAULT_PAL_SETTINGS_PATH = …` from the module-globals block.
- Kept `STEAM_DIR = Path.home() / ".steam/steam"` (game-agnostic; referenced by the `_PAL_*` block in Plan 03-01).
- Deleted the `_install_palworld(server_dir, app_id)` 4-line function.

### Task 2: Rewire nine Typer command bodies

Rewrote nine `@app.command()` bodies to read Palworld values from `GAMES["palworld"]`:

- **`install()`**: Binds `spec = GAMES["palworld"]`. `_install_palworld(PAL_SERVER_DIR, 2394010)` → `_run_steamcmd_update(spec.server_dir, spec.app_id)`. `_render_service_file(...)` kwargs use `spec.service_name`, `spec.service_template_name`, `spec.server_dir`, `spec.server_dir / spec.binary_rel_path`. Service file path → `Path(f"/etc/systemd/system/{spec.service_name}.service")`. `systemctl start` uses f-string. **Kept** direct `_fix_steam_sdk` call (Plan 03-03 target) and the `_setup_polkit("40-palserver.rules", …)` literals (Phase 4 target).
- **`update()`**: Binds `spec`, calls `_run_steamcmd_update(spec.server_dir, spec.app_id)`.
- **`edit_settings()`**: Binds `spec`, uses `spec.settings_adapter.parse/save(spec.settings_path)`, passes `spec.settings_section_rename` to `_create_settings_from_default` (PAL-05 closure).
- **`start/stop/restart/status/enable/disable()`**: Each binds `spec` and uses `f"systemctl {verb} {spec.service_name}"` instead of literal `"palserver"`.

### Task 3: Byte-diff exit gate + grep audits + commit

- `pytest tests/test_palworld_golden.py -x`: 3 passed.
- `python tests/test_palworld_golden.py`: exit 0.
- Grep audits (all expected): 0 module-level PAL_* assignments, 0 `def _install_palworld`, exactly 1 `2394010`, exactly 1 `[/Script/Pal.PalWorldSettings]` tuple (inside GAMES).
- Single atomic commit: `157baf7`.

## Acceptance Results

| Check | Expected | Actual |
| ----- | -------- | ------ |
| Module-level `PAL_SERVER_DIR` / `PAL_SETTINGS_PATH` / `DEFAULT_PAL_SETTINGS_PATH` | 0 | 0 |
| `def _install_palworld(` | 0 | 0 |
| Literal `2394010` | 1 (inside GAMES) | 1 |
| Literal `[/Script/Pal.PalWorldSettings]` | 1 (inside GAMES) | 1 |
| `"systemctl … palserver"` literal outside GAMES | 0 | 0 |
| `pytest tests/test_palworld_golden.py -x` | 3 passed | 3 passed |
| `python tests/test_palworld_golden.py` | exit 0 | exit 0 |
| Commit `157baf7` subject matches `refactor(03-02): …` | PASS | PASS |

## Requirements Closed

- ARCH-04: No Palworld-specific module globals in `logpose/main.py`; every command body reads from `GAMES["palworld"]`.
- PAL-05: `edit_settings()` reads `spec.settings_section_rename` instead of an inline tuple.

## Handoff Note for Plan 03-03

`install()` still contains a direct call:
```python
_fix_steam_sdk(
    Path.home() / ".steam/sdk64",
    STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so",
)
```
Plan 03-03 replaces these 4 lines with a 2-line iteration `for hook in spec.post_install_hooks: hook()`. The `_palworld_sdk_hook` closure registered in Plan 03-01 is already in `GAMES["palworld"].post_install_hooks` — the behavioral contract is identical (both paths call `_fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)` with the same Path values).

## Deviations from Plan

None — plan executed exactly as written.

## Deferred Items

None.

## Known Stubs

None introduced by this plan.

## Self-Check: PASSED

- logpose/main.py — FOUND (PAL_* globals and _install_palworld removed; nine command bodies rewired)
- Commit `157baf7` — FOUND on main
- `pytest tests/test_palworld_golden.py -x` — 3 passed
- `python tests/test_palworld_golden.py` — exit 0
- Grep audits: all pass
