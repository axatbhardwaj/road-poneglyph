---
phase: 05-add-ark-entry-e2e-arkmanager-wrapper
plan: 02
subsystem: games-registry-and-factory
tags: [ark, games, typer-factory, polkit-golden, atomic-commit]
requires: [05-01]
provides: [GAMES-ark, ark-cli-verbs, polkit-golden-v0.2.0-ark]
affects: [logpose/main.py, tests/golden/40-logpose.rules.v0_2_0]
tech-stack:
  added: []
  patterns: [factory-with-key-branch, atomic-golden-recapture, typer-callbacks]
key-files:
  modified:
    - logpose/main.py
    - tests/golden/40-logpose.rules.v0_2_0
decisions:
  - "Factory uses explicit if spec.key == 'ark' / else branch — ARK dispatches to arkmanager, Palworld keeps systemctl (ARK-19)"
  - "GAMES['ark'] appended AFTER 'palworld' so polkit units list renders as palserver first, arkserver second (dict insertion order stable since Python 3.7+)"
  - "Atomic commit: Tasks 1+2+3 land together — polkit golden recaptured in same commit so byte-diff harness stays 4/4 green (Pitfall 6)"
  - "ARK install admin_password precedence: --admin-password > --generate-password (secrets.token_urlsafe(16)) > hidden prompt (ARK-05)"
  - "Port collision probe runs BEFORE any apt action — fail early (ARK-07)"
metrics:
  tasks_completed: 3
  tasks_total: 3
  commits: 1
  completed: "2026-04-13"
---

# Phase 5 Plan 2: GAMES["ark"] + Factory Branches Summary

Flip-the-switch plan — inserts `GAMES["ark"]` and branches `_build_game_app` for ARK arkmanager dispatch while leaving Palworld byte-identical. All three tasks land in a single atomic commit so the byte-diff harness stays green across the boundary.

## Commits

| Hash | Subject |
|------|---------|
| 8476d3a | feat(05-02): wire GAMES["ark"] + factory branches + recapture polkit golden |

## What Was Built

### CLI-boundary validation (ARK-04, ARK-06, ARK-07)
- `_ARK_SUPPORTED_MAPS` — 12-tuple per ARK-06.
- `_ARK_FORBIDDEN_SESSION_CHARS` — `"`, `$`, backtick, `\`.
- `_validate_ark_map(value)` — rejects unsupported maps with `typer.BadParameter`.
- `_validate_ark_session_name(name)` — rejects unsafe chars; warns on >63 chars.
- `_probe_port_collision(ports)` — scans `ss -tuln` output; `typer.Exit(1)` if any in use.

### GAMES registry extension
- `GAMES["ark"]` inserted AFTER `"palworld"` with all 14 GameSpec fields populated:
  - `app_id=376030`
  - `server_dir=Path("/home/steam/ARK")`
  - `settings_path=_ARK_INSTANCE_CFG`
  - `default_settings_path=None`, `settings_section_rename=None`
  - `service_name="arkserver"`
  - `settings_adapter=SettingsAdapter(parse=_arkmanager_parse, save=_arkmanager_save)`
  - `post_install_hooks=[]` (ARK-12 — arkmanager owns SDK setup)
  - `install_options` with port_default=7778, query_port=27015, rcon_port=27020, players=10, map="TheIsland", session_name="logpose-ark", branch="preaquatica", supported_maps.

### Factory branching (`_build_game_app`)
- **`if spec.key == "ark":`** — 11 verbs:
  - `install` with 12 flags (`--map`, `--port`, `--query-port`, `--rcon-port`, `--players`, `--session-name`, `--admin-password`, `--password`, `--beta`, `--generate-password`, `--enable-autostart`, `--start`).
  - `start`/`stop`/`restart`/`status`/`saveworld`/`backup` → `sudo -u steam /usr/local/bin/arkmanager <verb>`.
  - `update` → runs arkmanager update --validate --beta=... TWICE (self-update quirk, ARK-19).
  - `enable`/`disable` → `sudo systemctl enable/disable arkserver` (only meaningful with --enable-autostart).
- **`else:` (Palworld)** — verbatim Phase-4 body (PAL-09 invariant — logic unchanged; pushed one indent level deeper).
- **Shared `edit-settings`** — unchanged; SettingsAdapter-driven (SET-02).

### Polkit golden re-capture
- `tests/golden/40-logpose.rules.v0_2_0` — 300 bytes now, units list is `"palserver.service", "arkserver.service"`.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `python -c "from logpose.main import GAMES; assert list(GAMES.keys()) == ['palworld', 'ark']"` → OK ✅
- `logpose --help` → shows `palworld` and `ark` sub-commands ✅
- `logpose ark --help` → shows `install`, `start`, `saveworld`, `backup`, etc. ✅
- `logpose ark install --help` → shows all 12 flags ✅
- `logpose palworld --help` → unchanged Phase-4 verbs ✅
- `pytest tests/test_palworld_golden.py -x` → 4 passed (test 4 polkit golden now matches updated golden) ✅
- `grep -c '"arkserver.service"' tests/golden/40-logpose.rules.v0_2_0` → 1 ✅
- `grep -c '"palserver.service"' tests/golden/40-logpose.rules.v0_2_0` → 1 ✅

## Self-Check: PASSED

- FOUND commit: 8476d3a
- FOUND: GAMES["ark"] key in logpose/main.py
- FOUND: `if spec.key == "ark":` branch in _build_game_app
- FOUND: 11 ARK verbs + 9 Palworld verbs + shared edit-settings
- Byte-diff harness: 4/4 green after atomic commit (Pitfall 6 mitigated)
