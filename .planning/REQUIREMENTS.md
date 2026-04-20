# Requirements: road-poneglyph v0.3.0

**Defined:** 2026-04-21
**Core Value:** One CLI, many games, zero sudo prompts — operators type `road-poneglyph <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box.

## v0.3.0 Requirements (Satisfactory milestone)

Requirements for adding Satisfactory dedicated server support to road-poneglyph.

### Satisfactory Game Entry (SAT)

- [ ] **SAT-01**: `GAMES["satisfactory"]` entry with app_id=1690800, service_name="satisfactory", binary=FactoryServer.sh, install via SteamCMD anonymous
- [ ] **SAT-02**: `satisfactory.service.template` with Type=simple, KillSignal=SIGINT, TimeoutStopSec=120, User={user}, WorkingDirectory={server_dir}
- [ ] **SAT-03**: Install helper wrapping SteamCMD install (anonymous login, app_update 1690800 validate) — same pattern as Palworld
- [ ] **SAT-04**: Install uses invoking user's home (like Palworld) — server files at `~/SatisfactoryDedicatedServer/`
- [ ] **SAT-05**: `road-poneglyph satisfactory install --port 7777 --reliable-port 8888 --players 4 --start` install command
- [ ] **SAT-06**: Standard verbs: start, stop, restart, status, enable, disable, update — all dispatched through factory
- [ ] **SAT-07**: `vm.max_map_count=262144` sysctl tuning via post_install_hook (prevents crash on large maps)
- [ ] **SAT-08**: Optional `--auto-update` flag writes ExecStartPre steamcmd update in service template

### Settings Adapter (SET)

- [ ] **SET-05**: INI-based SettingsAdapter parsing Engine.ini, Game.ini, GameUserSettings.ini (Unreal Engine INI via configparser)
- [ ] **SET-06**: `road-poneglyph satisfactory edit-settings` interactive editor (Rich-table UI, same UX as Palworld/ARK)
- [ ] **SET-07**: Graceful handling of missing config files (first-run: configs only generated after first graceful stop)

### HTTPS API Integration (API)

- [ ] **API-01**: Pre-shutdown save: ExecStop calls `SaveGame` via HTTPS API before sending SIGINT
- [ ] **API-02**: `road-poneglyph satisfactory save [name]` verb wrapping the SaveGame API endpoint
- [ ] **API-03**: Health check integration (`HealthCheck` endpoint — no auth required) for enhanced status output
- [ ] **API-04**: Bearer token auth flow: PasswordLogin → token; token cached at `~/.config/road-poneglyph/satisfactory-api-token`
- [ ] **API-05**: Token file stored with mode 0600, not committed to git, documented in README

### Polkit & Permissions (POL)

- [ ] **POL-06**: Merged polkit rule (40-road-poneglyph.rules) includes `satisfactory.service` in units array
- [ ] **POL-07**: Byte-diff golden recaptured atomically with GAMES["satisfactory"] insertion (same commit)

### Testing (TST)

- [ ] **TST-01**: Byte-diff golden test for satisfactory.service.template
- [ ] **TST-02**: Palworld + ARK goldens remain green after Satisfactory addition (regression invariant)
- [ ] **TST-03**: All tests pass in CI (GitHub Actions workflow, tag-triggered)

### Packaging & Release (PKG)

- [ ] **PKG-09**: README updated with Satisfactory section — all verbs, port reference (7777 UDP+TCP, 8888 TCP), first-run instructions
- [ ] **PKG-10**: Firewall port documentation in README (7777 UDP game, 7777 TCP API, 8888 TCP reliable messaging)
- [ ] **PKG-11**: pyproject.toml version bumped to 0.3.0
- [ ] **PKG-12**: Tag v0.3.0 triggers PyPI publish via existing trusted publisher workflow
- [ ] **PKG-13**: First-run instructions in README (claim step, config generation quirk, RAM requirements)

### End-to-End (E2E)

- [ ] **E2E-07**: `road-poneglyph satisfactory install --start` on Debian 13 (VM-gated)
- [ ] **E2E-08**: `road-poneglyph satisfactory stop` triggers API save + SIGINT graceful shutdown

## Traceability

| Phase | Requirements |
|-------|-------------|
| 7 — Satisfactory GameSpec + Service | SAT-01, SAT-02, SAT-03, SAT-04, SAT-05, SAT-06, SAT-07, SAT-08, POL-06, POL-07, TST-01, TST-02 |
| 8 — Settings Adapter + API Client | SET-05, SET-06, SET-07, API-01, API-02, API-03, API-04, API-05, E2E-08 |
| 9 — Release Polish + Publish | PKG-09, PKG-10, PKG-11, PKG-12, PKG-13, E2E-07, TST-03 |

---
*Created: 2026-04-21 for milestone v0.3.0*
