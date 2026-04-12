# Requirements: logpose v0.2.0

**Defined:** 2026-04-12
**Core Value:** One CLI, many games, zero sudo prompts — operators type `logpose <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box.

## v1 Requirements (v0.2.0 milestone)

Requirements for initial `logpose-launcher` release on PyPI.

### Packaging & Distribution

- [ ] **PKG-01**: Package directory renamed from `palworld_server_launcher/` to `logpose/` (via `git mv` to preserve history)
- [ ] **PKG-02**: `pyproject.toml` updated — `name = "logpose-launcher"`, `description` reflects multi-game scope, `[project.scripts]` entry `logpose = "logpose.main:app"`, `[tool.setuptools] packages = ["logpose"]`, `[tool.setuptools.package-data] "logpose" = ["templates/*"]`
- [ ] **PKG-03**: Dependencies pinned in `pyproject.toml` — `typer>=0.9,<0.21`, `rich>=13.0,<14` (Typer 0.21 dropped Python 3.8 on 2025-12-25)
- [ ] **PKG-04**: Python 3.8+ floor preserved via `requires-python = ">=3.8"`
- [ ] **PKG-05**: `from __future__ import annotations` added to every Python module in `logpose/` (PEP-585 generics work on Python 3.8)
- [ ] **PKG-06**: Tracked `palworld_server_launcher.egg-info/` removed from git via `git rm -r --cached`; `*.egg-info/`, `build/`, `dist/` added to `.gitignore`
- [ ] **PKG-07**: Published to PyPI as `logpose-launcher` v0.2.0; old `palworld-server-launcher` v0.1.19 untouched on PyPI
- [ ] **PKG-08**: README updated with new CLI examples for both games, migration note for existing v0.1.19 users, per-game firewall port reference, manual polkit cleanup instructions

### Core Architecture

- [ ] **ARCH-01**: `GameSpec` dataclass defined — frozen, fields: `key`, `display_name`, `app_id`, `server_dir`, `binary_rel_path`, `settings_path`, `default_settings_path` (Optional), `settings_section_rename` (Optional tuple), `service_name`, `service_template_name`, `settings_adapter`, `post_install_hooks`, `apt_packages`, `steam_sdk_paths`, `install_options`
- [ ] **ARCH-02**: `SettingsAdapter` dataclass defined — frozen, fields: `parse: Callable[[Path], dict[str, str]]`, `save: Callable[[Path, dict[str, str]], None]`
- [ ] **ARCH-03**: `GAMES: dict[str, GameSpec]` registry defined at module scope in `logpose/main.py`, keyed by game name (`"palworld"`, `"ark"`)
- [ ] **ARCH-04**: All helper functions (`_run_steamcmd_update`, `_fix_steam_sdk`, `_create_service_file`, `_install_game`, `_edit_settings`) take a `game: str` positional argument (or `spec: GameSpec`) and read game-specific values from the `GAMES` dict — no game-specific module-level constants
- [ ] **ARCH-05**: No `BaseGame` class, no `core/` module split, no `games/` submodules — everything lives in `logpose/main.py` and `logpose/templates/`
- [ ] **ARCH-06**: `_run_command`, `_install_steamcmd`, `_repair_package_manager` signatures unchanged from v0.1.19 (game-agnostic helpers stay as-is)

### CLI Structure

- [ ] **CLI-01**: Typer root app dispatches game-first — `logpose palworld <verb>`, `logpose ark <verb>`
- [ ] **CLI-02**: Per-game sub-app built via factory function `_build_game_app(spec: GameSpec) -> typer.Typer` registered via `app.add_typer(sub, name=spec.key)` in a loop over `GAMES`
- [ ] **CLI-03**: Every existing Palworld verb available per game: `install`, `start`, `stop`, `restart`, `status`, `enable`, `disable`, `update`, `edit-settings`
- [ ] **CLI-04**: Root + sub-apps set `no_args_is_help=True`; `help=` set on every `Typer()` and `add_typer()` call
- [ ] **CLI-05**: Error exits use `raise typer.Exit(code=1)` instead of `sys.exit(1)` (consistent Typer behavior, proper exception propagation)
- [ ] **CLI-06**: Root `@app.callback()` exposes `--version` via `importlib.metadata.version("logpose-launcher")`
- [ ] **CLI-07**: `logpose --help` shows both `palworld` and `ark` sub-commands with descriptions

### Palworld Behavioral Compatibility

- [ ] **PAL-01**: `palserver.service` filename unchanged
- [ ] **PAL-02**: `palserver.service.template` byte-identical to v0.1.19
- [ ] **PAL-03**: Palworld `OptionSettings=(...)` regex parser preserved verbatim as `_palworld_parse` function
- [ ] **PAL-04**: Palworld `_save_settings` quoting logic (`should_quote`) preserved verbatim as `_palworld_save` function
- [ ] **PAL-05**: Palworld settings section rename (`[/Script/Pal.PalWorldSettings]` → `[/Script/Pal.PalGameWorldSettings]`) preserved via `GameSpec.settings_section_rename`
- [ ] **PAL-06**: Palworld launch args identical (`-port={port} -players={players} -useperfthreads -NoAsyncLoadingThread -UseMultithreadForDS`)
- [ ] **PAL-07**: Palworld install flags identical: `--port` (default 8211), `--players` (default 32), `--start`
- [ ] **PAL-08**: `_fix_steam_sdk()` preserved as Palworld-only post-install hook (Palworld only needs `sdk64`)
- [ ] **PAL-09**: Byte-diff regression test — service file rendered with fixed fixture (`user=foo,port=8211,players=32`) must be byte-identical between v0.1.19 and v0.2.0 (zero-diff exit criterion)

### ARK Support (arkmanager wrapper — pivoted 2026-04-12)

**Pivot note:** v0.2.0 delegates ARK install/management to the third-party `arkmanager` (ark-server-tools) Bash harness. logpose wraps arkmanager; it does NOT re-implement steamcmd orchestration, direct systemd units, or `GameUserSettings.ini` editing for ARK. Reference: `docs/ark-install-reference.md`.

- [ ] **ARK-01**: `GAMES["ark"]` entry with `app_id=376030`, `server_dir="/home/steam/ARK"`, `binary_rel_path="ShooterGame/Binaries/Linux/ShooterGameServer"`, `settings_path="/etc/arkmanager/instances/main.cfg"` (arkmanager owns GameUserSettings.ini directly; logpose edits main.cfg), `service_name="arkserver"` (opt-in systemd wrapper), `display_name="ARK: Survival Evolved"`, `install_backend="arkmanager"`, `branch="preaquatica"` (required for current Linux builds with mod support)
- [ ] **ARK-02**: `arkserver.service.template` is a THIN wrapper around arkmanager: `Type=forking`, `RemainAfterExit=yes`, `ExecStart=/usr/bin/sudo -u steam /usr/local/bin/arkmanager start`, `ExecStop=/usr/bin/sudo -u steam /usr/local/bin/arkmanager stop`, `User=root` (needs root to sudo to steam). Disabled by default; enabled via `logpose ark install --enable-autostart`.
- [ ] **ARK-03**: Launch args are arkmanager-controlled (via `main.cfg` ark_* keys). logpose does NOT render a launch-args string directly. ARK-03 satisfied when main.cfg round-trip with sample values produces a valid `arkmanager status` after install.
- [ ] **ARK-04**: ARK SessionName is written to `main.cfg` as `ark_SessionName="..."` (arkmanager already handles the quoting/escaping correctly, even for names with spaces like `bunty's game`). The 63-char soft warning still applies at the CLI boundary.
- [ ] **ARK-05**: ARK install flags: `--map` (default `TheIsland`, validated against the 12-map enum), `--port` (default 7778 — arkmanager's raw socket; game port 7777 is implicit), `--query-port` (default 27015), `--rcon-port` (default 27020), `--players` (default 10 per the reference install; can be overridden up to 70), `--session-name` (default `logpose-ark`), `--admin-password` (required, prompted hidden if missing; falls back to `secrets.token_urlsafe(16)` only with explicit `--generate-password` flag; printed once), `--password` (optional ark_ServerPassword), `--beta` (default `preaquatica`; set to empty string for stable branch), `--enable-autostart` (optional; enables arkserver.service at boot), `--start`
- [ ] **ARK-06**: Map enum validation at CLI boundary — rejects invalid maps with list of valid options (TheIsland, TheCenter, ScorchedEarth_P, Aberration_P, Extinction, Ragnarok, Valguero_P, CrystalIsles, LostIsland, Fjordur, Genesis, Genesis2) — matches arkmanager's supported set
- [ ] **ARK-07**: Port collision probe via `ss -tuln` before install; fail early with specific port number if conflict detected
- [ ] **ARK-08**: Settings parser/saver targets `/etc/arkmanager/instances/main.cfg` (bash-style `key="value"` format), NOT `GameUserSettings.ini`. Implementation reads line-by-line, preserves comments/whitespace, mutates the `ark_*` lines in place. Not a `RawConfigParser` — main.cfg is sourced shell syntax, so a regex-based line editor is the correct tool.
- [ ] **ARK-09**: Editor writes main.cfg back with original line order and unrelated keys untouched (in-place edit, not full rewrite)
- [ ] **ARK-10**: Install-time seed of `/etc/arkmanager/instances/main.cfg` with all install-flag values (`arkserverroot`, `serverMap`, `ark_SessionName`, `ark_Port`, `ark_QueryPort`, `ark_RCONEnabled`, `ark_RCONPort`, `ark_ServerPassword`, `ark_ServerAdminPassword`, `ark_MaxPlayers`). GameUserSettings.ini is NOT touched by logpose — arkmanager owns it.
- [ ] **ARK-11**: ARK apt deps (minimum set verified on Debian 13 per install record): `steamcmd`, `libc6-i386`, `lib32gcc-s1`, `lib32stdc++6`, `curl`, `bzip2`, `tar`, `rsync`, `sed`, `perl-modules`, `lsof`. (Previous Debian 12 extras like `libncurses5`, `libncursesw5`, `libsdl2-2.0-0` dropped — not required by arkmanager v1.6.68.) On Debian: enable `contrib non-free` in `/etc/apt/sources.list` + add `i386` foreign arch. On Ubuntu: enable `multiverse`.
- [ ] **ARK-12**: `_fix_steam_sdk` applies to Palworld only. ARK's steamcmd SDK setup is handled entirely by arkmanager + the apt `steamcmd` package. `GAMES["ark"].post_install_hooks` omits `_fix_steam_sdk`.
- [ ] **ARK-13**: RCON triad alignment — install writes `ark_RCONEnabled="True"`, `ark_RCONPort="<rcon_port>"`, `ark_ServerAdminPassword="<admin_password>"` to main.cfg. arkmanager appends `?RCONEnabled=True?RCONPort=<port>` to launch args automatically.
- [ ] **ARK-14** *(new)*: `logpose ark install` installs arkmanager via the upstream netinstall.sh (`curl -sL https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/netinstall.sh | bash -s steam`) when not already present. Idempotent — skips netinstall if `/usr/local/bin/arkmanager` exists.
- [ ] **ARK-15** *(new)*: `logpose ark install` pre-accepts the Steam EULA non-interactively via `debconf-set-selections` for `steam/question` and `steamcmd/question` ("I AGREE") before `apt-get install steamcmd`.
- [ ] **ARK-16** *(new)*: `logpose ark install` creates the `steam` service user (`useradd -m -s /bin/bash steam`) if absent; no password set (access is only via `sudo -u steam`).
- [ ] **ARK-17** *(new)*: `logpose ark install` runs `sudo -u steam arkmanager install --beta=<branch> --validate` TWICE to work around steamcmd's known first-run self-update quirk (the first invocation exits 0 with no payload after self-updating). Second invocation downloads the actual server files.
- [ ] **ARK-18** *(new)*: `logpose ark install` drops a sudoers fragment at `/etc/sudoers.d/logpose-ark` granting passwordless access: `<invoking-user> ALL=(steam) NOPASSWD: /usr/local/bin/arkmanager *`. Removed cleanly on `logpose ark uninstall`.
- [ ] **ARK-19** *(new)*: `logpose ark <start|stop|restart|status|saveworld|backup|update|rconcmd>` delegate to `sudo -u steam arkmanager <verb>`, surfacing return code + tail of stderr to the user. `update` runs twice (same self-update quirk as install).

### Settings Editor

- [ ] **SET-01**: `logpose palworld edit-settings` works identically to v0.1.19 (uses `_palworld_parse`/`_palworld_save` behind `SettingsAdapter`)
- [ ] **SET-02**: `logpose ark edit-settings` works out-of-the-box using ARK's `_ark_parse`/`_ark_save` adapter
- [ ] **SET-03**: Interactive editor (Rich table + prompt-by-name loop) refactored to take a `GameSpec` and dispatch to `spec.settings_adapter` — same UX for both games
- [ ] **SET-04**: `_create_settings_from_default` for Palworld preserved; ARK uses install-time seed (ARK-10) instead of a default template

### Polkit & systemd

- [ ] **POL-01**: Single merged polkit rule file `40-logpose.rules` replaces `40-palserver.rules`; regenerated on every install with unit list from `GAMES.values()`
- [ ] **POL-02**: `40-logpose.rules.template` uses JS `var units = [{units}]; indexOf(...)` pattern; every `{`/`}` outside placeholders doubled as `{{`/`}}`
- [ ] **POL-03**: `_setup_polkit()` no longer takes game-specific args; reads from `GAMES` globally so installing any game authorizes all known game service units
- [ ] **POL-04**: Old v0.1.19 `40-palserver.rules` is left on disk if present (additive with new merged rule — Polkit merges across files). README documents manual cleanup
- [ ] **POL-05**: `pkcheck --action-id=org.freedesktop.systemd1.manage-units --process $$ --detail unit <service>.service` verification in exit criteria for both `palserver.service` and `arkserver.service`

### Verification & E2E

- [ ] **E2E-01**: Byte-diff regression test — rendered Palworld service file matches v0.1.19 output for fixed fixture
- [ ] **E2E-02**: CLI smoke-test matrix — `logpose --help`, `logpose palworld --help`, `logpose ark --help`, `logpose palworld install --help`, `logpose ark install --help` all exit 0 and show expected trees
- [ ] **E2E-03**: On fresh Debian 12 VM: `logpose palworld install --port 8211 --players 16 --start` → server advertises → `systemctl stop palserver` → saves intact → no sudo prompts
- [ ] **E2E-04**: On fresh Debian 12 VM: `logpose ark install --map TheIsland --admin-password XXX --start` → server advertises → RCON reachable on port 27020 → `systemctl stop arkserver` → saves intact → no sudo prompts
- [ ] **E2E-05**: Wheel metadata verification — `python -m build` then `unzip -p dist/*.whl *.dist-info/METADATA | head` shows `Name: logpose-launcher` and `Version: 0.2.0`
- [ ] **E2E-06**: TestPyPI dry-run publish + throwaway-venv install — `pip install -i https://test.pypi.org/simple/ logpose-launcher` succeeds; `logpose --help` works post-install

## v2 Requirements (deferred to v0.3+ or later milestones)

### Additional Games
- **NEXT-01**: Valheim dedicated server support
- **NEXT-02**: CS2 dedicated server support
- **NEXT-03**: Satisfactory dedicated server support
- **NEXT-04**: ARK: Survival Ascended (ASA) support (requires Proton/Wine wrapper)

### Enhanced Features
- **ENH-01**: `logpose list-games` discovery command (deferred until game count ≥ 4 — Typer `--help` is sufficient for 2)
- **ENH-02**: `logpose ark edit-settings` category-grouped editor (vs flat prompt-by-name)
- **ENH-03**: `logpose ark edit-settings` with filter/search by key name
- **ENH-04**: ARK `Game.ini` editing (engrams, spawn rates) — v0.2 ships only `GameUserSettings.ini`
- **ENH-05**: Mod management subcommand (`logpose ark mods add/list/remove`)
- **ENH-06**: Backup/restore commands per game
- **ENH-07**: ARK cluster management (cluster-id flag)
- **ENH-08**: RCON client (`logpose ark rcon <cmd>`)
- **ENH-09**: `logpose migrate-from-palworld-server-launcher` command (auto-rename systemd/polkit from old install)

### Distribution & Platform
- **PLT-01**: Arch Linux support (pacman, different systemd paths)
- **PLT-02**: RHEL/Fedora support (dnf, SELinux considerations)
- **PLT-03**: macOS support (no Steam dedicated servers typically, but steamcmd works)
- **PLT-04**: Trusted Publishing via GitHub Actions (OIDC) for PyPI releases

### Testing
- **TEST-01**: pytest harness under `tests/` with mocked `_run_command` and `subprocess`
- **TEST-02**: CI pipeline (GitHub Actions) running tests on push
- **TEST-03**: Settings parser fixture-based tests (Palworld regex + ARK configparser)

## Out of Scope

| Feature | Reason |
|---------|--------|
| `BaseGame` class hierarchy | User explicitly rejected — minimum-diff principle, 2 games don't justify abstraction |
| `core/` module split | Same reason — keep everything in `logpose/main.py` |
| CLI renamed to `gsl` | User chose `logpose` (One Piece theme) instead |
| ARK: Survival Ascended (ASA) | ASA has no native Linux server; requires Proton/Wine (deferred to v2) |
| Arch Linux / pacman | Debian/Ubuntu only; `_repair_package_manager()` is apt/dpkg-specific |
| Migration command for old palworld-server-launcher installs | Existing v0.1.19 users keep working; `logpose-launcher` is a clean install, documented in README |
| Web dashboard / GUI | Out of scope — CLI-only tool |
| Real-time log tailing (`logpose ark logs --follow`) | Use `journalctl -fu arkserver.service` directly |
| Windows support | Steam dedicated server Linux binaries; Windows is a different installation model |
| pytest framework in v0.2.0 | Deferred to later milestone per PROJECT.md; manual E2E verification only |
| ARK `Game.ini` editing | Only `GameUserSettings.ini` in v0.2.0 |
| Removal of `_repair_package_manager()` | Load-bearing per CLAUDE.md — GCP VMs and fresh Debian have broken dpkg state |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | Phase 1 | Pending |
| PKG-02 | Phase 1 | Pending |
| PKG-03 | Phase 1 | Pending |
| PKG-04 | Phase 1 | Pending |
| PKG-05 | Phase 1 | Pending |
| PKG-06 | Phase 1 | Pending |
| PKG-07 | Phase 6 | Pending |
| PKG-08 | Phase 4, 6 | Pending |
| ARCH-01 | Phase 3 | Pending |
| ARCH-02 | Phase 3 | Pending |
| ARCH-03 | Phase 3 | Pending |
| ARCH-04 | Phase 2, 3 | Pending |
| ARCH-05 | Phase 1–5 | Pending |
| ARCH-06 | Phase 1–3 | Pending |
| CLI-01 | Phase 4 | Pending |
| CLI-02 | Phase 4 | Pending |
| CLI-03 | Phase 4 | Pending |
| CLI-04 | Phase 4 | Pending |
| CLI-05 | Phase 4 | Pending |
| CLI-06 | Phase 4 | Pending |
| CLI-07 | Phase 4 | Pending |
| PAL-01 | Phase 1–5 | Pending |
| PAL-02 | Phase 1–5 | Pending |
| PAL-03 | Phase 2 | Pending |
| PAL-04 | Phase 2 | Pending |
| PAL-05 | Phase 3 | Pending |
| PAL-06 | Phase 1–5 | Pending |
| PAL-07 | Phase 4 | Pending |
| PAL-08 | Phase 3 | Pending |
| PAL-09 | Phase 2, 5 | Pending |
| ARK-01 | Phase 5 | Pending |
| ARK-02 | Phase 5 | Pending |
| ARK-03 | Phase 5 | Pending |
| ARK-04 | Phase 5 | Pending |
| ARK-05 | Phase 5 | Pending |
| ARK-06 | Phase 5 | Pending |
| ARK-07 | Phase 5 | Pending |
| ARK-08 | Phase 5 | Pending |
| ARK-09 | Phase 5 | Pending |
| ARK-10 | Phase 5 | Pending |
| ARK-11 | Phase 5 | Pending |
| ARK-12 | Phase 5 | Pending |
| ARK-13 | Phase 5 | Pending |
| ARK-14 | Phase 5 | Pending |
| ARK-15 | Phase 5 | Pending |
| ARK-16 | Phase 5 | Pending |
| ARK-17 | Phase 5 | Pending |
| ARK-18 | Phase 5 | Pending |
| ARK-19 | Phase 5 | Pending |
| SET-01 | Phase 2 | Pending |
| SET-02 | Phase 5 | Pending |
| SET-03 | Phase 4 | Pending |
| SET-04 | Phase 5 | Pending |
| POL-01 | Phase 4 | Pending |
| POL-02 | Phase 4 | Pending |
| POL-03 | Phase 4 | Pending |
| POL-04 | Phase 4, 6 | Pending |
| POL-05 | Phase 4, 5 | Pending |
| E2E-01 | Phase 2 | Pending |
| E2E-02 | Phase 4 | Pending |
| E2E-03 | Phase 5 | Pending |
| E2E-04 | Phase 5 | Pending |
| E2E-05 | Phase 6 | Pending |
| E2E-06 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 62 total (56 original + 6 added 2026-04-12 by the Phase 5 arkmanager pivot: ARK-14..ARK-19)
- Mapped to phases: 62
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 after initial definition*
