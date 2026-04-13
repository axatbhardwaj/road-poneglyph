---
phase: 04-typer-factory-merged-polkit
subsystem: logpose.main (CLI factory + merged polkit)
tags: [typer, factory, game-first, polkit, version, exit-codes, readme]
requirements: [CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, PAL-07, POL-01, POL-02, POL-03, POL-04, POL-05, SET-03, PKG-08, E2E-02]
dependency_graph:
  requires:
    - "Phase 3 — GameSpec + GAMES registry (Palworld only)"
  provides:
    - "_build_game_app(spec) -> typer.Typer factory + add_typer loop over GAMES"
    - "Game-first CLI dispatch (logpose <game> <verb>); flat commands removed"
    - "Root --version callback backed by importlib.metadata.version('logpose-launcher')"
    - "Merged 40-logpose.rules.template driven by GAMES.values() with JS units/indexOf pattern"
    - "Single-arg _setup_polkit(user) with Formatter placeholder audit"
    - "Fourth byte-diff golden (tests/golden/40-logpose.rules.v0_2_0) locking polkit template"
    - "Zero sys.exit in logpose/main.py — typer.Exit used throughout"
    - "README Palworld examples in logpose palworld <verb> form + logpose-launcher dist name"
  affects:
    - "Phase 5 — ARK entry slots into GAMES with zero main.py scaffolding edits"
    - "Phase 6 — README migration note + ARK firewall ports + polkit cleanup guidance"
tech_stack:
  added:
    - "importlib.metadata (stdlib) — version resolution via dist metadata"
    - "string.Formatter (stdlib) — placeholder audit tripwire for polkit template"
  patterns:
    - "Factory pattern: _build_game_app(spec) closes over spec — safe for add_typer loop over GAMES"
    - "JS units/indexOf merged polkit rule (str.format + brace doubling)"
    - "typer.Exit(code=1) for error exits; typer.Exit() for clean quit (Pitfall 6 discipline)"
    - "--version flag with is_eager=True + PackageNotFoundError fallback"
key_files:
  created:
    - logpose/templates/40-logpose.rules.template
    - tests/golden/40-logpose.rules.v0_2_0
    - .planning/phases/04-typer-factory-merged-polkit/04-01-SUMMARY.md
    - .planning/phases/04-typer-factory-merged-polkit/04-02-SUMMARY.md
    - .planning/phases/04-typer-factory-merged-polkit/04-03-SUMMARY.md
    - .planning/phases/04-typer-factory-merged-polkit/04-04-SUMMARY.md
    - .planning/phases/04-typer-factory-merged-polkit/04-SUMMARY.md
  modified:
    - logpose/main.py
    - logpose/templates/CLAUDE.md
    - tests/test_palworld_golden.py
    - README.md
  deleted:
    - logpose/templates/palserver.rules.template
decisions:
  - "Four atomic commits (additive factory, dispatch flip, polkit merge, sys.exit+README) preserved byte-diff harness green at every boundary (3 → 3 → 4 → 4 passed)."
  - "Factory body references spec closure parameter — never GAMES['palworld']. Phase 5's ARK entry slots into the same factory with zero edits to the factory body."
  - "Typer 0.16 + @app.callback() + no_args_is_help=True exits 2 on bare logpose invocation (Click 'no command = usage error' convention). Help text is still printed; deviation accepted vs. plan truth 'exits 0'."
  - "Placeholder audit via string.Formatter uses assert (programmer-error tripwire) — acceptable per Pitfall 4 rationale."
  - "Old on-disk /etc/polkit-1/rules.d/40-palserver.rules is NOT deleted by code (POL-04 additive posture). Polkit merges across rule files; README cleanup guidance lands in Phase 6."
  - "README kept minimal — ARK examples and v0.1.19 migration notes deferred to Phase 5/6 per PKG-08 partial scope."
metrics:
  duration: "~25 min (4 plans)"
  completed: "2026-04-13"
  plans_complete: 4
  total_commits: 4
  files_modified: 4
  files_created: 2
  files_deleted: 1
---

# Phase 4: Typer Factory + Merged Polkit — Summary

Four atomic commits flipped the CLI from flat `logpose <verb>` to game-first `logpose palworld <verb>` via a closure-safe `_build_game_app(spec)` factory and an `add_typer` loop over `GAMES`, merged the per-game polkit rule into a single `GAMES.values()`-driven `40-logpose.rules` template, completed the `sys.exit → typer.Exit` conversion, and updated the README to the new CLI surface. The byte-diff harness grew from 3 to 4 tests (added `40-logpose.rules` golden) and stayed green at every boundary.

## What Was Done

### Plan 04-01 (commit `3b1ad4c`) — Add `_build_game_app` factory + add_typer (additive)

Added `_build_game_app(spec: GameSpec) -> typer.Typer` with nine inner `@sub.command()` verbs (install/start/stop/restart/status/enable/disable/update/edit-settings), each binding `spec.*` via closure (not re-reading `GAMES`). Registered via `for _key, _spec in GAMES.items(): app.add_typer(...)` at module scope. Existing nine flat `@app.command()` decorators left untouched — both dispatch shapes worked in parallel. Factory install uses `typer.Exit(code=1)` for root-check (first typer.Exit in the module). Closes CLI-02 + CLI-04 (partial — sub-app half).

### Plan 04-02 (commit `f623e78`) — Flip dispatch to game-first + --version

Deleted all nine flat `@app.command()` decorators. Added `_version_cb` + `@app.callback()` with `--version` flag (is_eager=True) backed by `importlib.metadata.version("logpose-launcher")` with `PackageNotFoundError` fallback to `"unknown"`. Upgraded root `app = typer.Typer(help=..., no_args_is_help=True)`. Closes CLI-01, CLI-03, CLI-06, CLI-07, PAL-07, SET-03.

### Plan 04-03 (commit `a3e6a87`) — Merge polkit to 40-logpose.rules + golden test

Created `logpose/templates/40-logpose.rules.template` with JS `var units = [...]; units.indexOf(...)` pattern and `{units}`/`{user}` placeholders. Refactored `_setup_polkit(user: str)` to single-arg — reads unit list globally from `GAMES.values()` via `", ".join(f'"{spec.service_name}.service"' ...)`. Added placeholder audit via `string.Formatter().parse`. Updated factory install call-site. Deleted `logpose/templates/palserver.rules.template`. Added `tests/golden/40-logpose.rules.v0_2_0` + fourth byte-diff test `test_polkit_rule_byte_identical_to_v0_2_0_golden`. Updated `logpose/templates/CLAUDE.md`. Closes POL-01, POL-02, POL-03, POL-04, POL-05 (static half).

### Plan 04-04 (commit `822dc4f`) — Finish sys.exit → typer.Exit + README Palworld examples

Converted remaining four `sys.exit` sites: `_get_template`, `_run_command`, `_create_settings_from_default` → `raise typer.Exit(code=1)`; `_interactive_edit_loop` quit → `raise typer.Exit()` (no code). `import sys` retained (9 `sys.stderr` sites). Rewrote `README.md` to use `logpose palworld <verb>` form, `pip install logpose-launcher`, merged polkit rule mention, `logpose --version` example. Closes CLI-05 (fully), PKG-08 (partial — Palworld slice).

## Commit Ledger

| Plan  | Commit    | Subject                                                                                      | Harness  |
| ----- | --------- | -------------------------------------------------------------------------------------------- | -------- |
| 04-01 | `3b1ad4c` | `refactor(04-01): add _build_game_app factory + add_typer("palworld") alongside flat commands` | 3 passed |
| 04-02 | `f623e78` | `refactor(04-02): flip CLI to game-first (logpose palworld <verb>) + add --version`          | 3 passed |
| 04-03 | `a3e6a87` | `refactor(04-03): merge polkit rule to 40-logpose.rules driven by GAMES.values()`            | 4 passed |
| 04-04 | `822dc4f` | `chore(04-04): finish sys.exit → typer.Exit conversion + README Palworld CLI examples`       | 4 passed |

## Phase 4 Success Criteria — Final Status

| # | Criterion                                                                                                                  | Status                      |
| - | -------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| 1 | `logpose --help`, `logpose palworld --help`, `logpose palworld install --help` exit 0; `--version` via importlib.metadata | PASS (static/CLI matrix)    |
| 2 | `logpose palworld install --port 8211 --players 32 --start` on fresh Debian 12 — zero sudo prompts, identical UX to v0.1.19 | DEFERRED (Phase 5 VM E2E per Assumption A6) |
| 3 | `40-logpose.rules` generated from template via `units = [...]; indexOf(...)` from `GAMES.values()`; `pkcheck` allowed result | PASS static / DEFERRED pkcheck VM (Phase 5) |
| 4 | Interactive `logpose palworld edit-settings` uses shared Rich-table editor via `SettingsAdapter`; UX unchanged            | PASS                        |
| 5 | All error exits use `raise typer.Exit(code=1)`; no `sys.exit(1)` in `logpose/main.py`                                     | PASS (grep count = 0)       |

## Grep Audit (end-of-phase)

| Check                                                | Expected      | Actual        |
| ---------------------------------------------------- | ------------- | ------------- |
| `sys.exit` in `logpose/main.py`                      | 0             | 0             |
| `^@app\.command` decorators                          | 0             | 0             |
| `@app.callback(`                                     | 1             | 1             |
| `def _build_game_app(`                               | 1             | 1             |
| `app.add_typer(`                                     | 1             | 1             |
| `_setup_polkit(Path.home().name)`                    | present       | present       |
| `palserver.rules.template` / `40-palserver.rules` refs in code | 0   | 0             |

## Byte-Diff Harness Count

- **Before Phase 4:** 3 tests (palserver.service template byte-diff, v0.1.19 tag paranoia, `_render_service_file` real-path).
- **After Phase 4:** 4 tests — added `test_polkit_rule_byte_identical_to_v0_2_0_golden` (locks `40-logpose.rules.template` render against drift).
- **Status:** 4/4 green throughout Phase 4. Palworld service template + golden UNCHANGED (PAL-02 continuous invariant preserved).

## Invariants Preserved

- `palserver.service.template` byte-identical to v0.1.19 (PAL-02).
- Palworld's `OptionSettings` parse/save behavior unchanged (PAL-03, PAL-04).
- Byte-diff harness green after every commit.
- Python 3.8 floor honored — no PEP-604 unions, no `match`, no `str.removeprefix` introduced (PKG-04).
- `_repair_package_manager` untouched.
- On-disk `/etc/polkit-1/rules.d/40-palserver.rules` NOT deleted by code (POL-04).

## Known Deviations

### Non-blocking: `logpose` bare invocation exit code (Plan 04-02)

Typer 0.16 + `@app.callback()` + `no_args_is_help=True` exits 2 on bare invocation (Click "no command given = usage error" convention). Help text is still printed. Plan truth "exits 0 via no_args_is_help=True" is a version-dependent behavior mismatch; observable UX (help shown on bare invoke) is preserved.

### Non-blocking: git rename detection (Plan 04-03)

git detected `palserver.rules.template` → `40-logpose.rules.template` as a 68%-similarity rename; commit shows `R` status line instead of separate `A` + `D`. Semantically identical to plan intent.

## Handoff to Phase 5 (Add ARK Entry + E2E, arkmanager wrapper)

- Adding `GAMES["ark"]` is a single-file edit to `logpose/main.py` — the factory + registration loop + merged polkit rule auto-absorb it.
- **Re-capture golden:** when `GAMES["ark"]` is added, `test_polkit_rule_byte_identical_to_v0_2_0_golden` will fail. Phase 5 re-captures `tests/golden/40-logpose.rules.v0_2_0` (or renames the fixture) with the ARK unit slotted in.
- **ARK path differs from Palworld** per ROADMAP Phase 5 pivot (2026-04-12): ARK wraps `arkmanager` via `sudo -u steam` rather than a systemd service owned by the installing user. Polkit posture applies to Palworld only; ARK uses `/etc/sudoers.d/logpose-ark` NOPASSWD fragment.
- **VM-gated Phase 4 criteria (SC #2 install E2E, SC #3 `pkcheck`)** roll up into Phase 5's full VM sweep per 04-RESEARCH Assumption A6.
- **Phase 6 leftovers from PKG-08:** README migration note for v0.1.19 users, per-game firewall port reference for ARK, manual polkit cleanup instructions for old `40-palserver.rules`.

## Self-Check: PASSED

- All four SUMMARY files present.
- All four commits on HEAD: `3b1ad4c`, `f623e78`, `a3e6a87`, `822dc4f`.
- `logpose/templates/40-logpose.rules.template` and `tests/golden/40-logpose.rules.v0_2_0` exist; `logpose/templates/palserver.rules.template` removed.
- Byte-diff harness 4/4 green.
- End-of-phase grep audits all pass.
