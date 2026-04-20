# Phase 9: Release Polish + v0.3.0 Publish - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`road-poneglyph` v0.3.0 ships to PyPI with Satisfactory support, README covers all 3 games with examples, ports, and first-run guide.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion. PyPI publish is automated (tag v0.3.0 → GitHub Actions workflow). README pattern follows v0.2.0 (per-game sections with verb examples).

</decisions>

<code_context>
## Existing Code Insights

- README.md already has Palworld + ARK sections from v0.2.0 — add Satisfactory section in same format.
- pyproject.toml currently at version 0.2.0 — bump to 0.3.0.
- GitHub Actions workflow (`.github/workflows/workflow.yml`) already handles tag-triggered publish.
- pyproject.toml packages list needs `road_poneglyph` + new `satisfactory_api` module.

</code_context>

<specifics>
## Specific Ideas

README Satisfactory section must include:
- All verbs (install, start, stop, restart, status, enable, disable, update, save, edit-settings)
- Port table (7777 UDP game, 7777 TCP API, 8888 TCP reliable messaging)
- First-run instructions (claim step in-game, config generation quirk)
- RAM requirements (12-16 GB)
- Pre-shutdown save behavior explanation

</specifics>

<deferred>
## Deferred Ideas

- E2E-07 (VM install test) — deferred like Phases 4/5 pattern.

</deferred>
