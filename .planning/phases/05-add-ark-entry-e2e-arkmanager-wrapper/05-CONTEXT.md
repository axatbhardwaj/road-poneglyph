# Phase 5: Add ARK Entry + E2E (arkmanager wrapper) - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

ARK: Survival Evolved joins the registry as a first-class game — but instead of re-implementing the install/start/stop/save pipeline natively, logpose wraps the mature `arkmanager` (ark-server-tools) Bash harness under the hood. `logpose ark <verb>` provides a uniform CLI on top of arkmanager, manages `/etc/arkmanager/instances/main.cfg`, and preserves Palworld's native path untouched. E2E verified on fresh Debian 12 (compat) and Debian 13 (primary per install record).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Reference `docs/ark-install-reference.md` for the working arkmanager install recipe. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Reference document: `docs/ark-install-reference.md` — working manual install record for ARK via arkmanager on Debian 13. Phase 5 wraps this recipe as `logpose ark <verb>` commands.

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

Pivoted from native ARK install to arkmanager wrapper (see recent commits 7260be6, 10581f5). Palworld native path must remain byte-identical after ARK is added.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
