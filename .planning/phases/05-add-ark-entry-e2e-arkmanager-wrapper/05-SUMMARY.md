---
phase: 05-add-ark-entry-e2e-arkmanager-wrapper
subsystem: ark-integration
tags: [ark, arkmanager, e2e-deferred, games-registry]
status: partial-complete
autonomous_plans_complete: [05-01, 05-02, 05-03]
pending_vm_plans: [05-04, 05-05]
requires: [phase-4-complete]
provides: [GAMES-ark, arkmanager-wrapper, ark-cli-verbs, ark-byte-diff-harness]
affects: [logpose/main.py, logpose/templates/, tests/]
completed: "2026-04-13 (autonomous portion)"
---

# Phase 5: Add ARK Entry + E2E (arkmanager wrapper) — Autonomous Portion Summary

Phase 5 has 5 plans total. This summary covers the **3 autonomous plans (05-01, 05-02, 05-03) that were executed on-server**. Plans 05-04 and 05-05 are `[HUMAN-NEEDED VM]` and require fresh Debian 12 + 13 VMs — they remain pending.

## Scope Completed

ARK: Survival Evolved joins the registry as a first-class game by **wrapping arkmanager** (not re-implementing install/start/stop natively). All code, templates, and unit-level tests for the ARK adapter are on main; Palworld render path remains byte-identical.

## Plans

| Plan | Name | Status | Commits |
|------|------|--------|---------|
| 05-01 | ARK install scaffolding (templates + adapter + _install_ark) | ✅ Complete | 1edb6f9, 999bdbb, 7c956fe, 9522b15 |
| 05-02 | GAMES["ark"] + factory branches + polkit golden recapture | ✅ Complete (atomic) | 8476d3a, 0d41957 |
| 05-03 | ARK byte-diff harness | ✅ Complete | 2ccecba, 65772a6, 951ca14 |
| 05-04 | Debian 13 ARK E2E | ⏸️ Pending VM | — |
| 05-05 | Debian 12 compat + Palworld regression E2E | ⏸️ Pending VM | — |

## What Exists After 05-01..05-03

### Templates (`logpose/templates/`)
- `arkserver.service.template` — static systemd unit (`User=steam`, arkmanager ExecStart/Stop).
- `logpose-ark.sudoers.template` — NOPASSWD fragment with single `{user}` placeholder.

### Code (`logpose/main.py`)
- **Adapter** — `_arkmanager_parse`, `_arkmanager_save`, `_ark_should_quote`, `_ARKMANAGER_LINE_RE` — regex-based line editor that preserves comments + quoting style.
- **Install scaffolding** — `_install_ark`, `_enable_debian_contrib_nonfree`, `_accept_steam_eula`, `_ensure_steam_user`, `_install_arkmanager_if_absent`, `_arkmanager_install_validate`, `_install_sudoers_fragment` (visudo-validated), `_seed_ark_main_cfg`, `_get_os_version_codename`.
- **CLI-boundary validation** — `_ARK_SUPPORTED_MAPS` (12-tuple), `_validate_ark_map`, `_validate_ark_session_name`, `_probe_port_collision`.
- **Registry** — `GAMES["ark"]` as 2nd entry (after `palworld`), all 14 GameSpec fields.
- **Factory** — `_build_game_app` split on `spec.key == "ark"`:
  - ARK: 11 verbs (install with 12 flags + start/stop/restart/status/saveworld/backup/update/enable/disable) — arkmanager dispatch.
  - Palworld: verbatim Phase-4 body — systemctl dispatch (PAL-09 invariant).
  - Shared `edit-settings` — SettingsAdapter-driven (SET-02).

### Tests (`tests/`)
- `tests/test_ark_golden.py` — 2 byte-diff tests (arkserver.service + sudoers rendering).
- `tests/golden/arkserver.service.v0_2_0` — 296 bytes.
- `tests/golden/logpose-ark.sudoers.v0_2_0` — 54 bytes (rendered with `user='foo'`).
- `tests/golden/40-logpose.rules.v0_2_0` — re-captured, 300 bytes, units list is `"palserver.service", "arkserver.service"`.

## Invariants Preserved

- **Palworld byte-identical** — tests 1-3 of `test_palworld_golden.py` remain green (palserver.service render unchanged). Test 4 (polkit golden) re-captured in atomic commit with `GAMES["ark"]` insertion.
- **Byte-diff harness green** — 6/6 tests passing after final commit (4 palworld + 2 ark).
- **No architectural changes** — same `GameSpec`+`GAMES` pattern from Phase 4, no subclasses, no new abstractions.

## Requirements Closed

From plan frontmatter:
- 05-01: ARK-02, ARK-08, ARK-09, ARK-11, ARK-13, ARK-14, ARK-15, ARK-16, ARK-17, ARK-18, SET-04
- 05-02: ARK-01, ARK-03, ARK-04, ARK-05, ARK-06, ARK-07, ARK-10, ARK-12, ARK-19, SET-02, SET-04, PAL-09
- 05-03: ARK-02 (byte-diff), ARK-18 (byte-diff)

## Deviations

None — all 3 plans executed exactly as written.

## Pending: [HUMAN-NEEDED VM]

- **Plan 05-04: Debian 13 ARK E2E** — requires fresh Debian 13 VM. Install `logpose-launcher` from wheel, run `logpose ark install --admin-password X --map TheIsland`, verify arkmanager state, server start, map load, save, RCON.
- **Plan 05-05: Debian 12 compat + Palworld regression E2E** — requires fresh Debian 12 VM. Confirms the Debian codename detection branch works for bookworm AND that Palworld install remains untouched on the compat OS.

Both plans require `/gsd-execute-phase 05 --from 04` on a fresh VM by a human operator — no automation path.

## Verification

- `pytest tests/ -x` → **6 passed** (4 palworld + 2 ark) ✅
- `logpose --help` shows both `palworld` and `ark` sub-commands ✅
- `logpose ark --help` shows 11 verbs ✅
- `logpose ark install --help` shows 12 flags ✅
- `logpose palworld --help` unchanged from Phase 4 ✅
- All 9 commits present in main (1edb6f9..951ca14) ✅

## Self-Check: PASSED

- All 3 per-plan SUMMARY.md files written at `.planning/phases/05-add-ark-entry-e2e-arkmanager-wrapper/`.
- Final byte-diff harness green.
- No deviations from plan; no deferred issues.
