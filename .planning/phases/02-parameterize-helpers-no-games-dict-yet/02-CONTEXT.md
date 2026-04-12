---
name: Phase 2 Context
description: Auto-generated context for parameterize-helpers phase
phase: "2"
status: Ready for planning
mode: auto-generated (workflow.skip_discuss=true)
---

# Phase 2: Parameterize Helpers (no GAMES dict yet) — Context

**Gathered:** 2026-04-12
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Helper functions accept game-specific inputs as parameters (not module globals), and a byte-diff regression harness proves Palworld renders identically to v0.1.19 — the working oracle for every subsequent phase.

Requirements (from ROADMAP): ARCH-04 (partial), PAL-03, PAL-04, PAL-09 (harness half), SET-01 prep, E2E-01 (also contributes to ARCH-05, ARCH-06, PAL-01, PAL-02, PAL-06).

Success Criteria:
1. `OptionSettings=(...)` regex parser extracted into `_palworld_parse(path) -> dict[str, str]`; existing `should_quote` saver extracted into `_palworld_save(path, values)`. Byte-equivalent to v0.1.19 on fixture.
2. `_create_service_file`, `_fix_steam_sdk`, and install/settings helpers accept explicit paths/dicts as arguments instead of reading Palworld module constants directly.
3. Byte-diff test renders `palserver.service` against fixture (`user=foo`, `port=8211`, `players=32`) and asserts zero-diff against v0.1.19 golden file; script exits 0.
4. Palworld E2E behavior (install → start → edit-settings → stop) unchanged when exercised manually.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per `workflow.skip_discuss=true`. Use ROADMAP phase goal, success criteria, and codebase conventions (logpose package, Python 3.8 with `__future__` PEP-585) to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research. Known facts from prior phase 1:
- Package renamed to `logpose` (distribution: `logpose-launcher`).
- Python 3.8 support via `from __future__ import annotations` for PEP-585 types.
- Helpers currently read Palworld module-level constants; v0.1.19 behavior is the golden oracle.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond ROADMAP — discuss phase skipped. Refer to phase description and success criteria. The byte-diff harness is load-bearing for all subsequent phases: invest in a robust fixture + golden-file scheme.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
