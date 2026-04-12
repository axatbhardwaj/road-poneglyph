---
phase: 03-introduce-gamespec-games-dict-palworld-only
subsystem: logpose.main (dataclass migration + registry)
tags: [refactor, dataclasses, registry, post-install-hooks, palworld]
requirements: [ARCH-01, ARCH-02, ARCH-03, ARCH-04, PAL-05, PAL-08]
dependency_graph:
  requires:
    - "02-parameterize-helpers-no-games-dict-yet (parameterized helpers + byte-diff harness)"
  provides:
    - "SettingsAdapter + GameSpec frozen dataclasses"
    - "GAMES: dict[str, GameSpec] module-scope registry (single 'palworld' entry)"
    - "post_install_hooks pattern — factory-ready hook iteration"
  affects:
    - "Phase 4 (_build_game_app factory iterates over GAMES; merged 40-logpose.rules polkit)"
    - "Phase 5 (ARK entry slots into GAMES alongside Palworld)"
tech_stack:
  added: []
  patterns:
    - "frozen @dataclass for immutable per-game configuration"
    - "spec = GAMES['palworld'] binding at top of each @app.command()"
    - "for hook in spec.post_install_hooks: hook() — factory-uniform hook invocation"
    - "SettingsAdapter.parse/save dispatch via spec.settings_adapter"
key_files:
  created:
    - .planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-01-SUMMARY.md
    - .planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-02-SUMMARY.md
    - .planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-03-SUMMARY.md
    - .planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-SUMMARY.md
  modified:
    - logpose/main.py
decisions:
  - "Three atomic commits (03-01 additive, 03-02 dissolution, 03-03 hook wiring) kept each requirement closure verifiable in isolation and the byte-diff harness green at every boundary."
  - "Callable imported from typing (not collections.abc) — preserves Python 3.8 floor per PKG-04."
  - "_fix_steam_sdk signature untouched; the zero-arg closure pattern adapts game-specific paths without introducing byte-diff risk to the helper itself."
  - "_setup_polkit('40-palserver.rules', 'palserver.rules.template', …) literal strings left in place — Phase 4's merged polkit rule work targets them."
metrics:
  duration: "~15 min (3 plans)"
  completed: "2026-04-13"
  plans_complete: 3
  total_commits: 3
  files_modified: 1
---

# Phase 3: Introduce GameSpec + GAMES Dict (Palworld Only) — Summary

Three atomic commits migrated `logpose/main.py` from Palworld-specific module globals to a factory-ready `GameSpec` + `GAMES` registry architecture. `GAMES["palworld"]` is the single source of truth for every Palworld value — app id, server dir, settings paths, section-rename tuple, service name, steam SDK paths, and the post-install hook — and every `@app.command()` body reads from it. The byte-diff harness stayed green after every commit, proving Palworld's systemd unit rendering is byte-identical to v0.1.19.

## What Was Done

### Plan 03-01 (commit `c844030`) — Add dataclasses + GAMES registry (additive)

Introduced `@dataclass(frozen=True) class SettingsAdapter` (parse + save callables) and `@dataclass(frozen=True) class GameSpec` (15 named fields from ROADMAP Phase 3 Success Criterion #1). Added `_palworld_sdk_hook` zero-arg closure and built `GAMES: dict[str, GameSpec]` at module scope with a single `"palworld"` entry. All existing `PAL_*` module globals and command bodies left untouched — purely additive. Closed ARCH-01, ARCH-02, ARCH-03.

### Plan 03-02 (commit `157baf7`) — Dissolve PAL_* globals + rewire command bodies

Removed `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` module globals and the `_install_palworld` thin wrapper. Rewrote all nine `@app.command()` bodies (`install`, `update`, `edit_settings`, `start`, `stop`, `restart`, `status`, `enable`, `disable`) to bind `spec = GAMES["palworld"]` and read Palworld values exclusively via `spec.<field>`. The registry became load-bearing. Closed ARCH-04, PAL-05.

### Plan 03-03 (commit `b6003bf`) — Wire _fix_steam_sdk as post_install_hook

Replaced the direct `_fix_steam_sdk(Path.home() / ".steam/sdk64", STEAM_DIR / "…/steamclient.so")` call inside `install()` with `for hook in spec.post_install_hooks: hook()`. Palworld's hook list (registered in Plan 03-01) is now the sole driver of the steam SDK fix. Closed PAL-08.

## Commit Ledger

| Plan | Commit | Subject | Harness |
| ---- | ------ | ------- | ------- |
| 03-01 | `c844030` | `refactor(03-01): add GameSpec + SettingsAdapter dataclasses + GAMES registry` | 3 passed |
| 03-02 | `157baf7` | `refactor(03-02): dissolve PAL_* globals, rewire commands to read GAMES["palworld"]` | 3 passed |
| 03-03 | `b6003bf` | `refactor(03-03): wire _fix_steam_sdk as Palworld post_install_hook` | 3 passed |

## Phase 3 Success Criteria — Final Status

| # | Criterion | Status |
| - | --------- | ------ |
| 1 | `GameSpec` frozen dataclass with 14 named fields (15 total) + `SettingsAdapter` frozen with `parse` + `save` callables | PASS |
| 2 | `GAMES: dict[str, GameSpec]` at module scope with exactly one entry `"palworld"`; no `PAL_*` module constants remain | PASS |
| 3 | Every game-aware helper/command takes `spec` implicitly via `GAMES["palworld"]`; no hardcoded `palserver`/`PalWorld`/`2394010` in helper/command bodies (exceptions: the GAMES construction itself + the `_setup_polkit` literal strings which Phase 4 merges) | PASS |
| 4 | Section-rename via `GameSpec.settings_section_rename`; `_fix_steam_sdk` wired as Palworld-only `post_install_hook` | PASS |
| 5 | Byte-diff harness from Phase 2 exits 0 against v0.1.19 golden | PASS (3 tests green after each commit) |

## Grep Audit (end-of-phase exit criteria)

| Pattern | Expected | Actual |
| ------- | -------- | ------ |
| `^(PAL_SERVER_DIR\|PAL_SETTINGS_PATH\|DEFAULT_PAL_SETTINGS_PATH)\b` | 0 | 0 |
| `def _install_palworld\b` | 0 | 0 |
| `\b2394010\b` | 1 (inside GAMES) | 1 |
| `\[/Script/Pal\.PalWorldSettings\]` | 1 (inside GAMES) | 1 |
| `for hook in spec\.post_install_hooks` | 1 (inside install()) | 1 |
| `"palserver\.service\.template"` | 1 (inside GAMES) | 1 |
| `GameSpec` field count | 15 | 15 |
| `_fix_steam_sdk` references | 2 (def + hook) | 2 |

## Requirements Closed

| Req | Closed By | Status |
| --- | --------- | ------ |
| ARCH-01 | Plan 03-01 | ✅ `GameSpec` frozen dataclass with the 14-named-field ROADMAP set |
| ARCH-02 | Plan 03-01 | ✅ `SettingsAdapter` frozen dataclass with `parse`/`save` callables |
| ARCH-03 | Plan 03-01 | ✅ Module-scope `GAMES: dict[str, GameSpec]` with `"palworld"` entry |
| ARCH-04 | Plan 03-02 | ✅ No Palworld-specific module globals; helpers and commands read from `GAMES` |
| PAL-05 | Plan 03-02 | ✅ `edit_settings()` reads `spec.settings_section_rename` (no inline tuple) |
| PAL-08 | Plan 03-03 | ✅ `_fix_steam_sdk` wired as a Palworld-only `post_install_hook` |

## Invariants Preserved (byte-diff checked)

- `palserver.service.template` — untouched (PAL-02).
- `palserver.service` render — byte-identical to v0.1.19 golden (PAL-09 half).
- `_palworld_parse` / `_palworld_save` bodies — unchanged (PAL-03, PAL-04).
- `_run_command`, `_install_steamcmd`, `_repair_package_manager`, `_fix_steam_sdk` signatures — unchanged (ARCH-06).
- No `BaseGame` class, no `core/` split (ARCH-05).
- `logpose/main.py` remains the single implementation file per `logpose/CLAUDE.md`.

## Handoff Note for Phase 4

- `_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)` inside `install()` still uses literal strings. Phase 4's merged polkit rule work (`40-logpose.rules` generated from `GAMES.values()`) targets them.
- The `for hook in spec.post_install_hooks: hook()` pattern is factory-ready — when Phase 4's `_build_game_app(spec)` factory rolls out, the same loop body will be invoked inside a game-agnostic `install` template body.
- Every `@app.command()` already binds `spec = GAMES["palworld"]` at its top; Phase 4's factory will replace the hardcoded `"palworld"` key with the `spec` bound by the factory's closure argument.
- `GameSpec.install_options = {"port_default": 8211, "players_default": 32}` is populated — Phase 4's factory can feed these into `typer.Option()` defaults per spec, avoiding hardcoded literals inside the factory-generated `install` command body.

## Deviations from Plan

None across all three plans — each executed exactly as written.

## Deferred Items

None.

## Known Stubs

None introduced by this phase.

## Self-Check: PASSED

- logpose/main.py — modified across 3 commits, all audits pass
- Commits `c844030`, `157baf7`, `b6003bf` — all FOUND on main in order
- `pytest tests/test_palworld_golden.py -x` — 3 passed at every commit boundary
- `python tests/test_palworld_golden.py` — exit 0 after final commit
- Per-plan summaries written: 03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md
- Phase-level summary (this file): 03-SUMMARY.md
