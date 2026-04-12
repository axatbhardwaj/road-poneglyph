---
phase: 4
verified: 2026-04-13
status: human_needed
score: 4/5 must-haves verified (SC#1, SC#3-static, SC#4, SC#5 PASS; SC#2 + SC#3-pkcheck DEFERRED to Phase 5 VM sweep)
overrides_applied: 0
deferred:
  - truth: "`logpose palworld install --port 8211 --players 32 --start` on a fresh Debian 12 VM installs, starts, and advertises the server with zero sudo prompts — identical UX to v0.1.19"
    addressed_in: "Phase 5"
    evidence: "Phase 5 VM sweep per 04-RESEARCH Assumption A6 + ROADMAP Phase 5 success criteria rollup; Phase 4 SUMMARY explicitly flags SC#2 DEFERRED (Phase 5 VM E2E per Assumption A6)"
  - truth: "`pkcheck --action-id=org.freedesktop.systemd1.manage-units ... palserver.service` returns allowed result for installing user"
    addressed_in: "Phase 5"
    evidence: "Phase 5 VM sweep per 04-RESEARCH Assumption A6; ROADMAP Phase 5 SC#8 covers polkit/sudo posture verification; Phase 4 SUMMARY flags SC#3 pkcheck half DEFERRED pkcheck VM (Phase 5). Static half (template render matches golden byte-for-byte) is verified here."
human_verification:
  - test: "Fresh VM install E2E (Phase 4 SC#2 — deferred to Phase 5 VM sweep, documented for traceability)"
    expected: "`logpose palworld install --port 8211 --players 32 --start` on fresh Debian 12 installs, starts, and advertises server with zero sudo prompts — identical UX to v0.1.19."
    why_human: "Requires a fresh Debian 12 VM with network, root-capable user, and steamcmd network reachability; explicitly scheduled for Phase 5's consolidated VM sweep per 04-RESEARCH Assumption A6."
  - test: "pkcheck authorization on installed host (Phase 4 SC#3 second half — deferred to Phase 5)"
    expected: "After `logpose palworld install`, running `pkcheck --action-id=org.freedesktop.systemd1.manage-units --process $$ --detail unit palserver.service` as the installing user returns an allowed result (exit 0)."
    why_human: "Requires polkit daemon on a real Linux host with the rule installed to /etc/polkit-1/rules.d/40-logpose.rules and polkit service restarted — scheduled for Phase 5 VM sweep."
---

# Phase 4: Typer Factory + Merged Polkit — Verification Report

**Phase Goal (ROADMAP.md):** The CLI dispatches game-first (`logpose palworld <verb>`) via a factory-built sub-app loop, and a single merged polkit rule file authorizes every known game service unit.

**Verified:** 2026-04-13
**Status:** human_needed (static slice PASSED; VM-gated criteria deferred to Phase 5)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `logpose --help`, `logpose palworld --help`, `logpose palworld install --help` each exit 0 and show expected sub-command tree; `--version` reports `importlib.metadata.version("logpose-launcher")` | ✓ VERIFIED | `.venv/bin/logpose --help` exit 0 → shows `palworld` sub-app; `.venv/bin/logpose --version` exit 0 → `logpose 0.1.19`; `palworld --help` lists all 9 verbs; `palworld install --help` shows `--port [default: 8211]`, `--players [default: 32]`, `--start`. CliRunner smoke matrix passes 5/5. |
| 2 | `logpose palworld install --port 8211 --players 32 --start` on fresh Debian 12 VM installs, starts, advertises zero sudo prompts — identical UX to v0.1.19 | ⏸ DEFERRED | Addressed in Phase 5 per 04-RESEARCH Assumption A6; Phase 4 SUMMARY explicitly tags SC#2 DEFERRED. Static precursors (install command exists, flags correct, factory closes over spec, polkit + service file writes wired) all verified. |
| 3 | `40-logpose.rules` generated from `40-logpose.rules.template` via JS `units = [...]; indexOf(...)` driven by `GAMES.values()`; `pkcheck` returns allowed | ◐ PARTIAL (static half VERIFIED; pkcheck DEFERRED) | Template (`logpose/templates/40-logpose.rules.template`) uses `var units = [{units}]; units.indexOf(...)` pattern; `_setup_polkit(user)` builds units via `", ".join(f'"{spec.service_name}.service"' for spec in GAMES.values())` (line 219); writes to `/etc/polkit-1/rules.d/40-logpose.rules`; byte-diff test `test_polkit_rule_byte_identical_to_v0_2_0_golden` passes. pkcheck VM verification deferred to Phase 5. |
| 4 | Interactive `logpose palworld edit-settings` uses shared Rich-table + prompt-by-name editor via `SettingsAdapter`; UX unchanged from v0.1.19 | ✓ VERIFIED | `main.py:478-503` — factory `edit_settings` dispatches `spec.settings_adapter.parse/save` through closure, uses shared `_interactive_edit_loop` + `_display_settings` (Rich table, line 302). `--help` exits 0. UX parity preserved by closure over `spec.settings_path` + `spec.settings_adapter`. |
| 5 | All error exits use `raise typer.Exit(code=1)`; no `sys.exit(1)` in `logpose/main.py` | ✓ VERIFIED | `grep -c 'sys\.exit' logpose/main.py` → 0. `grep -c 'raise typer.Exit' logpose/main.py` → 8 (1 clean-quit `Exit()` in `_interactive_edit_loop`, 7 error `Exit(code=1)` across `_get_template`, `_run_command`, `_create_settings_from_default`, factory `install` root check, factory `edit-settings` parse + save paths, `_version_cb`). |

**Score:** 4/5 truths VERIFIED (SC#1, SC#4, SC#5 full pass; SC#3 static half pass); SC#2 and SC#3 pkcheck half DEFERRED to Phase 5 per 04-RESEARCH Assumption A6.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | SC#2 install E2E on fresh Debian 12 VM | Phase 5 | 04-RESEARCH Assumption A6; Phase 4 SUMMARY flags SC#2 DEFERRED |
| 2 | SC#3 pkcheck VM verification | Phase 5 | ROADMAP Phase 5 SC#8 polkit/sudo posture; Phase 4 SUMMARY flags pkcheck half DEFERRED |

### Required Artifacts

| Artifact | Expected | Exists | Substantive | Wired | Data-Flow | Status |
|----------|----------|--------|-------------|-------|-----------|--------|
| `logpose/main.py` — `_build_game_app(spec)` factory | Closure-bound factory producing Typer sub-app with 9 verbs | ✓ | ✓ (main.py:380-505, 125 lines) | ✓ (registered via `app.add_typer` loop lines 533-538) | ✓ (spec.service_name/app_id/server_dir/etc referenced as closure vars, no `GAMES["palworld"]` in body) | ✓ VERIFIED |
| `logpose/main.py` — `@app.callback()` + `--version` | Root callback with `--version` flag backed by importlib.metadata | ✓ | ✓ (`_version_cb` lines 508-517; `_root` lines 520-530) | ✓ (callback registered on `app`; `is_eager=True`) | ✓ (`logpose --version` prints `logpose 0.1.19`) | ✓ VERIFIED |
| `logpose/main.py` — `_setup_polkit(user)` single-arg | GAMES-driven unit list + placeholder audit | ✓ | ✓ (lines 214-228) | ✓ (called at line 424 from factory install) | ✓ (units built from `GAMES.values()` line 219; Formatter audit line 222) | ✓ VERIFIED |
| `logpose/templates/40-logpose.rules.template` | JS units/indexOf template with `{units}`/`{user}` placeholders, braces doubled | ✓ | ✓ (9 lines, correct `{{`/`}}` doubling, exactly two placeholders) | ✓ (read by `_setup_polkit` via `_get_template("40-logpose.rules.template")`) | ✓ (renders to golden byte-for-byte) | ✓ VERIFIED |
| `tests/test_palworld_golden.py` — 4th test | `test_polkit_rule_byte_identical_to_v0_2_0_golden` | ✓ | ✓ (lines 106-126; also wired in `__main__` script path lines 172-179) | ✓ (pytest discovers + passes) | ✓ (renders template, compares to golden) | ✓ VERIFIED |
| `tests/golden/40-logpose.rules.v0_2_0` | Byte oracle for polkit render (Palworld-only GAMES + user="foo") | ✓ | ✓ (8 lines, balanced braces, no `{{`/`}}` leakage, contains `"palserver.service"` + `user === "foo"`) | ✓ (read by test 4) | ✓ (matches render byte-for-byte) | ✓ VERIFIED |
| `logpose/templates/palserver.rules.template` | Removed (package asset) | ✓ NOT PRESENT (correctly removed via git rename to 40-logpose.rules.template) | N/A | N/A | N/A | ✓ VERIFIED |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `main.py` module scope | `app` root Typer | `for _key, _spec in GAMES.items(): app.add_typer(_build_game_app(_spec), name=_key, help=f"Manage {_spec.display_name}.")` | ✓ WIRED | Lines 533-538; `grep -c 'app.add_typer(' main.py` → 1 |
| `_build_game_app(spec)` | `spec.*` fields (closure) | Closure capture of `spec` parameter in 9 inner `@sub.command` bodies | ✓ WIRED | `spec.service_name`, `spec.app_id`, `spec.server_dir`, `spec.post_install_hooks`, `spec.binary_rel_path`, `spec.settings_adapter`, `spec.settings_path`, `spec.default_settings_path`, `spec.settings_section_rename`, `spec.display_name`, `spec.key` all appear inside factory body. No `GAMES["palworld"]` or hardcoded `2394010`/`"palserver"` inside factory body. |
| `_root` callback | `importlib.metadata.version("logpose-launcher")` | `_version_cb` with `is_eager=True` | ✓ WIRED | Lines 508-517; lazy import inside callback; `PackageNotFoundError` → `"unknown"` fallback present. Verified: `logpose --version` → `logpose 0.1.19`. |
| Factory `edit-settings` | `spec.settings_adapter.parse` / `spec.settings_adapter.save` | Closure dispatch (SET-03) | ✓ WIRED | Lines 482, 490, 500 — all three call sites reference `spec.settings_adapter.*` not `GAMES["palworld"]`. |
| Factory `install` | `_setup_polkit(Path.home().name)` | Single-arg call | ✓ WIRED | Line 424; `grep -c '_setup_polkit(Path.home().name)' main.py` → 1 |
| `_setup_polkit(user)` | `GAMES.values()` | `units = ", ".join(f'"{spec.service_name}.service"' for spec in GAMES.values())` | ✓ WIRED | Line 219; placeholder audit via `Formatter().parse(template)` on line 222 ensures template stays in sync with `{units,user}` contract. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_build_game_app(spec)` inner commands | `spec.*` attributes | Factory parameter bound at `add_typer` time from `GAMES.items()` | ✓ Yes — `GAMES["palworld"]` is a fully-populated `GameSpec` with real app_id=2394010, service_name="palserver", etc. | ✓ FLOWING |
| `_setup_polkit.units` | `spec.service_name` iteration | `GAMES.values()` registry | ✓ Yes — produces `"palserver.service"` (single entry today); Phase 5 adds `"arkserver.service"` | ✓ FLOWING |
| `_version_cb.v` | Package version | `importlib.metadata.version("logpose-launcher")` | ✓ Yes — resolves to `0.1.19` in installed venv (fallback `"unknown"` for uninstalled checkouts) | ✓ FLOWING |

### Behavioral Spot-Checks

| # | Behavior | Command | Result | Status |
|---|----------|---------|--------|--------|
| 1 | Byte-diff harness passes (4 tests) | `.venv/bin/pytest tests/test_palworld_golden.py -x` | `4 passed in 0.08s` | ✓ PASS |
| 2 | Root help includes palworld sub-app | `.venv/bin/logpose --help` | exit 0; "palworld   Manage Palworld." visible in Commands block | ✓ PASS |
| 3 | Version command prints version | `.venv/bin/logpose --version` | exit 0; `logpose 0.1.19` | ✓ PASS |
| 4 | Palworld sub-app lists 9 verbs | `.venv/bin/logpose palworld --help` | exit 0; install/start/stop/restart/status/enable/disable/update/edit-settings all shown | ✓ PASS |
| 5 | Install help shows Phase-4 flags | `.venv/bin/logpose palworld install --help` | exit 0; `--port [default: 8211]`, `--players [default: 32]`, `--start` | ✓ PASS |
| 6 | edit-settings help reachable | CliRunner `['palworld', 'edit-settings', '--help']` | exit 0 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plans | Description (paraphrase) | Status | Evidence |
|-------------|--------------|--------------------------|--------|----------|
| CLI-01 | 04-02 | Game-first dispatch is the only path | ✓ SATISFIED | Zero `@app.command` decorators in main.py; sole dispatch is via `app.add_typer(_build_game_app(...))` loop |
| CLI-02 | 04-01, 04-02 | `add_typer` loop over `GAMES` | ✓ SATISFIED | Lines 533-538 |
| CLI-03 | 04-02 | All 9 verbs under `logpose palworld` | ✓ SATISFIED | CLI help lists all 9 |
| CLI-04 | 04-01 | `help=` on root Typer + each sub-app | ✓ SATISFIED | Root `app = typer.Typer(help=..., no_args_is_help=True)`; `sub = typer.Typer(help=f"Manage {spec.display_name}...")`; `add_typer(..., help=...)` |
| CLI-05 | 04-04 | No `sys.exit(1)` — use `typer.Exit` | ✓ SATISFIED | `grep -c 'sys.exit' main.py` → 0; 8 `raise typer.Exit` sites |
| CLI-06 | 04-02 | `--version` via importlib.metadata + fallback | ✓ SATISFIED | `_version_cb` lines 508-517 |
| CLI-07 | 04-02 | `logpose --help` lists sub-commands with descriptions | ✓ SATISFIED | Verified via `logpose --help` output |
| PAL-07 | 04-02 | Install flags unchanged: `--port 8211`, `--players 32`, `--start` | ✓ SATISFIED | Verified via `logpose palworld install --help` |
| POL-01 | 04-03 | Single merged rule file `40-logpose.rules` | ✓ SATISFIED | `_setup_polkit` writes `/etc/polkit-1/rules.d/40-logpose.rules` |
| POL-02 | 04-03 | JS units/indexOf template with escaped braces | ✓ SATISFIED | Template content confirmed; Formatter audit at runtime |
| POL-03 | 04-03 | `_setup_polkit(user)` — no game-specific args | ✓ SATISFIED | Signature `_setup_polkit(user: str)`; reads `GAMES.values()` globally |
| POL-04 | 04-03 | Additive posture — old on-disk rule NOT deleted by code | ✓ SATISFIED | No code path removes `/etc/polkit-1/rules.d/40-palserver.rules`; Phase 6 owns README cleanup |
| POL-05 (static) | 04-03 | Rendered rule matches golden byte-for-byte | ✓ SATISFIED | Test 4 passes; VM pkcheck half DEFERRED to Phase 5 |
| SET-03 | 04-02 | edit-settings dispatches via SettingsAdapter | ✓ SATISFIED | Factory body uses `spec.settings_adapter.parse/save` via closure |
| PKG-08 (partial) | 04-04 | README Palworld slice updated to game-first examples | ✓ SATISFIED (per SUMMARY) | Plan 04-04 SUMMARY records README rewrite; commit 822dc4f touches README.md |
| E2E-02 | 04-04 | Byte-diff harness green throughout | ✓ SATISFIED | 4/4 tests passing |

No ORPHANED requirements detected — all 16 requirements declared across 04-01..04-04 plans' frontmatter are traced to code/test artifacts.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None |

Scans run:
- `sys\.exit` in `logpose/main.py` → 0 hits (correctly absent per CLI-05)
- `TODO|FIXME|XXX|HACK|PLACEHOLDER` in `logpose/main.py` → 0 hits
- Hardcoded `"palworld"`/`"palserver"`/`2394010` inside `_build_game_app` body → 0 hits (all such literals live only in the `GAMES = { "palworld": GameSpec(...) }` construction)
- `return null` / `return {}` / `return []` placeholder stubs → 0 hits
- `@app.command` decorators → 0 (correctly removed in Plan 04-02)

### Human Verification Required

1. **Fresh VM install E2E (Phase 4 SC#2 — deferred to Phase 5)**
   - Test: On a fresh Debian 12 VM, run `logpose palworld install --port 8211 --players 32 --start` as a non-root user.
   - Expected: steamcmd installs; PalServer downloads under `~/.steam/steam/steamapps/common/PalServer`; `palserver.service` is written to `/etc/systemd/system/`; `40-logpose.rules` is written to `/etc/polkit-1/rules.d/`; service starts; zero sudo prompts during `start/stop` subsequent verbs; UX parity with v0.1.19 preserved.
   - Why human: requires a fresh Debian 12 VM with network, user account, and steamcmd reachability; explicitly scheduled for Phase 5's consolidated VM sweep per 04-RESEARCH Assumption A6 and Phase 4 SUMMARY.

2. **pkcheck authorization on installed host (Phase 4 SC#3 pkcheck half — deferred to Phase 5)**
   - Test: After a successful `logpose palworld install`, as the installing user run `pkcheck --action-id=org.freedesktop.systemd1.manage-units --process $$ --detail unit palserver.service`.
   - Expected: exit 0 (allowed) without polkit prompt; `systemctl start/stop palserver` succeeds without sudo.
   - Why human: requires a real polkit daemon on Linux with the rule installed and polkit service restarted. Scheduled for Phase 5 VM sweep per ROADMAP Phase 5 SC#8.

### Gaps Summary

No unresolved gaps. The two outstanding items (SC#2 install E2E; SC#3 pkcheck VM verification) are explicitly scheduled for Phase 5 per 04-RESEARCH Assumption A6 and were accepted as deferrals by the planner when Phase 4 was decomposed. Static slices for both criteria (install command + flags + polkit template render) are verified here.

The deferred items are recorded in the `deferred:` frontmatter section and mirrored into `human_verification:` so the Phase 5 VM sweep has a traceable checklist.

## Pytest + CLI Smoke Results (Inline)

```
$ .venv/bin/pytest tests/test_palworld_golden.py -x
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0
rootdir: /root/personal/palworld-server-launcher
configfile: pyproject.toml
collected 4 items

tests/test_palworld_golden.py ....                                       [100%]

============================== 4 passed in 0.08s ===============================
```

```
$ .venv/bin/logpose --help      → exit 0 (lists `palworld   Manage Palworld.`)
$ .venv/bin/logpose --version   → exit 0, output: `logpose 0.1.19`
$ .venv/bin/logpose palworld --help → exit 0 (install/start/stop/restart/status/enable/disable/update/edit-settings)
$ .venv/bin/logpose palworld install --help → exit 0 (--port [8211], --players [32], --start)
```

## End-of-Phase Grep Audit

| Check | Expected | Actual |
|-------|----------|--------|
| `sys.exit` in `logpose/main.py` | 0 | 0 |
| `^@app.command` decorators | 0 | 0 |
| `@app.callback(` | 1 | 1 |
| `def _build_game_app(` | 1 | 1 |
| `app.add_typer(` | 1 | 1 |
| `_setup_polkit(Path.home().name)` call site | present | present (line 424) |
| `palserver.rules.template` / `40-palserver.rules` in code | 0 | 0 |
| `raise typer.Exit` in `logpose/main.py` | ≥ 5 | 8 |
| `GAMES.values()` in `_setup_polkit` | present | present (line 219) |

## Commits on HEAD (Phase 4)

| Plan | Commit | Subject |
|------|--------|---------|
| 04-01 | `3b1ad4c` | refactor(04-01): add _build_game_app factory + add_typer("palworld") alongside flat commands |
| 04-02 | `f623e78` | refactor(04-02): flip CLI to game-first (logpose palworld <verb>) + add --version |
| 04-03 | `a3e6a87` | refactor(04-03): merge polkit rule to 40-logpose.rules driven by GAMES.values() |
| 04-04 | `822dc4f` | chore(04-04): finish sys.exit → typer.Exit conversion + README Palworld CLI examples |

---

_Verified: 2026-04-13_
_Verifier: Claude (gsd-verifier)_
