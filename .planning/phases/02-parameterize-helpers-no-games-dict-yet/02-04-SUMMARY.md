---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 04
subsystem: cli-wiring
tags: [typer, wiring, palworld, python]
requires:
  - "02-parameterize-helpers-no-games-dict-yet/02"
  - "02-parameterize-helpers-no-games-dict-yet/03"
provides:
  - "install command threads Palworld values into parameterized helpers"
  - "update command threads Palworld values into _run_steamcmd_update"
  - "edit_settings threads Palworld section-rename tuple into _create_settings_from_default"
affects:
  - logpose/main.py
tech-stack:
  added: []
  patterns:
    - "caller-threaded game-specific constants (app_id, section-rename tuple, sdk64 path, template names, service name)"
    - "kwarg-style call for multi-param helpers (_render_service_file has 7 params — positional would be a readability footgun)"
key-files:
  created: []
  modified:
    - logpose/main.py
decisions:
  - "Kept module-scope constants (PAL_SERVER_DIR, PAL_SETTINGS_PATH, etc.) at module scope — Phase 3 will dissolve them into GAMES['palworld']. Phase 2 scope is helpers-no-read-globals; command wiring still reads globals by design."
  - "Used kwargs for _render_service_file (7 params); positional style used for 2-3 param helpers."
  - "Preserved 'palworld-server-launcher' post-install strings verbatim — CLI restructure is Phase 4 (CLI-05), not Phase 2."
  - "sys.exit(1) preserved (typer.Exit migration is Phase 4)."
metrics:
  completed: "2026-04-12"
  tasks: 2
  commits: 2
---

# Phase 02 Plan 04: Wire Typer Commands Summary

Wired the three Palworld Typer commands (`install`, `update`, `edit_settings`) to call the Wave-2 parameterized helper signatures, threading Palworld-specific values (app_id 2394010, sdk64 path, steamclient.so source, template names, polkit filename, section-rename tuple) from command bodies. Helper bodies no longer reach back up to Palworld-named module globals — calls flow top-down from commands.

## What Changed

### `install()` command (logpose/main.py ~line 310)
Replaced five stale zero-arg calls with parameterized calls:

| Before                         | After                                                                                                                                                                            |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_install_palworld()`          | `_install_palworld(PAL_SERVER_DIR, 2394010)`                                                                                                                                     |
| `_fix_steam_sdk()`             | `_fix_steam_sdk(Path.home() / ".steam/sdk64", STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so")`                                                      |
| `_create_service_file(port, players)` | `service_content = _render_service_file(service_name="palserver", template_name="palserver.service.template", user=..., working_directory=..., exec_start_path=..., port=port, players=players)` + `_write_service_file(Path("/etc/systemd/system/palserver.service"), service_content)` |
| `_setup_polkit()`              | `_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)`                                                                                              |

### `update()` command (~line 389)
`_run_steamcmd_update()` → `_run_steamcmd_update(PAL_SERVER_DIR, 2394010)` (one-line delta).

### `edit_settings()` command (~line 396)
`_create_settings_from_default()` → `_create_settings_from_default(DEFAULT_PAL_SETTINGS_PATH, PAL_SETTINGS_PATH, ("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]"))` — section-rename tuple threaded as caller argument.

## Grep Verification (final sweep)

```text
grep -c '_install_palworld(PAL_SERVER_DIR, 2394010)'       logpose/main.py  → 1
grep -c '_fix_steam_sdk('                                  logpose/main.py  → 2   (1 def + 1 call)
grep -c '_render_service_file('                            logpose/main.py  → 2   (1 def + 1 call)
grep -c '_write_service_file('                             logpose/main.py  → 2   (1 def + 1 call)
grep -c '_setup_polkit('                                   logpose/main.py  → 2   (1 def + 1 call)
grep -c '_run_steamcmd_update('                            logpose/main.py  → 3   (1 def + 1 call inside _install_palworld + 1 call inside update)
grep -c '_create_settings_from_default('                   logpose/main.py  → 2   (1 def + 1 call)

# Stale-call sweep (expected: no matches anywhere)
grep -E '_parse_settings|_save_settings|_create_service_file|_install_palworld\(\)|_fix_steam_sdk\(\)|_setup_polkit\(\)|_run_steamcmd_update\(\)|_create_settings_from_default\(\s*\)' logpose/main.py
  → NO MATCHES (clean sweep)
```

## Runtime Checks

- `python -c "import logpose.main"` → exit 0 (no TypeError on command attribute lookup).
- `python -c "import logpose.main; logpose.main.install; logpose.main.update; logpose.main.edit_settings"` → exit 0.
- `python -m logpose.main --help` → exit 0, lists all 9 commands (install, start, stop, restart, status, enable, disable, update, edit-settings).
- `pytest tests/test_palworld_golden.py -x` → 2 passed, 0 failed (template + byte-diff harness unaffected by this plan).

### `--help` stdout head

```text
 Usage: python -m logpose.main [OPTIONS] COMMAND [ARGS]...

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ install         Install the Palworld dedicated server and create a systemd   │
│                 service.                                                     │
│ start           Start the Palworld server.                                   │
...
│ update          Update the Palworld dedicated server.                        │
│ edit-settings   Edit the PalWorldSettings.ini file.                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Byte-Compat Invariants Preserved

- `working_directory=PAL_SERVER_DIR` and `exec_start_path=PAL_SERVER_DIR / "PalServer.sh"` match v0.1.19's in-helper derivation exactly — systemd unit render stays byte-identical (Plan 01 harness confirms).
- `Path.home() / ".steam/sdk64"` and `STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"` reproduce v0.1.19 character-for-character, including the embedded spaces in `"Steamworks SDK Redist"`.
- Palworld section-rename tuple `("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]")` reproduces v0.1.19's inline `content.replace()` literals verbatim (PAL-05 preserved).
- Post-install text strings (`"palworld-server-launcher start"`, `"palworld-server-launcher enable"`) preserved — CLI renaming deferred to Phase 4 CLI-05.
- `sys.exit(1)` on root-user guard preserved — `typer.Exit` migration deferred to Phase 4.

## Requirements Closed

- **ARCH-04 (Phase 2 partial scope):** Every helper in `logpose/main.py` takes game-specific values as arguments; helper bodies no longer read Palworld-named module globals. Commands do the reading, pass explicit values down. Phase 3 will dissolve the remaining module globals into `GAMES["palworld"]`.
- **SET-01:** `edit_settings` works end-to-end with `_palworld_parse` / `_palworld_save` / `_create_settings_from_default(..., section_rename)` wired at the command level.
- **PAL-08:** `_fix_steam_sdk` Palworld-only sdk64 behavior preserved — `install` passes exactly the v0.1.19 sdk64 destination path.
- **SET-04:** `_create_settings_from_default` Palworld section-rename preserved via caller-threaded tuple.

## Commits

| Task | Commit    | Message                                                        |
| ---- | --------- | -------------------------------------------------------------- |
| 1    | `b3cda38` | refactor(02-04): wire install+update to parameterized helpers  |
| 2    | `f43d714` | refactor(02-04): wire edit_settings section-rename tuple       |

## Deviations from Plan

None — plan executed exactly as written.

The plan's acceptance check `grep -c '_create_settings_from_default(' logpose/main.py` expects `1` but returns `2` (definition line + one call site). This is a grep-pattern quirk, not a deviation: the *call sites* count is exactly 1 as intended. Same pattern applies to the other helpers (1 def + N calls).

## Self-Check: PASSED

- `logpose/main.py` modified, committed (commits `b3cda38`, `f43d714`) — FOUND in `git log --all`.
- `.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-04-SUMMARY.md` — FOUND (this file).
- `pytest tests/test_palworld_golden.py -x` → 2 passed.
- `python -c "import logpose.main"` → exit 0.
- All plan `must_haves.truths` verified via grep + runtime.
