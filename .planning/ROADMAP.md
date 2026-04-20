# Roadmap: road-poneglyph v0.3.0

**Milestone:** v0.3.0 — Add Satisfactory dedicated server support
**Granularity:** coarse
**Created:** 2026-04-21
**Core Value:** One CLI, many games, zero sudo prompts — `road-poneglyph <game> <command>` handles Palworld, ARK, and now Satisfactory.

## Phases

- [x] **Phase 7: Satisfactory GameSpec + Service Template** — Add `GAMES["satisfactory"]` entry, `satisfactory.service.template` (Type=simple, KillSignal=SIGINT), install helper (SteamCMD anonymous, app 1690800), sysctl tuning, polkit + golden recapture
- [ ] **Phase 8: Settings Adapter + HTTPS API Client** — INI-based SettingsAdapter for Unreal Engine config files, pre-shutdown save via HTTPS API, Bearer token auth, `save` verb, health check integration
- [ ] **Phase 9: Release Polish + v0.3.0 Publish** — README Satisfactory section, firewall ports, first-run instructions, version bump, tag v0.3.0 → PyPI

## Phase Details

### Phase 7: Satisfactory GameSpec + Service Template
**Goal**: `GAMES["satisfactory"]` exists with the correct GameSpec, `satisfactory.service.template` uses SIGINT shutdown, install helper wraps SteamCMD (app 1690800), merged polkit covers all 3 games, and byte-diff harness proves no regression.
**Depends on**: v0.2.0 complete (Phase 6)
**Requirements**: SAT-01, SAT-02, SAT-03, SAT-04, SAT-05, SAT-06, SAT-07, SAT-08, POL-06, POL-07, TST-01, TST-02
**Success Criteria** (what must be TRUE):
  1. `GAMES["satisfactory"]` defined at module scope with app_id=1690800, service_name="satisfactory", settings_adapter using INI parse/save, post_install_hooks containing sysctl tuner.
  2. `satisfactory.service.template` renders with `Type=simple`, `KillSignal=SIGINT`, `TimeoutStopSec=120`, `User={user}`, `ExecStart=...FactoryServer.sh -Port={port} -ReliablePort={reliable_port} -multihome=0.0.0.0 -log -unattended`.
  3. `road-poneglyph satisfactory install --port 7777 --reliable-port 8888 --players 4 --start` completes without errors (factory dispatches all standard verbs).
  4. Merged polkit rule (`40-road-poneglyph.rules`) contains `satisfactory.service` in units list; golden recaptured atomically.
  5. `pytest tests/ -x` passes with 8+ tests (6 existing + 2 new Satisfactory goldens); Palworld + ARK goldens byte-identical.
**Plans:** 3 plans
Plans:
- [x] 07-01-PLAN.md — Service template + install helpers (SteamCMD wrapper, sysctl hook, custom renderer)
- [x] 07-02-PLAN.md — GAMES["satisfactory"] entry + factory verb routing + atomic polkit golden recapture
- [x] 07-03-PLAN.md — Byte-diff golden tests for Satisfactory + full harness green assertion

### Phase 8: Settings Adapter + HTTPS API Client
**Goal**: `road-poneglyph satisfactory edit-settings` works via INI-based adapter for Engine.ini/Game.ini/GameUserSettings.ini; pre-shutdown save calls HTTPS API `SaveGame` before SIGINT; `road-poneglyph satisfactory save` verb available.
**Depends on**: Phase 7
**Requirements**: SET-05, SET-06, SET-07, API-01, API-02, API-03, API-04, API-05, E2E-08
**Success Criteria** (what must be TRUE):
  1. `road-poneglyph satisfactory edit-settings` parses GameUserSettings.ini → Rich table → mutate → save; preserves sections and comments.
  2. Graceful handling of missing config files (first run: prints message, instructs user to start→stop→edit).
  3. ExecStop in satisfactory.service calls a save script/command that hits HTTPS API `SaveGame` before the main process receives SIGINT.
  4. `road-poneglyph satisfactory save [name]` calls the HTTPS API and reports success/failure.
  5. Bearer token cached at `~/.config/road-poneglyph/satisfactory-api-token` with mode 0600; `PasswordLogin` flow on first use.
  6. `road-poneglyph satisfactory status` includes API health check info when server is running and claimed.
**Plans:** 3 plans
Plans:
- [ ] 08-01-PLAN.md — INI-based SettingsAdapter + edit-settings graceful missing-file handling
- [ ] 08-02-PLAN.md — HTTPS API client + token caching + save verb + enhanced status
- [ ] 08-03-PLAN.md — ExecStop pre-shutdown save wiring + golden recapture

### Phase 9: Release Polish + v0.3.0 Publish
**Goal**: `road-poneglyph` v0.3.0 ships to PyPI with Satisfactory support, README covers all 3 games with examples, ports, and first-run guide.
**Depends on**: Phase 8
**Requirements**: PKG-09, PKG-10, PKG-11, PKG-12, PKG-13, E2E-07, TST-03
**Success Criteria** (what must be TRUE):
  1. README includes Satisfactory section with per-verb examples, port table (7777 UDP+TCP, 8888 TCP), first-run claim instructions, RAM guidance (12-16 GB).
  2. pyproject.toml version = "0.3.0"; clean `python -m build` produces wheel with `Name: road-poneglyph`, `Version: 0.3.0`.
  3. Tag v0.3.0 pushed → GitHub Actions workflow builds + publishes to PyPI successfully.
  4. `pip install road-poneglyph` in a fresh venv shows `satisfactory` in `road-poneglyph --help`.
  5. `road-poneglyph satisfactory install --start` on Debian 13 completes E2E (VM-gated; may defer like Phase 5).
**Plans:** 3 plans
Plans:
- [ ] 08-01-PLAN.md — INI-based SettingsAdapter + edit-settings graceful missing-file handling
- [ ] 08-02-PLAN.md — HTTPS API client + token caching + save verb + enhanced status
- [ ] 08-03-PLAN.md — ExecStop pre-shutdown save wiring + golden recapture

## Dependencies

| Phase | Depends On | Why |
|-------|------------|-----|
| 7 — GameSpec + Service | v0.2.0 (Phase 6) | Factory + registry must exist |
| 8 — Settings + API | Phase 7 | GameSpec must be registered; service template must exist for ExecStop wiring |
| 9 — Release | Phase 8 | All features complete before publish |

## Research Hooks

| Phase | Research Needed? | Priority | Notes |
|-------|------------------|----------|-------|
| 7 | No | — | SteamCMD pattern well-understood; service template is mechanical. Research already complete in `.planning/research/satisfactory-hosting.md`. |
| 8 | Low | Low | Brief validation of HTTPS API Bearer token flow against live server. Endpoint schema documented in research. |
| 9 | No | — | Standard PyPI flow; workflow already exists. |

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 7. Satisfactory GameSpec + Service | 3/3 | Complete | 2026-04-20 |
| 8. Settings Adapter + API Client | 0/3 | In progress | — |
| 9. Release Polish + v0.3.0 Publish | 0/0 | Not started | — |

## Coverage

- v0.3.0 requirements: **24 / 24 mapped** ✓
- Orphaned requirements: **0** ✓
- Phases without requirements: **0** ✓
- Source of truth: `.planning/REQUIREMENTS.md` Traceability table

---
*Roadmap created: 2026-04-21*
