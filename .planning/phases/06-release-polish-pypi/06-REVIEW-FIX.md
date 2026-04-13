---
phase: 06-release-polish-pypi
fixed_at: 2026-04-13T00:00:00Z
review_path: .planning/phases/06-release-polish-pypi/06-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-04-13
**Source review:** `.planning/phases/06-release-polish-pypi/06-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, IN-01)
- Fixed: 3
- Skipped: 0
- Out-of-scope (confirmation-only, no action required per review): IN-02, IN-03

## Fixed Issues

### IN-01: Palworld Quick Start claims "defaults (port 8211, 32 players)" but example overrides players to 16

**Files modified:** `README.md`
**Commit:** `b96025e`
**Applied fix:** Reworded the Quick Start comment from `# Install with defaults (port 8211, 32 players) and start immediately` to `# Install at port 8211 with a 16-player cap and start immediately`, matching the phrasing style used later in the Palworld Usage section (line 80). The example command (`--players 16 --start`) is preserved — the comment now accurately describes what the command does, and a 32-player example remains in the Palworld Usage block at lines 78-80.

---

### WR-02: ARK Quick Start labels `--admin-password` as "required", but the flag is `Optional[str]` and prompts hidden if missing

**Files modified:** `README.md`
**Commit:** `f76b6f8`
**Applied fix:** Replaced the single-line "required" comment with a two-line comment that explicitly mentions the hidden-prompt fallback:

```
# Install with the admin password you want to use (or omit --admin-password for a
# hidden prompt) and start the server
```

Matches the suggested fix from REVIEW.md verbatim. Users now understand they can either pass `--admin-password` directly, omit the flag for a `typer.prompt(hide_input=True)` fallback, or use `--generate-password` (covered by the existing follow-up sentence at line 72).

---

### WR-01: README claims `arkserver.service` is always installed — code only writes it when `--enable-autostart` is passed

**Files modified:** `README.md`
**Commit:** `b32cf30`
**Applied fix:** Two passages reworded to reflect actual `logpose/main.py:871-886` behavior (unit only written inside `if enable_autostart:` block):

1. **Features bullet (line 12):** Changed from `arkserver.service is installed but NOT enabled at boot by default — pass --enable-autostart ...` to `arkserver.service is NOT installed by default. Pass --enable-autostart to logpose ark install to write and enable the systemd unit; without the flag, manage the server exclusively through logpose ark start/stop/... (which call arkmanager directly — no systemd unit needed).`

2. **ARK Usage section prose (line 124):** Changed from `An arkserver.service unit is written but intentionally left disabled at boot — opt in with --enable-autostart (at install time) or logpose ark enable (afterwards).` to `An arkserver.service unit is written only when --enable-autostart is passed at install time; otherwise no systemd unit exists for ARK and day-to-day management goes through arkmanager directly via logpose ark <verb>.`

Per scope rules, `logpose/main.py` was NOT modified — the code's existing behavior (only write unit when `--enable-autostart` passed) is now correctly described by the README. The existing caveat at line 182 (`Only effective if arkserver.service exists — pass --enable-autostart to logpose ark install if you did not already.`) remains consistent with the reworded passages.

Both README edits landed in a single atomic commit since they address the same finding (WR-01).

## Verification

**Tier 1 (mandatory):** For each edit, re-read the modified README section to confirm fix text present and surrounding Markdown structure intact. All three passes confirmed.

**Tier 2 (syntax check):** Not applicable — README.md is prose Markdown, no syntax checker in scope. Text/structure re-read (Tier 1) covers integrity.

**Tier 3 (test suite):** `pytest` not available in the review environment (`No module named pytest`). README-only edits cannot affect Python test outcomes by construction — zero code touched, zero imports changed, no docstring-based doctests in the codebase. Tests will remain green on CI.

**Scope compliance:**
- README.md edits only. No changes to `logpose/main.py`, `pyproject.toml`, templates, or other source files.
- Version (`0.2.0` in `pyproject.toml`) unchanged — no wheel/sdist rebuild required.
- README content is not embedded in any Python module as a string constant, so no downstream effect on installed package behavior.

**Git state at end of run:**
- Three atomic commits on `main`: `b96025e` (IN-01), `f76b6f8` (WR-02), `b32cf30` (WR-01).
- Working tree clean (REVIEW-FIX.md pending user/orchestrator commit per workflow convention).

---

_Fixed: 2026-04-13_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
