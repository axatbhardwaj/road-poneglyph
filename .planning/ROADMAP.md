# Roadmap: logpose v0.2.0

**Milestone:** v0.2.0 — logpose rewrite (in-place rename + generalize + add ARK)
**Granularity:** coarse
**Created:** 2026-04-12
**Core Value:** One CLI, many games, zero sudo prompts — operators type `logpose <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box.

## Phases

- [x] **Phase 1: Rename + Hygiene** — `git mv` package to `logpose/`, update `pyproject.toml`, scrub tracked `*.egg-info/`, add `from __future__ import annotations`, pin deps for Python 3.8 compat ✅ 2026-04-12
- [x] **Phase 2: Parameterize Helpers (no GAMES dict yet)** — thread game-specific paths/dicts through helpers, wrap Palworld regex parser/saver as named functions, land byte-diff regression harness ✅ 2026-04-12
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

### Phase 2: Parameterize Helpers (no GAMES dict yet) ✅ Complete (2026-04-12)
**Goal**: Helper functions accept game-specific inputs as parameters (not module globals), and a byte-diff regression harness proves Palworld renders identically to v0.1.19 — the working oracle for every subsequent phase.
**Depends on**: Phase 1
**Status**: Passed static verification (3/3 static criteria). VM E2E (Criterion 4) deferred to Phase 5 per explicit ROADMAP wording and user direction. 19 atomic commits. Code review: clean. See `.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-VERIFICATION.md`.
**Requirements**: ARCH-04 (partial), PAL-03, PAL-04, PAL-09 (harness half), SET-01 prep, E2E-01 (also contributes to ARCH-05, ARCH-06, PAL-01, PAL-02, PAL-06)
**Success Criteria** (what must be TRUE):
  1. Palworld's `OptionSettings=(...)` regex parser is extracted into a named function `_palworld_parse(path) -> dict[str, str]`; the existing `should_quote` saver is extracted into `_palworld_save(path, values)`. Both are byte-equivalent to v0.1.19 on the fixture. ✅
  2. `_create_service_file`, `_fix_steam_sdk`, and the install/settings helpers accept explicit paths/dicts as arguments instead of reading module-level Palworld constants directly. ✅
  3. A byte-diff test script renders `palserver.service` against the fixed fixture (`user=foo`, `port=8211`, `players=32`) and asserts zero-diff against the v0.1.19 golden file; the script exits 0. ✅ (3 tests in `tests/test_palworld_golden.py`)
  4. Palworld end-to-end behavior (install → start → edit-settings → stop) is unchanged when exercised manually — no observable regression from parameterization. ⏭ Deferred to Phase 5 VM E2E.
**Plans**: 5/5 complete
- [x] 02-01-golden-fixture-and-harness-PLAN.md ✅
- [x] 02-02-extract-palworld-parse-save-PLAN.md ✅
- [x] 02-03-parameterize-helpers-PLAN.md ✅
- [x] 02-04-wire-typer-commands-PLAN.md ✅
- [x] 02-05-harness-real-render-path-PLAN.md ✅

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
**Plans**: 3 plans
- [ ] 03-01-add-dataclasses-and-games-registry-PLAN.md — Add SettingsAdapter + GameSpec dataclasses + GAMES["palworld"] registry alongside existing globals (no call-site changes)
- [ ] 03-02-dissolve-pal-globals-switch-call-sites-PLAN.md — Dissolve PAL_* module globals, rewire all @app.command() bodies to read GAMES["palworld"], delete _install_palworld wrapper (closes ARCH-04 + PAL-05)
- [ ] 03-03-wire-fix-steam-sdk-post-install-hook-PLAN.md — Replace direct _fix_steam_sdk call with spec.post_install_hooks iteration (closes PAL-08)

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
**Plans**: 4 plans
- [ ] 04-01-PLAN.md — Add _build_game_app factory + register palworld sub-app alongside flat commands
- [ ] 04-02-PLAN.md — Flip dispatch (delete flat commands, add --version callback, game-first only)
- [ ] 04-03-PLAN.md — Merge polkit to 40-logpose.rules driven by GAMES.values() + golden test
- [ ] 04-04-PLAN.md — Finish sys.exit → typer.Exit conversion + Palworld README CLI examples
**UI hint**: yes

### Phase 5: Add ARK Entry + E2E (arkmanager wrapper)
**Goal**: ARK: Survival Evolved joins the registry as a first-class game — but instead of re-implementing the install/start/stop/save pipeline natively, logpose wraps the mature `arkmanager` (ark-server-tools) Bash harness under the hood. `logpose ark <verb>` provides a uniform CLI on top of arkmanager, manages `/etc/arkmanager/instances/main.cfg`, and preserves Palworld's native path untouched. E2E verified on fresh Debian 12 (compat) and Debian 13 (primary per install record).
**Depends on**: Phase 4
**Pivot (2026-04-12):** Phase 5 pivots from native steamcmd + custom systemd unit + `GameUserSettings.ini` parser to arkmanager delegation. Rationale: arkmanager v1.6.68 already solves steamcmd self-update quirks, branch opt-outs (preaquatica), start/stop/backup/RCON, and works on both Debian and Ubuntu. Delegating preserves Palworld's symmetry while cutting scope. Install record at `docs/ark-install-reference.md` is the reference implementation.
**Requirements**: ARK-01..ARK-19 (ARK-14..ARK-19 added by the arkmanager pivot), SET-02, SET-04, POL-05 (ARK verification — may reduce since arkmanager uses `sudo -u steam`, not a systemd service owned by the installing user), PAL-09 (byte-diff second half), E2E-03, E2E-04
**Success Criteria** (what must be TRUE):
  1. `logpose ark install --map TheIsland --admin-password XXX --start` on a fresh Debian 12 or Debian 13 VM:
     - enables `contrib non-free` in apt sources (Debian only; Ubuntu already exposes these as `multiverse`),
     - adds i386 foreign architecture,
     - pre-accepts the `steam`/`steamcmd` EULA via `debconf-set-selections`,
     - installs apt deps (`steamcmd`, `libc6-i386`, `lib32gcc-s1`, `lib32stdc++6`, `curl`, `bzip2`, `tar`, `rsync`, `sed`, `perl-modules`, `lsof`),
     - creates the `steam` service user if absent (`useradd -m -s /bin/bash steam`),
     - installs arkmanager v1.6.68+ via the upstream netinstall.sh (`curl -sL https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/netinstall.sh | bash -s steam`),
     - runs `sudo -u steam arkmanager install --beta=preaquatica --validate` **twice** (first call self-updates steamcmd and exits 0 with zero payload — known quirk),
     - starts via `sudo -u steam arkmanager start`.
  2. `logpose ark install` materialises `/etc/arkmanager/instances/main.cfg` from `GAMES["ark"]` values (arkserverroot, serverMap, ark_SessionName, ark_Port, ark_QueryPort, ark_RCONEnabled, ark_RCONPort, ark_ServerPassword, ark_ServerAdminPassword, ark_MaxPlayers). Unrelated keys in `main.cfg` are preserved (in-place edit, not rewrite).
  3. `logpose ark edit-settings` edits `/etc/arkmanager/instances/main.cfg` via the shared Rich-table editor (same UX as Palworld's `edit-settings`). The arkmanager `ark_*` key set becomes the `SettingsAdapter` parse/save target. `GameUserSettings.ini` is NOT directly edited by logpose in this milestone (arkmanager owns it); `logpose ark edit-settings --game-ini` is deferred to a future milestone if needed.
  4. `logpose ark start|stop|restart|status|saveworld|backup|update` delegate to `sudo -u steam arkmanager <verb>` with return codes + last-line output surfaced to the user.
  5. Install flow validates map against arkmanager's supported set (`TheIsland`, `TheCenter`, `ScorchedEarth_P`, `Aberration_P`, `Extinction`, `Ragnarok`, `Valguero_P`, `CrystalIsles`, `LostIsland`, `Fjordur`, `Genesis`, `Genesis2`), probes ports 7777/udp, 7778/udp, 27015/udp, 27020/tcp via `ss -tuln` before install, and aligns the RCON triad in `main.cfg` (`ark_RCONEnabled=True` + `ark_RCONPort=<port>` + `ark_ServerAdminPassword=<pw>`). `--admin-password` is required (hidden prompt) or generated via `secrets.token_urlsafe(16)` only with an explicit `--generate-password` flag and printed once.
  6. `palserver.service` output remains byte-identical to v0.1.19 under the Phase 2 harness (Palworld path unchanged; only ARK is delegated to arkmanager).
  7. `logpose ark stop` completes a clean save within arkmanager's default timeout; RCON is reachable on the configured `ark_RCONPort`.
  8. **Polkit/sudo posture — ARK is different from Palworld.** arkmanager uses `sudo -u steam`, not a systemd service owned by the installing user. So POL-05 (sudo-less service management) applies to Palworld only in v0.2.0; ARK uses one-time `sudo -u steam` invocations that the installing user authorises via passwordless NOPASSWD entry (`<user> ALL=(steam) NOPASSWD: /usr/local/bin/arkmanager *`). `logpose ark install` drops this sudoers fragment in `/etc/sudoers.d/logpose-ark`. Documented in README and Phase 6 migration note.
  9. **Auto-start at boot is opt-in.** A systemd unit `arkserver.service` (thin wrapper: `ExecStart=/usr/bin/sudo -u steam /usr/local/bin/arkmanager start`, `ExecStop=/usr/bin/sudo -u steam /usr/local/bin/arkmanager stop`, `Type=forking` since arkmanager backgrounds the server, `RemainAfterExit=yes`) is created but **not enabled by default**. `logpose ark install --enable-autostart` opts in.
**Plans**: TBD
**UI hint**: yes
**Reference**: `docs/ark-install-reference.md` (working install record, 2026-04-12, Debian 13 trixie, preaquatica beta, arkmanager v1.6.68)

### Phase 6: Release Polish + PyPI
**Goal**: `logpose-launcher` v0.2.0 ships to PyPI with a verified wheel, the README reflects the multi-game CLI, and the v0.1.19 `palworld-server-launcher` release is left untouched.
**Depends on**: Phase 5
**Requirements**: PKG-07, PKG-08 (complete — migration note, per-game firewall ports, manual polkit uninstall), POL-04 (final README cleanup guidance), E2E-05, E2E-06
**Success Criteria** (what must be TRUE):
  1. A clean local build (`rm -rf build dist *.egg-info` then `python -m build`) produces a wheel whose `*.dist-info/METADATA` shows `Name: logpose-launcher` and `Version: 0.2.0`.
  2. TestPyPI dry-run publish succeeds; `pip install -i https://test.pypi.org/simple/ logpose-launcher` in a throwaway venv installs, and `logpose --help` post-install shows both `palworld` and `ark` sub-commands.
  3. `logpose-launcher` v0.2.0 is published to production PyPI; `palworld-server-launcher` v0.1.19 remains frozen and untouched.
  4. `README.md` includes: new `logpose palworld ...` / `logpose ark ...` examples for every verb, migration note for existing v0.1.19 users (new install, not upgrade), per-game firewall port reference (8211/UDP for Palworld; 7777/UDP game + 7778/UDP raw socket + 27015/UDP query + 27020/TCP RCON for ARK), manual polkit cleanup instructions for the old `40-palserver.rules`, and — new for v0.2.0 — ARK's sudoers fragment at `/etc/sudoers.d/logpose-ark` and the opt-in `arkserver.service` systemd unit (disabled by default; enabled via `--enable-autostart` at install time).
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
| **5 — ARK + E2E (arkmanager wrapper)** | **Yes** | **MEDIUM** | Research scope narrowed by the 2026-04-12 pivot. Still needed: arkmanager netinstall idempotency on re-run, arkmanager config format edge cases (quoted vs unquoted values, comment preservation), `main.cfg` line-ending normalisation, `sudo -u steam arkmanager` exit-code semantics, Debian 12 vs Debian 13 i386 lib availability. Reference implementation already captured in `docs/ark-install-reference.md` — research validates edge cases, not approach. |
| 6 — Release Polish | No | — | Standard PyPI publishing; TestPyPI flow is well-trodden. |

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Rename + Hygiene | 0/0 | ✅ Complete | 2026-04-12 |
| 2. Parameterize Helpers (no GAMES dict yet) | 5/5 | ✅ Complete | 2026-04-12 |
| 3. Introduce GameSpec + GAMES dict (Palworld only) | 0/0 | Not started | — |
| 4. Typer Factory + Merged Polkit | 0/4 | Not started | — |
| 5. Add ARK Entry + E2E | 0/0 | Not started | — |
| 6. Release Polish + PyPI | 0/0 | Not started | — |

## Coverage

- v1 requirements: **62 / 62 mapped** ✓ (56 original + ARK-14..ARK-19 added by the 2026-04-12 arkmanager pivot)
- Orphaned requirements: **0** ✓
- Phases without requirements: **0** ✓
- Source of truth: `.planning/REQUIREMENTS.md` Traceability table

---
*Roadmap created: 2026-04-12*
*Last updated: 2026-04-12 after initialization*
