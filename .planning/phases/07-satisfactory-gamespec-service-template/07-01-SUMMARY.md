---
phase: 07-satisfactory-gamespec-service-template
plan: 01
subsystem: satisfactory-service-template
tags: [satisfactory, systemd, steamcmd, sysctl]
dependency_graph:
  requires: []
  provides: [satisfactory.service.template, _install_satisfactory, _satisfactory_sysctl_hook, _render_satisfactory_service]
  affects: [road_poneglyph/main.py]
tech_stack:
  added: []
  patterns: [custom-renderer-for-extra-placeholders]
key_files:
  created:
    - road_poneglyph/templates/satisfactory.service.template
  modified:
    - road_poneglyph/main.py
decisions:
  - Custom renderer (_render_satisfactory_service) instead of extending generic _render_service_file — Satisfactory needs reliable_port and auto_update_line placeholders not in the standard signature
metrics:
  duration: 120s
  completed: "2026-04-20T20:46:00Z"
---

# Phase 7 Plan 01: Service Template + Install Helpers Summary

Satisfactory systemd template (KillSignal=SIGINT, TimeoutStopSec=120) and three install helpers ready for GAMES dict wiring.

## What Was Done

### Task 1: satisfactory.service.template
Created template with Type=simple, KillSignal=SIGINT (critical -- SIGTERM kills without cleanup), TimeoutStopSec=120, and {auto_update_line} conditional placeholder for ExecStartPre.

### Task 2: Install helpers
Added three functions to main.py:
- `_satisfactory_sysctl_hook()`: writes vm.max_map_count=262144 to /etc/sysctl.d/99-satisfactory.conf
- `_render_satisfactory_service()`: custom renderer handling reliable_port and auto_update_line
- `_install_satisfactory()`: SteamCMD anonymous install wrapper for app 1690800

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1-2 | 48dc0ad | feat(07-01): add satisfactory.service.template + install helpers |

## Self-Check: PASSED
