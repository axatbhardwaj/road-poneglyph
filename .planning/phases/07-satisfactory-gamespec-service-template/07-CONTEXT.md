# Phase 7: Satisfactory GameSpec + Service Template - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`GAMES["satisfactory"]` exists with the correct GameSpec, `satisfactory.service.template` uses SIGINT shutdown, install helper wraps SteamCMD (app 1690800), merged polkit covers all 3 games, and byte-diff harness proves no regression.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, research at `.planning/research/satisfactory-hosting.md`, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Reference: `.planning/research/satisfactory-hosting.md` — comprehensive technical brief covering ports, config, API, systemd, quirks.

Codebase pattern: Phase 5 (ARK) is the closest template — native SteamCMD path without wrapper tool. Key differences: SIGINT (not SIGTERM), simpler port setup (2 ports vs ARK's 4), no RCON.

</code_context>

<specifics>
## Specific Ideas

- SteamCMD app 1690800, anonymous login
- Service template: Type=simple, KillSignal=SIGINT, TimeoutStopSec=120
- Binary: FactoryServer.sh with -Port, -ReliablePort, -multihome, -log, -unattended flags
- post_install_hook: vm.max_map_count=262144 sysctl tuning
- Polkit golden recapture atomic with GAMES["satisfactory"] insertion

</specifics>

<deferred>
## Deferred Ideas

- HTTPS API client → Phase 8
- Settings editing → Phase 8
- README + release → Phase 9

</deferred>
