# Roadmap: logpose v0.2.0

**Milestone:** v0.2.0 — logpose rewrite (in-place rename + generalize + add ARK)
**Granularity:** coarse
**Created:** 2026-04-12
**Core Value:** One CLI, many games, zero sudo prompts — operators type `logpose <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box.

## Phases

- [x] **Phase 1: Rename + Hygiene** — `git mv` package to `logpose/`, update `pyproject.toml`, scrub tracked `*.egg-info/`, add `from __future__ import annotations`, pin deps for Python 3.8 compat ✅ 2026-04-12
- [ ] **Phase 2: Parameterize Helpers (no GAMES dict yet)** — thread game-specific paths/dicts through helpers, wrap Palworld regex parser/saver as named functions, land byte-diff regression harness
- [ ] **Phase 3: Introduce GameSpec + GAMES dict (Palworld only)** — define `GameSpec` + `SettingsAdapter` dataclasses, fold all `PAL_*` module globals into `GAMES["palworld"]`, every helper takes `game: str`
- [ ] **Phase 4: Typer Factory + Merged Polkit** — `_build_game_app(spec)` factory + `add_typer` loop, `no_args_is_help=True`, `typer.Exit`, `--version` callback, merged `40-logpose.rules` template, CLI smoke-test matrix
- [ ] **Phase 5: Add ARK Entry + E2E** — `GAMES["ark"]`, `arkserver.service.template`, `_ark_parse`/`_ark_save` with correct `RawConfigParser` constructor, full ARK install flow (10 flags), per-game apt deps, sdk32+sdk64 fix, fresh-VM E2E
- [ ] **Phase 6: Release Polish + PyPI** — clean build, wheel metadata verification, TestPyPI dry-run + throwaway-venv install, production PyPI publish as `logpose-launcher`, final README pass

## Phase Details

### Phase 1: Rename + Hygiene ✅ Complete (2026-04-12)
**Goal**: Repo carries the `logpose` identity cleanly — package path, distribution name, pinned deps, and tree hygiene all align before any behavioral change.
**Depends on**: Nothing (first phase)
**Status**: Passed — 4 atomic commits (7257387, 10add52, 643e1c6, a6c2b3c). See `.planning/phases/01-rename-hygiene/01-SUMMARY.md`.
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05, PKG-06 (also contributes to ARCH-05, ARCH-06, PAL-01, PAL-02, PAL-06)
**Success Criteria** (what must be TRUE):
  1. Package directory is `logpose/` (history-preserved via `git mv`); `pyproject.toml` declares `name = "logpose-launcher"` with entry point `logpose = "logpose.main:app"` and pinned `typer>=0.9,<0.21`, `rich>=13.0,<14`.
  2. `palworld_server_launcher.egg-info/` is removed from git tracking; `.gitignore` covers `*.egg-info/`, `build/`, `dist/`.
  3. Every module in `logpose/` starts with `from __future__ import annotations`; `python -c "import logpose.main"` succeeds on Python 3.8.
  4. `palserver.service.template` and polkit template are byte-identical to v0.1.19; running the existing Palworld install path still produces the same service file.
**Plans**: TBD

### Phase 2: Parameterize Helpers (no GAMES dict yet)
**Goal**: Helper functions accept game-specific inputs as parameters (not module globals), and a byte-diff regression harness proves Palworld renders identically to v0.1.19 — the working oracle for every subsequent phase.
**Depends on**: Phase 1
**Requirements**: ARCH-04 (partial), PAL-03, PAL-04, PAL-09 (harness half), SET-01 prep, E2E-01 (also contributes to ARCH-05, ARCH-06, PAL-01, PAL-02, PAL-06)
**Success Criteria** (what must be TRUE):
  1. Palworld's `OptionSettings=(...)` regex parser is extracted into a named function `_palworld_parse(path) -> dict[str, str]`; the existing `should_quote` saver is extracted into `_palworld_save(path, values)`. Both are byte-equivalent to v0.1.19 on the fixture.
  2. `_create_service_file`, `_fix_steam_sdk`, and the install/settings helpers accept explicit paths/dicts as arguments instead of reading module-level Palworld constants directly.
  3. A byte-diff test script renders `palserver.service` against the fixed fixture (`user=foo`, `port=8211`, `players=32`) and asserts zero-diff against the v0.1.19 golden file; the script exits 0.
  4. Palworld end-to-end behavior (install → start → edit-settings → stop) is unchanged when exercised manually — no observable regression from parameterization.
**Plans**: 5 plans
- [ ] 02-01-golden-fixture-and-harness-PLAN.md — Land the byte-diff regression harness with dual entrypoint, committed 323-byte golden fixture, and .gitattributes to preserve template EOF bytes
- [ ] 02-02-extract-palworld-parse-save-PLAN.md — Rename _parse_settings → _palworld_parse(path) and _save_settings → _palworld_save(path, settings) with verbatim bodies
- [ ] 02-03-parameterize-helpers-PLAN.md — Parameterize _run_steamcmd_update, _install_palworld, _fix_steam_sdk, _setup_polkit, _create_settings_from_default; split _create_service_file into _render_service_file + _write_service_file
- [ ] 02-04-wire-typer-commands-PLAN.md — Wire install, update, edit_settings Typer commands to call parameterized helpers with Palworld values threaded from module-scope constants
- [ ] 02-05-harness-real-render-path-PLAN.md — Extend harness with third test that imports _render_service_file and asserts byte-equality against golden (closes Pitfall 4)

### Phase 3: Introduce GameSpec + GAMES dict (Palworld only)
**Goal**: The `GameSpec` + `SettingsAdapter` dataclasses and the `GAMES` registry become the single source of truth for per-game configuration; all Palworld module-globals are dissolved into `GAMES["palworld"]`.
**Depends on**: Phase 2
**Requirements**: ARCH-01, ARCH-02, ARCH-03, ARCH-04 (complete), PAL-05, PAL-08 (also contributes to ARCH-05, ARCH-06, PAL-01, PAL-02, PAL-06)
**Success Criteria** (what must be TRUE):
  1. `GameSpec` is a frozen dataclass with all 14 fields (`key`, `display_name`, `app_id`, `server_dir`, `binary_rel_path`, `settings_path`, `default_settings_path`, `settings_section_rename`, `service_name`, `service_template_name`, `settings_adapter`, `post_install_hooks`, `apt_packages`, `steam_sdk_paths`, `install_options`); `SettingsAdapter` is a frozen dataclass with `parse` + `save` callables.
  2. `GAMES: dict[str, GameSpec]` is defined at module scope in `logpose/main.py` with exactly one entry (`"palworld"`); no `PAL_*` module-level constants remain.
  3. Every game-aware helper takes a required `game: str` (or `spec: GameSpec`) positional argument and reads Palworld values from `GAMES["palworld"]` — grepping for hardcoded `palserver`/`PalWorld`/`2394010` in helper bodies returns nothing.
  4. Palworld's section-rename (`[/Script/Pal.PalWorldSettings]` → `[/Script/Pal.PalGameWorldSettings]`) is expressed via `GameSpec.settings_section_rename`; `_fix_steam_sdk` is wired as a Palworld-only `post_install_hook`.
  5. Byte-diff harness from Phase 2 still exits 0 against the v0.1.19 golden file.
**Plans**: TBD

### Phase 4: Typer Factory + Merged Polkit
**Goal**: The CLI dispatches game-first (`logpose palworld <verb>`) via a factory-built sub-app loop, and a single merged polkit rule file authorizes every known game service unit.
**Depends on**: Phase 3
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, PAL-07, POL-01, POL-02, POL-03, POL-04 (additive behavior), POL-05 (Palworld verification), SET-03, PKG-08 (partial — README CLI examples), E2E-02
**Success Criteria** (what must be TRUE):
  1. `logpose --help`, `logpose palworld --help`, `logpose palworld install --help` each exit 0 and show the expected sub-command tree; `--version` reports the value from `importlib.metadata.version("logpose-launcher")`.
  2. `logpose palworld install --port 8211 --players 32 --start` on a fresh Debian 12 VM installs, starts, and advertises the server with zero sudo prompts — identical UX to v0.1.19.
  3. `40-logpose.rules` is generated from `40-logpose.rules.template` using a JS `units = [...]; indexOf(...)` pattern driven by `GAMES.values()`; `pkcheck --action-id=org.freedesktop.systemd1.manage-units --process $$ --detail unit palserver.service` returns an allowed result for the installing user.
  4. Interactive `logpose palworld edit-settings` uses the shared Rich-table + prompt-by-name editor dispatched through `SettingsAdapter`; UX is unchanged from v0.1.19.
  5. All error exits go through `raise typer.Exit(code=1)`; no `sys.exit(1)` remains in `logpose/main.py`.
**Plans**: TBD
**UI hint**: yes

### Phase 5: Add ARK Entry + E2E
**Goal**: ARK: Survival Evolved joins the registry as a first-class game — install, configure, start, stop, edit-settings, and E2E verification on a fresh Debian 12 VM all work end-to-end without sudo prompts.
**Depends on**: Phase 4
**Requirements**: ARK-01, ARK-02, ARK-03, ARK-04, ARK-05, ARK-06, ARK-07, ARK-08, ARK-09, ARK-10, ARK-11, ARK-12, ARK-13, SET-02, SET-04, POL-05 (ARK verification), PAL-09 (byte-diff second half), E2E-03, E2E-04
**Success Criteria** (what must be TRUE):
  1. `logpose ark install --map TheIsland --admin-password XXX --start` on a fresh Debian 12 VM installs required 32-bit apt deps (`lib32gcc-s1` with `lib32gcc1` fallback, `libc6-i386`, `libncurses5`, `libncursesw5`, `libsdl2-2.0-0`, `lib32stdc++6`), lays down `steamclient.so` in both `~/.steam/sdk32/` and `~/.steam/sdk64/` plus the Engine symlink, and brings `arkserver.service` up with zero sudo prompts.
  2. `arkserver.service.template` renders with `LimitNOFILE=100000`, `KillSignal=SIGINT`, `TimeoutStopSec=300`, `Type=exec`, direct-binary `ExecStart` (no shell wrapper); `palserver.service` output remains byte-identical to v0.1.19 under the Phase 2 harness.
  3. `logpose ark edit-settings` reads and writes `GameUserSettings.ini` via `RawConfigParser(strict=False, interpolation=None, allow_no_value=True, delimiters=("=",), comment_prefixes=(";","#"))` with `cp.optionxform = str`; CamelCase keys and untouched keys survive round-trip.
  4. Install flow validates map against the 12-map enum, probes port collisions via `ss -tuln` before install, writes SessionName only to `[SessionSettings]` (never launch args, 63-char soft warning enforced), and aligns the RCON triad (`RCONEnabled=True` + `RCONPort=<port>` + `ServerAdminPassword=<pw>` in INI AND `?RCONEnabled=True?RCONPort=<port>` in launch args); `--admin-password` is required (hidden prompt) or generated via `secrets.token_urlsafe(16)` only with an explicit flag and printed once.
  5. `systemctl stop arkserver` completes a clean save within `TimeoutStopSec`; `pkcheck` verifies both `palserver.service` and `arkserver.service` are managed sudo-lessly by the installing user; RCON is reachable on the configured `rcon_port`.
**Plans**: TBD
**UI hint**: yes

### Phase 6: Release Polish + PyPI
**Goal**: `logpose-launcher` v0.2.0 ships to PyPI with a verified wheel, the README reflects the multi-game CLI, and the v0.1.19 `palworld-server-launcher` release is left untouched.
**Depends on**: Phase 5
**Requirements**: PKG-07, PKG-08 (complete — migration note, per-game firewall ports, manual polkit uninstall), POL-04 (final README cleanup guidance), E2E-05, E2E-06
**Success Criteria** (what must be TRUE):
  1. A clean local build (`rm -rf build dist *.egg-info` then `python -m build`) produces a wheel whose `*.dist-info/METADATA` shows `Name: logpose-launcher` and `Version: 0.2.0`.
  2. TestPyPI dry-run publish succeeds; `pip install -i https://test.pypi.org/simple/ logpose-launcher` in a throwaway venv installs, and `logpose --help` post-install shows both `palworld` and `ark` sub-commands.
  3. `logpose-launcher` v0.2.0 is published to production PyPI; `palworld-server-launcher` v0.1.19 remains frozen and untouched.
  4. `README.md` includes: new `logpose palworld ...` / `logpose ark ...` examples for every verb, migration note for existing v0.1.19 users (new install, not upgrade), per-game firewall port reference (8211/UDP for Palworld; 7777/UDP, 27015/UDP, 27020/TCP for ARK), and manual polkit cleanup instructions for the old `40-palserver.rules`.
**Plans**: TBD

## Dependencies

Phases execute strictly in order — each phase's behavior contract depends on the prior phase's invariants:

| Phase | Depends On | Why |
|-------|------------|-----|
| 1 — Rename + Hygiene | — | First phase; prerequisite for every later path and wheel. |
| 2 — Parameterize Helpers | 1 | Parameterization touches files in `logpose/`; also needs scrubbed `egg-info` so no stale artifacts mask diffs. |
| 3 — GameSpec + GAMES | 2 | Dataclass migration requires helpers to already accept parameters; byte-diff harness from Phase 2 is the regression oracle. |
| 4 — Typer Factory + Polkit | 3 | Factory iterates over `GAMES` — dict must exist. Merged polkit rule reads unit names from `GAMES.values()`. |
| 5 — ARK + E2E | 4 | ARK sub-app is registered via the factory; merged polkit rule already covers unknown game keys; CLI shape is locked. |
| 6 — Release Polish | 5 | Distribution verification requires all runtime behavior complete; README migration note documents ARK flows. |

`ARCH-05` (no `BaseGame`, no `core/` split) and `ARCH-06` (game-agnostic helper signatures unchanged) are invariants enforced across Phases 1–5. `PAL-01`, `PAL-02`, `PAL-06` (Palworld byte-compat) are continuous invariants checked by the Phase 2 harness at every phase boundary.

## Research Hooks

| Phase | Research Needed? | Priority | Notes |
|-------|------------------|----------|-------|
| 1 — Rename + Hygiene | No | — | Mechanical: `git mv`, `pyproject.toml` edits, `.gitignore` entries. |
| 2 — Parameterize Helpers | No | — | Byte-diff harness is the only novelty; spec already captured in `research/ARCHITECTURE.md`. |
| 3 — GameSpec + GAMES | No | — | Schema fully specified in `research/ARCHITECTURE.md`. |
| 4 — Typer Factory + Polkit | Low | Low | Brief verification on Debian 12 of polkit JS array merge under `str.format()`; fallback to two-file rule documented as exit-criteria option. |
| **5 — ARK + E2E** | **Yes** | **HIGH** | Recommend `/gsd-research-phase` during planning: confirm exact 32-bit apt package names per target distro (Debian 12 vs Ubuntu 22.04+), current-year ARK signal handling on `SIGINT`, BattlEye default state, `[SessionSettings]` vs `[ServerSettings]` key placement, RCON port convention. Six of the top ten risks concentrate in this phase. |
| 6 — Release Polish | No | — | Standard PyPI publishing; TestPyPI flow is well-trodden. |

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Rename + Hygiene | 0/0 | Not started | — |
| 2. Parameterize Helpers (no GAMES dict yet) | 0/5 | Planned | — |
| 3. Introduce GameSpec + GAMES dict (Palworld only) | 0/0 | Not started | — |
| 4. Typer Factory + Merged Polkit | 0/0 | Not started | — |
| 5. Add ARK Entry + E2E | 0/0 | Not started | — |
| 6. Release Polish + PyPI | 0/0 | Not started | — |

## Coverage

- v1 requirements: **56 / 56 mapped** ✓
- Orphaned requirements: **0** ✓
- Phases without requirements: **0** ✓
- Source of truth: `.planning/REQUIREMENTS.md` Traceability table

---
*Roadmap created: 2026-04-12*
*Last updated: 2026-04-12 after initialization*
