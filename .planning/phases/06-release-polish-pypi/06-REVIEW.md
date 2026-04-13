---
phase: 06-release-polish-pypi
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - pyproject.toml
  - README.md
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Phase 6 is a docs/metadata phase: `pyproject.toml` bumps the version to 0.2.0 and `README.md` is fully rewritten for the multi-game v0.2.0 CLI. Scope was checked against `logpose/main.py` (the CLI source of truth), `docs/ark-install-reference.md` (port/branch reference), and Phase 6 Plan 02 requirements.

The `pyproject.toml` change is clean — version bump is the single intended edit, and all other metadata (name, entry point, license, classifiers) remains consistent with prior phases.

The `README.md` rewrite is thorough, grep-verified against Plan 02's required-strings list, and accurate in almost all technical claims (verb names, flag names, ports, polkit path, sudoers path, SteamCMD app ids, supported map list). Two factual inconsistencies around ARK's `arkserver.service` installation lifecycle warrant correction before the README ships to PyPI — without `--enable-autostart`, the unit file is never written, which contradicts two passages that imply it is always installed. A few minor wording issues are noted as Info.

## Warnings

### WR-01: README claims `arkserver.service` is always installed — code only writes it when `--enable-autostart` is passed

**File:** `README.md:12` (also reinforced at `README.md:124`)
**Issue:** The Features bullet states:

> Opt-in autostart for ARK: `arkserver.service` is installed but NOT enabled at boot by default — pass `--enable-autostart` to `logpose ark install` or run `logpose ark enable` later.

And the ARK section prose at `README.md:124` says the `arkserver.service` unit "is written but intentionally left disabled at boot — opt in with `--enable-autostart`".

Per `logpose/main.py:871-886`, the unit file is only rendered and written to `/etc/systemd/system/arkserver.service` **inside** the `if enable_autostart:` block. Without the flag, no service unit is written at all. A user who reads the README and runs `logpose ark install ...` (no autostart flag), then later runs `logpose ark enable`, will get a systemd failure ("Unit arkserver.service does not exist") — not a "service is installed but disabled" experience. This contradicts the README's implied behavior and will trip migrating users.

The README does note the caveat correctly later at line 182 ("Only effective if `arkserver.service` exists — pass `--enable-autostart` to `logpose ark install` if you did not already."), but the earlier claims frame the unit as always installed.

**Fix:** Reword both passages to match behavior. Suggested text for the Features bullet:

```markdown
- **Opt-in autostart for ARK**: `arkserver.service` is NOT installed by default. Pass
  `--enable-autostart` to `logpose ark install` to write and enable the systemd unit;
  without the flag, manage the server exclusively through `logpose ark start/stop/...`
  (which call `arkmanager` directly — no systemd unit needed).
```

And for the ARK section prose (line 124):

```markdown
An `arkserver.service` unit is written **only when `--enable-autostart` is passed at
install time**; otherwise no systemd unit exists for ARK and day-to-day management
goes through `arkmanager` directly via `logpose ark <verb>`.
```

Alternatively, if the intent is for the unit to always be written (matching the README), change `logpose/main.py` to move the `_render_service_file` + `_write_service_file` calls outside the `if enable_autostart:` block and keep only `systemctl enable` inside it. That is a code change and out of Phase 6 scope — README correction is the pragmatic fix.

---

### WR-02: ARK Quick Start labels `--admin-password` as "required", but the flag is `Optional[str]` and prompts hidden if missing

**File:** `README.md:66-67`
**Issue:** The ARK Quick Start reads:

> Install with an admin password (required) and start the server
> `logpose ark install --map TheIsland --admin-password 'your-strong-password' --start`

Per `logpose/main.py:796-799`, `admin_password: Optional[str] = typer.Option(None, "--admin-password", ...)` — the flag itself is NOT required. If the user omits both `--admin-password` and `--generate-password`, the code at `main.py:842-846` falls back to `typer.prompt("Admin password", hide_input=True)` which hides the value from shell history. The README's "required" label is therefore ambiguous: the *credential* is required, but the *flag* is not, and interactive hidden-prompt is the safer default for a password users wouldn't want in `.bash_history`.

**Fix:** Rephrase to clarify. Suggested:

```markdown
# Install with the admin password you want to use (or omit --admin-password for a
# hidden prompt) and start the server
logpose ark install --map TheIsland --admin-password 'your-strong-password' --start
```

The follow-up sentence about `--generate-password` already handles that branch.

## Info

### IN-01: Palworld Quick Start claims "defaults (port 8211, 32 players)" but example overrides players to 16

**File:** `README.md:59-61`
**Issue:**

```markdown
# Install with defaults (port 8211, 32 players) and start immediately
logpose palworld install --port 8211 --players 16 --start
```

The comment says "defaults ... 32 players" but the command explicitly passes `--players 16`. Reads as copy-paste inconsistency.

**Fix:** Either drop "32 players" from the comment or change `--players 16` to `--players 32`. If the intent was to demo a non-default player cap, reword the comment to "Install at port 8211 with a 16-player cap and start immediately" (matching the style used later at line 80).

---

### IN-02: Migration section mentions `~/Steam/steamapps/common/PalServer` but the Palworld path derived by `logpose/main.py` uses `STEAM_DIR / "steamapps/common/PalServer"` where `STEAM_DIR = Path.home() / "Steam"`

**File:** `README.md:47`
**Issue:** The path shown (`~/Steam/steamapps/common/PalServer`) is correct against `main.py:682` (`_PAL_SERVER_DIR_LOCAL = STEAM_DIR / "steamapps/common/PalServer"`). No action required — flagging only to record that the path was verified rather than assumed.

**Fix:** None — this is a confirmation note, not a defect.

---

### IN-03: Permissions section uses `$$` in `pkcheck` example — correct for shell, but worth noting it's a verification snippet the user must run interactively

**File:** `README.md:224-226`
**Issue:** The `pkcheck` example uses `--process $$` which relies on `$$` expanding to the current shell's PID. That only works when pasted into an interactive shell (not inside, say, a shell script that backgrounds the check). Acceptable as-is for the Permissions/verification use case; no change required.

**Fix:** None — verified correct. Logged for completeness.

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
