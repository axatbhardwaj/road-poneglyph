# Phase 6: Release Polish + PyPI - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`logpose-launcher` v0.2.0 ships to PyPI with a verified wheel, the README reflects the multi-game CLI (Palworld + ARK), and the v0.1.19 `palworld-server-launcher` release is left untouched.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. PyPI publishing (SC3) is a human-gated step — requires live API tokens.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

README must include: per-verb examples for `logpose palworld <verb>` and `logpose ark <verb>`, migration note (new install not upgrade), firewall port reference, manual polkit cleanup for old `40-palserver.rules`, new-for-v0.2.0 `/etc/sudoers.d/logpose-ark` fragment, and opt-in `arkserver.service` (disabled by default via `--enable-autostart`).

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
