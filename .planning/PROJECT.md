# road-poneglyph

## What This Is

`road-poneglyph` is a multi-game dedicated server launcher for Debian/Ubuntu — a single CLI that installs, configures, and manages game servers (Palworld, ARK: Survival Evolved, Satisfactory) via SteamCMD + systemd + Polkit. It evolved from the `palworld-server-launcher` codebase, generalizing into a game-dispatched launcher.

## Core Value

**One CLI, many games, zero sudo prompts** — operators type `road-poneglyph <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box. Adding a new game is a config entry, not a new tool.

## Requirements

### Validated

<!-- Shipped in road-poneglyph v0.2.0 -->

- ✓ SteamCMD install automation on Debian/Ubuntu — existing (v0.1.19)
- ✓ Aggressive apt/dpkg repair before install (`_repair_package_manager`) — existing (v0.1.19)
- ✓ systemd service creation with user-scoped execution — existing (v0.1.19)
- ✓ Polkit rule for sudo-less `systemctl start|stop|restart` — existing (v0.1.19)
- ✓ Palworld install, start, stop, restart, status, enable, disable, update, edit-settings — v0.2.0
- ✓ GameSpec frozen dataclass + GAMES registry — v0.2.0
- ✓ Typer factory with game-first subcommands (`road-poneglyph <game> <verb>`) — v0.2.0
- ✓ Merged polkit rule covering all registered games — v0.2.0
- ✓ ARK via arkmanager wrapper (`road-poneglyph ark <verb>`) — v0.2.0
- ✓ PyPI publish via GitHub Actions OIDC trusted publisher — v0.2.0
- ✓ Byte-diff golden regression harness (6 tests) — v0.2.0

### Active

<!-- Milestone v0.3.0 scope: add Satisfactory -->

- [ ] Add Satisfactory dedicated server entry — SteamCMD app id 1690800, native binary FactoryServer.sh, Type=simple, KillSignal=SIGINT
- [ ] Satisfactory systemd service template with SIGINT shutdown + TimeoutStopSec=120
- [ ] INI-based SettingsAdapter for Unreal Engine INI (Engine.ini, Game.ini, GameUserSettings.ini)
- [ ] Pre-shutdown save via HTTPS API (SaveGame call before SIGINT)
- [ ] HTTPS API client for server management (health check, save, shutdown)
- [ ] Merged polkit rule updated to cover satisfactory.service
- [ ] Byte-diff golden tests for satisfactory.service.template
- [ ] README updated with Satisfactory CLI examples + port reference (7777 UDP+TCP, 8888 TCP)
- [ ] Publish road-poneglyph v0.3.0 to PyPI (tag-triggered)

### Out of Scope

- **Arch Linux / pacman support** — Debian/Ubuntu only.
- **ARK: Survival Ascended (ASA)** — no native Linux server.
- **Satisfactory mods management** — too complex for v0.3.0; manual via ficsit-cli.
- **Satisfactory auto-claim** — server must be claimed in-game by first player (human step, cannot be automated).
- **Custom HTTPS certificates for Satisfactory API** — self-signed works; custom certs deferred.
- **Multi-instance Satisfactory** — single instance per box for v0.3.0.

## Context

- Single-file Python package (`road_poneglyph/main.py`, ~1100 lines) + templates.
- Satisfactory uses same SteamCMD + systemd pattern as Palworld (native path, no wrapper).
- Key difference: SIGINT shutdown (SIGTERM kills immediately), no auto-save on stop, HTTPS REST API instead of RCON.
- Config files only generated after first graceful shutdown (first-run quirk).
- GameSpec schema already supports this pattern — `post_install_hooks` can handle sysctl tuning.

## Constraints

- **Tech stack**: Python 3.8+, Typer, Rich — no new runtime dependencies. stdlib `configparser` for Unreal INI.
- **OS**: Debian/Ubuntu only.
- **Behavioral compatibility**: Palworld + ARK must remain byte-identical after Satisfactory is added.
- **SIGINT shutdown**: Satisfactory service MUST use `KillSignal=SIGINT` (SIGTERM kills without cleanup).
- **Pre-shutdown save**: ExecStop or pre-stop hook must call API `SaveGame` before stop signal.
- **Minimum RAM**: Document 12-16 GB requirement in README for Satisfactory.
- **Port simplicity**: Only 7777 (UDP game + TCP API) and 8888 (TCP reliable messaging).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Renamed to road-poneglyph (One Piece) | `logpose` taken on PyPI; road-poneglyph (ancient stones pointing to treasure) reflects multi-game navigation | ✓ Done (v0.2.0) |
| Native SteamCMD path for Satisfactory | Same pattern as Palworld — simpler, no wrapper tool needed. LinuxGSM exists but wrapping is unnecessary complexity. | — Pending |
| HTTPS API for save management | Satisfactory has no RCON; HTTPS API on port 7777 is the only management interface. Minimal client needed. | — Pending |
| Pre-stop save via ExecStop or hook | Server doesn't auto-save on any signal. Must explicitly save before SIGINT. | — Pending |
| stdlib configparser for INI | Unreal Engine INI is standard enough for configparser; same conclusion as research for settings editing. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-04-21 — new milestone v0.3.0 (Satisfactory)*
