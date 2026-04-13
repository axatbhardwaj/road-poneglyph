# Phase 6 — Deferred Items

Items discovered during execution that are out of scope for the current plans.

## DI-1: templates/CLAUDE.md shipped inside the wheel

- **Discovered during:** Plan 06-01 Task 2 (wheel content inspection)
- **Detail:** `[tool.setuptools.package-data] "logpose" = ["templates/*"]` includes `logpose/templates/CLAUDE.md` (1.1 KB LLM instructions file) in the published wheel. Not a runtime asset — pure documentation for Claude.
- **Impact:** Negligible (wheel stays 17 KB). Harmless at install time.
- **Remediation (future plan):** tighten the glob to `templates/*.template` in `pyproject.toml`, rebuild, confirm the four runtime templates still ship and `templates/CLAUDE.md` does not.
- **Why not fixed now:** out of scope for 06-01 (version bump) and 06-02 (README rewrite). The byte-diff harness reads templates at runtime — a glob edit should be paired with a full harness re-run and belongs in a focused packaging-polish plan (not in a v0.2.0 release plan).
