# logpose

## What This Is

`logpose` is a multi-game dedicated server launcher for Debian/Ubuntu — a single CLI that installs, configures, and manages game servers (Palworld, ARK: Survival Evolved) via SteamCMD + systemd + Polkit. It evolves in place from the existing `palworld-server-launcher` codebase, generalizing the Palworld-specific tool into a game-dispatched launcher without a full architectural rewrite.

## Core Value

**One CLI, many games, zero sudo prompts** — operators type `logpose <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box. Adding a new game is a config entry, not a new tool.

## Requirements

### Validated

<!-- Shipped and confirmed valuable in palworld-server-launcher v0.1.19 -->

- ✓ SteamCMD install automation on Debian/Ubuntu — existing (v0.1.19)
- ✓ Aggressive apt/dpkg repair before install (`_repair_package_manager`) — existing (v0.1.19)
- ✓ systemd service creation with user-scoped execution — existing (v0.1.19)
- ✓ Polkit rule for sudo-less `systemctl start|stop|restart` — existing (v0.1.19)
- ✓ SteamCMD license pre-acceptance via debconf-set-selections — existing (v0.1.19)
- ✓ Palworld install, start, stop, restart, status, enable, disable, update — existing (v0.1.19)
- ✓ Palworld `edit-settings` — custom `OptionSettings=(...)` regex parser + interactive editor — existing (v0.1.19)
- ✓ Steam SDK fix (`steamclient.so` → `~/.steam/sdk64/`) — existing (v0.1.19)
- ✓ Templates via `str.format()` with escaped JS braces in polkit rules — existing (v0.1.19)

### Active

<!-- Milestone v0.2.0 scope: rename + generalize + add ARK -->

- [ ] Rename package `palworld_server_launcher/` → `logpose/`; update `pyproject.toml` (`name = "logpose"`, entry point `logpose = "logpose.main:app"`)
- [ ] Parameterize `main.py` via a `GAMES` dict keyed by game name — fields: `app_id`, `server_dir`, `settings_path`, `default_settings_path`, `service_name`, `service_template`, `launch_args_template`, `settings_adapter` (callable pair for parse/save)
- [ ] Refactor existing helpers (`_run_command`, `_install_steamcmd`, `_repair_package_manager`, `_fix_steam_sdk`, `_create_service_file`, `_setup_polkit`) to accept a game key or read game-specific values from the `GAMES` dict — no `BaseGame` class, no `core/` module split
- [ ] Convert Typer CLI to game-first nested subcommands: `logpose palworld install`, `logpose palworld start`, `logpose ark install`, `logpose ark start`, etc. Every existing command re-exposed per game.
- [ ] Add ARK: Survival Evolved game entry — SteamCMD app id `376030`, binary `ShooterGame/Binaries/Linux/ShooterGameServer`, multi-port launch args (GamePort 7777 / QueryPort 27015 / RCON 32330 optional), map selection (TheIsland default; Ragnarok, TheCenter, ScorchedEarth, Aberration, Extinction, Valguero, CrystalIsles, Fjordur, LostIsland, Genesis, Genesis2 supported), session name + admin password on install
- [ ] Add ARK settings adapter — standard-INI parser for `ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini` (configparser-based; preserves sections, comments where feasible) — works out-of-the-box with `logpose ark edit-settings`
- [ ] Create `arkserver.service` systemd template with ARK launch command
- [ ] Create per-game polkit rule covering both `palserver.service` and `arkserver.service` for the installing user
- [ ] Preserve Palworld behavior identically — same service name `palserver.service`, same polkit rule filename (or merged file covering both games), same `OptionSettings` regex parser, same launch args, same settings format
- [ ] Update `README.md` with new CLI examples for both games + migration note ("this is a new package; `palworld-server-launcher` v0.1.19 stays as-is on PyPI")
- [ ] Publish `logpose` as a new PyPI package (not renamed) — old `palworld-server-launcher` stays frozen at v0.1.19

### Out of Scope

- **Arch Linux / pacman support** — Debian/Ubuntu only for this milestone; generalization to other distros deferred.
- **ARK: Survival Ascended (ASA)** — ASA has no native Linux server (requires Proton/Wine); only ASE (app id 376030) is in scope.
- **`BaseGame` abstract class and `core/` module split** — explicitly rejected for minimum-diff approach; deferred until 3+ games justify the abstraction.
- **Migration command for existing `palworld-server-launcher` users** — existing users keep running v0.1.19; `logpose` is a new install, not an upgrade path. Documented in README, not automated.
- **CLI renamed to `gsl` per original future-direction note** — name is `logpose` (One Piece-inspired) instead.
- **Additional games (Valheim, CS2, Satisfactory, etc.)** — only Palworld + ARK in v0.2.0; further games are future milestones.
- **Test framework** — no pytest harness in v0.2.0; deferred to a later milestone.
- **`Game.ini` editing for ARK** — only `GameUserSettings.ini` is editable via `edit-settings` in v0.2.0. `Game.ini` tuning (engrams, spawn rates) is manual.
- **Migration of existing `palserver.service` installs** — installs from `palworld-server-launcher` v0.1.19 keep running; `logpose` creates its own service file with the same name but operators should re-run `logpose palworld install` to regenerate.

## Context

- Existing codebase is a single-file Python package (`palworld_server_launcher/main.py`, ~400 lines) + two templates (`palserver.service.template`, `palserver.rules.template`).
- Heavy reliance on `subprocess.Popen` via a single `_run_command()` helper — never raw subprocess outside it.
- Rich + Typer stack; Python 3.8+ per `requires-python`.
- Template placeholders use Python `str.format()` — literal braces in polkit JS must be escaped as `{{ }}`.
- Palworld settings file is **not** standard INI: values live inside `OptionSettings=(Key=Value,Key=Value,...)`, parsed via `re.findall(r'(\w+)=(".*?"|[^,]+)', ...)`.
- ARK settings are standard INI split across `GameUserSettings.ini` and `Game.ini` — the two games need different settings adapters.
- ARK needs more install-time parameters than Palworld (map, query port, RCON port, session name, admin password).
- GCP VMs and fresh Debian installs frequently have broken dpkg state — `_repair_package_manager()` is load-bearing and must not be removed.
- Service management via systemd; passwordless `systemctl start|stop|restart` via Polkit rule per installing user.
- Current release: `palworld-server-launcher` v0.1.19 on PyPI (frozen); `logpose` will be a new package.

## Constraints

- **Tech stack**: Python 3.8+, Typer, Rich — no new runtime dependencies unless strongly justified. Python's stdlib `configparser` is sufficient for ARK's standard INI.
- **OS**: Debian/Ubuntu only (`apt` + `dpkg`). No Arch/pacman, no RPM, no macOS, no Windows.
- **Minimum diff**: No `BaseGame` class, no `core/` module split. A `GAMES` dict and per-game helper functions are the expected shape. Three similar lines > premature abstraction.
- **Behavioral compatibility**: Palworld must behave identically to v0.1.19 — same service name, same polkit rule semantics, same launch args, same INI parsing. Anyone re-running `logpose palworld install` on an existing box should see no surprises.
- **Template placeholder escaping**: `{user}`, `{port}`, `{players}`, `{exec_start_path}`, `{working_directory}` for Palworld; ARK needs extras like `{query_port}`, `{rcon_port}`, `{map}`, `{session_name}`, `{admin_password}`. Literal braces in JS (polkit) stay as `{{ }}`.
- **SteamCMD app ids**: Palworld `2394010`, ARK: Survival Evolved `376030`.
- **Keep `_repair_package_manager()` intact** — documented as load-bearing in CLAUDE.md.
- **New PyPI package**: distribution name `logpose` (if available) — verify on PyPI before first publish. Fallback: `logpose-launcher` or `logpose-server-launcher`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| In-place rename (not new repo) | User explicitly wants "use this project, don't modify too much" — minimum diff, one repo, git-rename preserves history. | — Pending |
| `GAMES` dict over `BaseGame` class | Only 2 games — abstraction cost exceeds benefit. Three similar lines > premature abstraction (per user CLAUDE.md). | — Pending |
| Game-first nested subcommands (`logpose <game> <command>`) | Matches future `gsl`-style vision (One Piece metaphor aside) and scales cleanly when a 3rd game is added. Closer to `kubectl <resource> <verb>` ergonomics than a `--game` flag. | — Pending |
| Publish new PyPI package (leave old frozen) | PyPI doesn't support package renames; cleanest is new name + deprecation note on old. No back-compat shims. User accepted explicitly. | — Pending |
| Name = `logpose` (One Piece) | Short (7 chars), typeable, metaphorically clean (navigational pointer to target), user-chosen. | ✓ Good |
| Debian/Ubuntu only | Existing `_repair_package_manager()` is apt/dpkg-specific; Arch/pacman deferred. User explicitly scoped out. | — Pending |
| ARK-ASE only (not ASA) | ASA has no native Linux server (Proton/Wine required). ASE has native Linux binary via app id 376030. | — Pending |
| ARK INI adapter via stdlib `configparser` | Standard INI — no new dependency needed. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after initialization*
