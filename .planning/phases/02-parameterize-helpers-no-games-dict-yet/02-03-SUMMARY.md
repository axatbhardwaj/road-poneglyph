---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 03
subsystem: logpose.main
tags: [refactor, palworld, parameterization, python]
requirements: [ARCH-04, PAL-08, SET-04]
dependency_graph:
  requires:
    - "02-parameterize-helpers-no-games-dict-yet/02 (Wave 1 rename: _palworld_parse, _palworld_save)"
    - "02-parameterize-helpers-no-games-dict-yet/01 (byte-diff harness + golden fixture)"
  provides:
    - "Pure _render_service_file for Plan 05 harness real-code-path oracle"
    - "Parameterized helper signatures ready for Plan 04 install() wiring"
    - "_create_settings_from_default(default, dst, section_rename) shape for Phase 5 ARK (None rename)"
  affects:
    - "install() Typer command — now broken at call sites; Plan 04 wires it"
    - "edit_settings() Typer command — now broken at _create_settings_from_default() call; Plan 04 wires it"
tech_stack:
  added: []
  patterns:
    - "helper-body parameterization (no module-global reads)"
    - "render/write split (pure function + I/O side effects)"
    - "Optional[tuple[str, str]] for game-specific section-rename"
key_files:
  created: []
  modified:
    - logpose/main.py
decisions:
  - "Kept PalServer.sh hardcoded inside _run_steamcmd_update — Phase 3 generalizes via spec.binary_rel_path (out of scope)"
  - "Kept service_name parameter unused in _render_service_file body — Phase 3 shape symmetry; silenced via `_ = service_name`"
  - "Moved section-rename literals OUT of _create_settings_from_default body into caller — Plan 04 wires Palworld's ('[/Script/Pal.PalWorldSettings]', '[/Script/Pal.PalGameWorldSettings]') tuple; ARK will pass None"
  - "Moved `user = Path.home().name` OUT of _setup_polkit body — caller now passes user arg explicitly"
  - "console.print('Creating Pal Server service...') stayed with _write_service_file (I/O-adjacent), keeping _render_service_file pure"
metrics:
  duration: "~25 min"
  completed: "2026-04-12"
  tasks: 3
  commits: 3
  files_modified: 1
---

# Phase 2 Plan 3: Parameterize Helpers Summary

Parameterized every remaining Palworld-specific helper in `logpose/main.py` (steamcmd trio, service render/write split, polkit + settings helpers) so helper bodies stop reading module globals and hardcoded literals — Plan 04 will wire the new signatures into the `install()` and `edit_settings()` Typer commands.

## What Was Done

### Task 1: Steamcmd Trio — commit `7c5490a`

- `_run_steamcmd_update(server_dir: Path, app_id: int) -> None` — body no longer reads `PAL_SERVER_DIR` or the `2394010` literal.
- `_install_palworld(server_dir: Path, app_id: int) -> None` — thin wrapper, forwards both args.
- `_fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path) -> None` — body no longer reads `STEAM_DIR`; both paths come from arguments (PAL-08 prep).
- Used Python's adjacent-string-literal concatenation to keep the steamcmd command byte-identical to v0.1.19 while splitting the f-string over two physical lines for readability.

### Task 2: Render/Write Split — commit `758f7fb`

- **Deleted** `_create_service_file(port: int, players: int)`.
- Added `_render_service_file(service_name, template_name, user, working_directory, exec_start_path, port, players) -> str` — PURE function: no `_run_command`, no `console.print`, no filesystem I/O. Returns the rendered unit-file string.
- Added `_write_service_file(service_file: Path, content: str) -> None` — preserves v0.1.19 side effects byte-for-byte: `echo '{content}' | sudo tee {service_file}` then `sudo systemctl daemon-reload`. The "Creating Pal Server service..." console message moved here to keep the render half pure.
- `service_name` is accepted but unused in Phase 2 — reserved for Phase 3 shape symmetry, silenced via `_ = service_name`.

### Task 3: Polkit + Settings Helpers — commit `823fe71`

- `_setup_polkit(rules_filename: str, template_name: str, user: str) -> None` — filename, template name, and user now args. Rule body still references `palserver.service` literal via the existing template (Phase 4 merges into `40-logpose.rules`).
- `_create_settings_from_default(default_path: Path, dst_path: Path, section_rename: Optional[tuple[str, str]]) -> None` — paths and section-rename now args. Palworld's `[/Script/Pal.PalWorldSettings]` → `[/Script/Pal.PalGameWorldSettings]` string literals moved OUT of the body; `content.replace(section_rename[0], section_rename[1])` is the verbatim replacement call. `None` disables the rename (ARK in Phase 5).
- Error messages preserved byte-for-byte from v0.1.19.

## Signature Verification

All 7 new/renamed signatures confirmed via grep:

```
$ grep -nE '^def _run_steamcmd_update|^def _install_palworld|^def _fix_steam_sdk|^def _render_service_file|^def _write_service_file|^def _setup_polkit|^def _create_settings_from_default' logpose/main.py
129:def _run_steamcmd_update(server_dir: Path, app_id: int) -> None:
140:def _install_palworld(server_dir: Path, app_id: int) -> None:
146:def _fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path) -> None:
159:def _render_service_file(
182:def _write_service_file(service_file: Path, content: str) -> None:
189:def _setup_polkit(rules_filename: str, template_name: str, user: str) -> None:
240:def _create_settings_from_default(
```

Old function deleted:

```
$ grep -c '^def _create_service_file' logpose/main.py
0
```

## Helper-Body Grep Results (zero module-global reads)

| Helper                          | Invariant                                         | Result |
| ------------------------------- | ------------------------------------------------- | ------ |
| `_fix_steam_sdk`                | body ∩ `STEAM_DIR`                                | 0 hits |
| `_run_steamcmd_update`          | body ∩ `PAL_SERVER_DIR`, `2394010`                | 0 hits |
| `_create_settings_from_default` | body ∩ `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`, `PalWorldSettings`, `PalGameWorldSettings` | 0 hits |
| `_setup_polkit`                 | body ∩ `Path.home().name`, `40-palserver.rules`, `palserver.rules.template` | 0 hits |

Module-scope constants (`STEAM_DIR`, `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`) remain at module scope — Typer commands still read them. Phase 3 dissolves them into `GAMES["palworld"]`.

## Direct Functional Check — `_render_service_file` vs golden

```
$ .venv/bin/python - <<'PY'
from pathlib import Path
import logpose.main as m
out = m._render_service_file(
    "palserver", "palserver.service.template", "foo",
    Path("/home/foo/.steam/steam/steamapps/common/PalServer"),
    Path("/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh"),
    8211, 32,
)
golden = Path("tests/golden/palserver.service.v0_1_19").read_bytes()
assert out.encode("utf-8") == golden
print("OK")
PY
OK
```

Exit code: 0.

## Harness Still Green

```
$ pytest tests/test_palworld_golden.py -x
collected 2 items
tests/test_palworld_golden.py ..                                         [100%]
============================== 2 passed in 0.30s ===============================
```

`python -c "import logpose.main"` also succeeds (exit 0).

## Intentional Breakage — Plan 04's Scope

`install()` and `edit_settings()` Typer commands currently call the refactored helpers with their OLD signatures — invoking `logpose install` or `logpose edit-settings` would raise `TypeError`. This is intentional per Plan 04's wave plan — that plan wires the new signatures into the command bodies. The Plan 01 harness does NOT invoke those commands, so it stays green.

## Deviations from Plan

**1. [Rule 1 — Acceptance strictness] Tightened comment wording inside `_create_settings_from_default`**

- **Found during:** Task 3 verification
- **Issue:** The initial comment inside the helper mentioned "PalGameWorldSettings" as a descriptive aside, which tripped the plan's acceptance grep `! ( sed ... | grep -qE '...PalGameWorldSettings' )` even though no string *literal* existed in the body (only a comment substring).
- **Fix:** Reworded the comment to drop game-specific nouns: "Game-specific behavior: some games need the section header renamed when copying the default template into the saved config. ARK passes None." — semantically equivalent, satisfies the strict grep invariant.
- **Files modified:** `logpose/main.py`
- **Commit:** `823fe71` (folded into Task 3 commit)

No other deviations. Plan executed as written.

## Deferred Items

None.

## Known Stubs

None introduced by this plan. The `install()` / `edit_settings()` call-site breakage is not a stub — it is a scheduled hand-off to Plan 04, explicitly documented in the plan's `<verification>` "Expected status" note.

## Self-Check: PASSED

- logpose/main.py — FOUND
- .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-03-SUMMARY.md — FOUND (this file)
- Commit `7c5490a` — FOUND (Task 1: steamcmd trio)
- Commit `758f7fb` — FOUND (Task 2: render/write split)
- Commit `823fe71` — FOUND (Task 3: polkit + settings helpers)
- Plan 01 harness: 2 passed
- `_render_service_file` golden equality: OK
