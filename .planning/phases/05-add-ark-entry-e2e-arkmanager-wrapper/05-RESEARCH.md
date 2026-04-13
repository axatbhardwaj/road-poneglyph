# Phase 5: Add ARK Entry + E2E (arkmanager wrapper) — Research

**Researched:** 2026-04-13
**Domain:** Multi-game CLI (logpose) wrapping arkmanager (ark-server-tools v1.6.68 Bash harness) for ARK: Survival Evolved on Debian 12 / Debian 13
**Confidence:** HIGH (working install record at `docs/ark-install-reference.md` is the reference implementation; remaining unknowns are SessionName-with-apostrophes edge cases and netinstall second-run semantics)

## Summary

Phase 5 is the final code-bearing phase of the v0.2.0 milestone. After Phase 4, `logpose/main.py` already contains the `_build_game_app(spec)` factory + `add_typer` loop driven by `GAMES.values()`, the merged `40-logpose.rules.template`, the `--version` callback, and a four-test byte-diff harness covering `palserver.service.template` + `40-logpose.rules.template` (Palworld-only fixture). **Phase 5 adds exactly one entry to `GAMES`** (`"ark"`) plus a thin systemd unit template, an ARK-aware `SettingsAdapter` for `/etc/arkmanager/instances/main.cfg`, install-flow code that wraps the manual recipe in `docs/ark-install-reference.md`, and re-captures the `40-logpose.rules.v0_2_0` golden to include `arkserver.service`.

The arkmanager pivot collapsed enormous risk — the historical configparser/SIGINT/LimitNOFILE/sdk32 pitfalls in `.planning/research/PITFALLS.md` (Pitfalls 3, 4, 5, 8) are now arkmanager's problem, not logpose's. What remains is **install-environment plumbing** (apt sources + i386 arch + EULA pre-accept + steam user + arkmanager netinstall + the steamcmd self-update double-call) and **a fundamentally different security posture for ARK** — sudoers NOPASSWD instead of polkit because arkmanager is invoked as `sudo -u steam`, not via `systemctl <verb> <unit>`.

**Primary recommendation:** Implement as 4–5 atomic plans landing in this order so the byte-diff harness stays green at every commit boundary: (1) `arkserver.service.template` + `_arkmanager_parse`/`_arkmanager_save` for `main.cfg` (no `GAMES["ark"]` yet — pure addition, harness still 4/4 green); (2) `GAMES["ark"]` entry + re-captured polkit golden + harness extended to 5 tests including ARK in the polkit unit list; (3) `_install_ark` helper + `ark`-only `install` overload in the factory (port collision probe, EULA pre-accept, steam user, netinstall, double-arkmanager-install, sudoers fragment); (4) wire `start/stop/restart/status/saveworld/backup/update` to `sudo -u steam arkmanager <verb>` instead of `systemctl <verb> arkserver`; (5) optional `arkserver.service` opt-in via `--enable-autostart` + README per-game firewall section. Treat `docs/ark-install-reference.md` Section 4 as the line-by-line spec — every command in the manual recipe must appear in code with identical flags.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation choices are at Claude's discretion — discuss phase was skipped per `workflow.skip_discuss=true` in `.planning/config.json`. The reference document `docs/ark-install-reference.md` is the working install recipe. Use ROADMAP Phase 5 goal + success criteria + REQUIREMENTS.md ARK-01..ARK-19 + codebase conventions to guide decisions.

### Claude's Discretion
- Plan splitting strategy (4 vs 5 atomic plans) — pick whatever keeps the byte-diff harness green at every commit boundary.
- Whether `_arkmanager_parse`/`_arkmanager_save` lives as two top-level functions (mirroring `_palworld_parse`/`_palworld_save`) or as a small adapter class — pick the form that minimizes diff. **Recommendation: top-level functions, mirror Palworld.**
- How to surface arkmanager exit codes (raw `_run_command` + `check=True`, or wrap with a one-line stderr-tail printer) — the install record shows arkmanager produces grep-friendly output, so raw `_run_command` is fine.
- Where to put the sudoers-fragment template (in `logpose/templates/` like the polkit rule, or string-literal in code) — **recommendation: template, for symmetry with polkit + visible to template/CLAUDE.md inventory.**
- Whether `logpose ark install --start` defaults to `--enable-autostart` (no, per ROADMAP Plan 9: "auto-start at boot is opt-in" — `--start` runs the server now; `--enable-autostart` enables boot persistence; the two flags are independent).

### Deferred Ideas (OUT OF SCOPE)
None — discuss phase skipped. All ARK-related deferrals already live under `## v2 Requirements` in `REQUIREMENTS.md` (mods, RCON CLI, cluster, Game.ini editing, ASA/Proton).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID     | Description                                                                                                            | Research Support |
|--------|------------------------------------------------------------------------------------------------------------------------|------------------|
| ARK-01 | `GAMES["ark"]` entry with the documented field set                                                                     | `## GameSpec Fit for ARK` (schema mapping; no schema expansion needed) |
| ARK-02 | `arkserver.service.template` thin wrapper: `Type=forking`, `RemainAfterExit=yes`, `ExecStart=/usr/bin/sudo -u steam …` | `## arkserver.service Template` (verbatim from install record §4.10 launch line + arkmanager start/stop semantics) |
| ARK-03 | Launch args owned by arkmanager via `main.cfg` ark_* keys                                                              | `## Settings Adapter — main.cfg Round-Trip` (regex line editor) |
| ARK-04 | ARK SessionName written to `main.cfg` as `ark_SessionName="…"`; 63-char soft warning at CLI boundary                   | `## SessionName Quoting` (CAVEAT below — arkmanager docs explicitly recommend `.ini` for special chars) |
| ARK-05 | Install flag set: map, port, query-port, rcon-port, players, session-name, admin-password, password, beta, enable-autostart, start | `## Install Flag Surface` |
| ARK-06 | Map enum validation against the 12 supported maps                                                                      | `## Map Enum` |
| ARK-07 | Port collision probe via `ss -tuln` before install                                                                     | `## Port Probe` |
| ARK-08 | Settings parser/saver targets `main.cfg` (bash-sourced syntax), not `GameUserSettings.ini` — regex line editor         | `## Settings Adapter — main.cfg Round-Trip` |
| ARK-09 | Editor preserves original line order + unrelated keys (in-place edit, not full rewrite)                                | `## Settings Adapter — main.cfg Round-Trip` |
| ARK-10 | Install-time seed of `main.cfg` with all install-flag values; `GameUserSettings.ini` NOT touched by logpose            | `## Install-Time main.cfg Seed` |
| ARK-11 | Apt deps minimum set (Debian 13 verified): steamcmd, libc6-i386, lib32gcc-s1, lib32stdc++6, curl, bzip2, tar, rsync, sed, perl-modules, lsof | `## Apt Dependencies` (verified against install record §4.3; Debian 12 fallbacks documented) |
| ARK-12 | `_fix_steam_sdk` Palworld-only — `GAMES["ark"].post_install_hooks` omits it                                            | `## post_install_hooks for ARK` (empty list — arkmanager + apt steamcmd handle SDK) |
| ARK-13 | RCON triad alignment in main.cfg: ark_RCONEnabled=True, ark_RCONPort, ark_ServerAdminPassword                          | `## RCON Triad` |
| ARK-14 | netinstall.sh idempotent install (skip if `/usr/local/bin/arkmanager` exists)                                          | `## arkmanager netinstall.sh — Idempotency Reality Check` |
| ARK-15 | Pre-accept Steam EULA via debconf-set-selections (`steam/question` + `steamcmd/question`)                              | `## Apt Dependencies — EULA Pre-accept` |
| ARK-16 | Create `steam` service user if absent (`useradd -m -s /bin/bash steam`)                                                | `## Steam Service User` (CRITICAL: arkmanager's install.sh does NOT create the user) |
| ARK-17 | Run `sudo -u steam arkmanager install --beta=<branch> --validate` TWICE                                                | `## The steamcmd Double-Call Quirk` (verified in install record §4.9) |
| ARK-18 | Sudoers fragment at `/etc/sudoers.d/logpose-ark` with NOPASSWD for `arkmanager *`                                      | `## Sudoers Fragment` |
| ARK-19 | `logpose ark <verb>` delegates to `sudo -u steam arkmanager <verb>` (with `update` running twice)                      | `## Verb Delegation Map` |
| SET-02 | `logpose ark edit-settings` works out-of-the-box via `_arkmanager_parse`/`_arkmanager_save` adapter                    | `## Settings Adapter — main.cfg Round-Trip` |
| SET-04 | ARK uses install-time seed (ARK-10) instead of a default template (no `default_settings_path`)                         | `## GameSpec Fit for ARK` (sets `default_settings_path=None`) |
| POL-05 | `pkcheck` verification — Palworld in Phase 5 VM E2E; ARK uses sudoers, not polkit                                       | `## Polkit + Sudoers Posture` |
| PAL-09 | Byte-diff regression — `palserver.service` render unchanged after ARK lands                                            | `## Byte-Diff Harness Plan` (golden re-capture only for `40-logpose.rules.v0_2_0`, NEVER for `palserver.service.v0_1_19`) |
| E2E-03 | Fresh Debian 12 VM E2E for Palworld                                                                                    | `## E2E Plan` (defaults from Phase 2/4 deferrals roll up here) |
| E2E-04 | Fresh Debian 12 VM E2E for ARK                                                                                         | `## E2E Plan` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Root `CLAUDE.md` and the directory-scoped `CLAUDE.md` files in `logpose/`, `logpose/templates/`, and `docs/` were loaded. Extracted constraints:

| Constraint                                                                          | Source                          | Impact on Phase 5                                                  |
|-------------------------------------------------------------------------------------|---------------------------------|--------------------------------------------------------------------|
| Everything lives in `logpose/main.py` + `logpose/templates/` (no `core/`, no `games/`) | Root + logpose/CLAUDE.md (implied via "Files" tables)        | ARK code lands in `main.py`; new template in `templates/`. Update `templates/CLAUDE.md` table when `arkserver.service.template` is added.        |
| Templates are systemd unit + polkit-style files; document each new one in `templates/CLAUDE.md` | logpose/templates/CLAUDE.md      | Add `arkserver.service.template` (and possibly `logpose-ark.sudoers.template`) to the table. |
| Reference document for ARK is `docs/ark-install-reference.md` — Phase 5 wraps that recipe | docs/CLAUDE.md (explicit table entry) | Read end-to-end before planning; every command in §4 maps to code. |
| Keep `_repair_package_manager()` load-bearing                                       | REQUIREMENTS.md "Out of Scope"  | Call it from the ARK install path (same pattern as `_install_steamcmd`); do not refactor. |

These rules have the same authority as locked decisions from CONTEXT.md.

## Standard Stack

### Core (already shipped — no new runtime deps)

| Library / Tool   | Version             | Purpose                                          | Why Standard                                                          |
|------------------|---------------------|--------------------------------------------------|-----------------------------------------------------------------------|
| typer            | `>=0.9,<0.21`       | CLI subcommand routing (already locked Phase 4)  | Phase 4 factory + `add_typer` loop already absorbs new GAMES entries. |
| rich             | `>=13.0,<14`        | Console + table editor (shared via SettingsAdapter) | Already used; ARK reuses `_interactive_edit_loop` unchanged.        |
| Python stdlib `re` | 3.8+              | Regex line-edit for `main.cfg` (key="value")     | `main.cfg` is sourced bash, NOT INI — `configparser` is wrong tool.   |
| Python stdlib `secrets` | 3.8+         | `secrets.token_urlsafe(16)` for `--generate-password` | Cryptographically secure; same primitive ARK community recommends.   |
| Python stdlib `subprocess` | 3.8+      | `_run_command` is the existing pipeline           | Reuse — do not introduce `Popen` wrappers.                            |

### External (system-level — not pip)

| Tool        | Version        | Purpose                                           | Source / Verification                                       |
|-------------|----------------|---------------------------------------------------|-------------------------------------------------------------|
| arkmanager (ark-server-tools) | **v1.6.68** (released **2025-12-13**) | Wrapped Bash harness — owns install/start/stop/save/RCON/backup/update for ARK | `[VERIFIED: api.github.com/repos/arkmanager/ark-server-tools/releases/latest]` checked 2026-04-13: `tag_name=v1.6.68`, `published_at=2025-12-13T10:03:56Z`. Same version installed in `docs/ark-install-reference.md` §4.5. |
| steamcmd (Debian apt) | latest from `non-free` (Debian) / `multiverse` (Ubuntu) | Steam download client | `[VERIFIED: install record §4.3]` — installed via `apt-get install steamcmd` on Debian 13, lands at `/usr/games/steamcmd`. |
| netinstall.sh | master branch | Bootstraps arkmanager onto the system via curl-pipe | `[VERIFIED: github.com/arkmanager/ark-server-tools/blob/master/netinstall.sh]` — accepts `<user>` as first positional arg; delegates to `tools/install.sh`. |

### Alternatives Considered

| Instead of (recommended)                       | Could Use                                              | Tradeoff                                                                                                     |
|------------------------------------------------|--------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `_arkmanager_parse` regex line editor          | `shlex` + manual reparse                                | shlex would handle quoting better but doesn't preserve comment/whitespace lines — breaks ARK-09. Regex wins. |
| arkmanager wrapper                              | Native steamcmd + custom systemd (the original Phase 5 plan) | Already rejected by 2026-04-12 pivot. arkmanager v1.6.68 already solves SIGINT, LimitNOFILE, branch opt-out, RCON triad. |
| ConfigParser for `main.cfg`                     | hand-rolled regex                                      | `main.cfg` is sourced shell, not INI. `[section]` headers don't exist; `key="value"` is bash assignment. ConfigParser would mangle it. |
| Single `sudo -u steam arkmanager` ExecStart in arkserver.service | direct `ShooterGameServer` ExecStart        | Direct path needs LimitNOFILE/KillSignal/TimeoutStopSec dance (Pitfall 3 + 4). arkmanager wraps all of that — keep the wrapper, follow the install record.    |

**Installation:** No pip changes needed. arkmanager is installed at runtime by `_install_ark` helper.

**Version verification (Phase 5 plan-time check):** Before the planner locks ARK-14 wording, re-run the GitHub API check for `arkmanager/ark-server-tools` latest release. If it has moved past v1.6.68, update the success-criteria narrative (the netinstall script always pulls master HEAD, so the running version matches whatever is current at install time — but the installed version should be logged in the install record).

## Architecture Patterns

### Recommended Phase 5 File Structure

```
logpose/
├── main.py                                    # ALL Phase 5 code (no submodules)
└── templates/
    ├── palserver.service.template             # UNCHANGED
    ├── 40-logpose.rules.template              # UNCHANGED template; rendered output gains arkserver.service
    ├── arkserver.service.template             # NEW — thin arkmanager wrapper
    └── logpose-ark.sudoers.template           # NEW (recommended) — passwordless sudo to steam user
tests/
├── test_palworld_golden.py                    # 4 tests → 4 tests (golden re-captured for polkit only)
└── golden/
    ├── palserver.service.v0_1_19              # UNCHANGED (PAL-09 invariant)
    └── 40-logpose.rules.v0_2_0                # RE-CAPTURED with arkserver.service in units
```

### Pattern 1: GAMES Registry Extension (single dict insertion)

**What:** Add one literal `GAMES["ark"] = GameSpec(...)` entry. Phase 4's `for _key, _spec in GAMES.items(): app.add_typer(...)` loop auto-registers the ARK sub-app; `_setup_polkit(user)` reads `GAMES.values()` globally so the merged polkit rule auto-includes `arkserver.service`.

**When to use:** Always. This is exactly the affordance the GameSpec architecture was built for.

**Example:**
```python
# Source: logpose/main.py:371-392 (existing GAMES["palworld"] mirrored)
_ARK_INSTANCE_CFG = Path("/etc/arkmanager/instances/main.cfg")

def _ark_post_install_noop() -> None:
    """ARK has no post-install hooks — arkmanager + apt steamcmd handle SDK setup."""
    pass  # explicit no-op for symmetry; alternative is post_install_hooks=[]

GAMES["ark"] = GameSpec(
    key="ark",
    display_name="ARK: Survival Evolved",
    app_id=376030,
    server_dir=Path("/home/steam/ARK"),
    binary_rel_path="ShooterGame/Binaries/Linux/ShooterGameServer",
    settings_path=_ARK_INSTANCE_CFG,
    default_settings_path=None,                     # SET-04: install-time seed instead
    settings_section_rename=None,                   # ARK-09: no header rewrite for main.cfg
    service_name="arkserver",
    service_template_name="arkserver.service.template",
    settings_adapter=SettingsAdapter(parse=_arkmanager_parse, save=_arkmanager_save),
    post_install_hooks=[],                          # ARK-12: empty
    apt_packages=[
        "steamcmd", "libc6-i386", "lib32gcc-s1", "lib32stdc++6",
        "curl", "bzip2", "tar", "rsync", "sed", "perl-modules", "lsof",
    ],
    steam_sdk_paths=[],                             # ARK-12: arkmanager owns SDK
    install_options={
        "port_default": 7778,                       # arkmanager raw socket; game port 7777 is implicit
        "players_default": 10,                      # install record §3
        "query_port_default": 27015,
        "rcon_port_default": 27020,
        "map_default": "TheIsland",
        "session_name_default": "logpose-ark",
        "branch_default": "preaquatica",
        "supported_maps": (
            "TheIsland", "TheCenter", "ScorchedEarth_P", "Aberration_P",
            "Extinction", "Ragnarok", "Valguero_P", "CrystalIsles",
            "LostIsland", "Fjordur", "Genesis", "Genesis2",
        ),
    },
)
```

### Pattern 2: ark-Specific Install Branch Inside the Factory

**What:** The current `_build_game_app(spec)` factory has a single `install` command with `(port, players, start)` flags. Phase 5 must expand this WITHOUT breaking Palworld. Recommended: branch on `spec.key`. Per `.planning/research/ARCHITECTURE.md` §"Typer Subcommand Composition Pattern" line 141–158, the canonical pattern is `if spec.key == "palworld": @sub.command() def install(...) elif spec.key == "ark": @sub.command() def install(...)`. **This is acceptable because each branch closes over the same `spec` and the symmetry is preserved at the verb-name level.**

**When to use:** Whenever per-game flag surfaces diverge enough that a single `install(**common)` signature would lose `--help` clarity. ARK has 11 install flags vs Palworld's 3 — a single signature is wrong.

**Anti-pattern:** Do NOT use `**kwargs` — Typer cannot introspect it; `--help` becomes useless. (Pitfall 7 in PITFALLS.md.)

### Pattern 3: arkmanager Verb Delegation

**What:** For `start/stop/restart/status/saveworld/backup/update`, the existing factory's `_run_command(f"systemctl {verb} {spec.service_name}")` is **wrong for ARK**. Branch on `spec.key` (or check `spec.install_options` for an `"uses_arkmanager": True` flag) and dispatch to `sudo -u steam /usr/local/bin/arkmanager <verb>`.

**When to use:** Per ARK-19. `update` runs twice (same self-update quirk as install).

**Example:**
```python
# Inside _build_game_app, replacing the current @sub.command() def start():
if spec.key == "ark":
    @sub.command()
    def start() -> None:
        """Start the ARK server via arkmanager."""
        _run_command("sudo -u steam /usr/local/bin/arkmanager start")
    # ... same shape for stop/restart/status/saveworld/backup
    @sub.command()
    def update() -> None:
        """Update ARK via arkmanager (runs twice — steamcmd self-update quirk)."""
        _run_command("sudo -u steam /usr/local/bin/arkmanager update --validate --beta=preaquatica", check=False)
        _run_command("sudo -u steam /usr/local/bin/arkmanager update --validate --beta=preaquatica")
else:
    # existing systemctl-based verbs for Palworld
```

### Anti-Patterns to Avoid

- **Per-game module split (`logpose/games/ark.py`):** Forbidden by ARCH-05. Everything in `main.py`.
- **`BaseGame` subclass for ARK to override `start()`:** Same — explicitly rejected.
- **Editing `GameUserSettings.ini` from logpose:** Forbidden by ARK-08 + ARK-10. arkmanager owns it. `logpose ark edit-settings` targets `main.cfg` only.
- **Using `configparser` for `main.cfg`:** It's sourced bash (`key="value"`), not INI. Will mangle quotes and section headers don't exist.
- **Adding ExecStop=arkmanager stop with a hard-kill fallback:** Pitfall 4 — failing ExecStop turns systemctl stop into hard-kill. arkmanager's own stop already does graceful save-and-exit; don't second-guess it.

## Don't Hand-Roll

| Problem                                       | Don't Build                                                | Use Instead                                                                          | Why                                                                              |
|-----------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| ARK install / steamcmd orchestration          | Custom `_install_ark_native` re-implementing Pitfalls 1–4   | `arkmanager install --beta=preaquatica --validate` (run twice)                       | arkmanager already solves the steamcmd self-update quirk, branch opt-out, validate retries. |
| `GameUserSettings.ini` parsing                | configparser shim with `optionxform=str` + strict=False     | Don't touch the file — arkmanager + game runtime own it                              | Pitfall 5 has 3 distinct configparser failure modes; sidestepping the file removes the entire risk class. |
| ARK SIGINT / TimeoutStopSec dance             | Custom systemd unit with `KillSignal=SIGINT TimeoutStopSec=300` | arkmanager's own `stop` (called via `ExecStop=` in the thin wrapper unit, or via `sudo -u steam arkmanager stop` from CLI) | arkmanager already does graceful RCON saveworld-then-quit. Re-implementing risks hard-kill on ExecStop failure (Pitfall 4). |
| `LimitNOFILE` + `TasksMax` tuning             | Per-unit limits in `arkserver.service`                      | Skip — install record §8 explicitly dropped these                                    | Modern Debian 13 default soft limit is high enough; arkmanager does not need them in the working install record. |
| Steam SDK sdk32/sdk64 fix for ARK             | Generalize `_fix_steam_sdk` for ARK's dual-path requirement | No-op — arkmanager + apt steamcmd package handle this                                | Pitfall 2 was for native install. arkmanager's `install.sh` symlinks the right paths. |
| RCON client                                   | Wrapping `mcrcon` or rolling a `socket` RCON                | `arkmanager rconcmd "..."`                                                           | Already in arkmanager. Out of v0.2.0 scope (NEXT/ENH-08).                        |
| Backup / restore                              | tar pipeline + retention logic                              | `arkmanager backup`                                                                   | Built into arkmanager. v2 deferral (ENH-06).                                     |
| Mod management                                | Steam Workshop mod download orchestration                    | Set `ark_GameModIds=` in `main.cfg` via `edit-settings` + `arkmanager installmods`   | v2 deferral (ENH-05).                                                            |
| Steam user creation in arkmanager             | Trusting `netinstall.sh` to create the user                 | **Create steam user yourself** before invoking netinstall                            | `[VERIFIED: github.com/arkmanager/ark-server-tools/blob/master/tools/install.sh]` — install.sh validates user via `getent passwd "$1"` and **does NOT create it**. ARK-16 is mandatory. |

**Key insight:** The arkmanager pivot reduces logpose's ARK code surface to: (a) adapter for `main.cfg`, (b) install-environment plumbing (apt + EULA + user + sudoers + netinstall + double-call + main.cfg seed), and (c) verb delegation. Everything else is arkmanager's job. The temptation to "add one helpful feature on top" is the wrong instinct — every such feature reintroduces a pitfall arkmanager already handles.

## Runtime State Inventory

> Phase 5 is primarily an **additive** phase (new GAMES entry + new template + install-time runtime state on the target VM). It is NOT a rename/refactor. But the install creates substantial OS-registered state that future uninstall/upgrade phases must know about.

| Category                 | Items Created at `logpose ark install` time                                                                                              | Action Required (this phase)                              |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| Stored data              | `/home/steam/ARK/` (~18 GB game files); `/home/steam/.steam/` cache; `/home/steam/ARK-Backups/`; `/home/steam/ARK/ShooterGame/Saved/SavedArks/*.ark` save files (created at first start) | Document in install completion message + README; no migration logic needed (greenfield install). |
| Live service config      | `/etc/arkmanager/arkmanager.cfg` (created by netinstall, edited at install: `steamcmdroot="/usr/games"`, `steamcmdexec="steamcmd"`); `/etc/arkmanager/instances/main.cfg` (seeded by logpose with all install-flag values) | Implement seed logic (ARK-10); document keys edited.      |
| OS-registered state      | `/etc/systemd/system/arkserver.service` (only if `--enable-autostart`); `/etc/sudoers.d/logpose-ark` (always); `/etc/polkit-1/rules.d/40-logpose.rules` (re-rendered to include `arkserver.service`); apt `i386` foreign architecture; `contrib non-free` in `/etc/apt/sources.list`; debconf selections for `steam`/`steamcmd` license; `steam` user (uid 1000 typically); `/usr/local/bin/arkmanager`, `/usr/local/libexec/arkmanager/`, `/usr/local/share/arkmanager/` | Implement registration logic in `_install_ark`. **Document reversal in README per Phase 6 / install record §10.** |
| Secrets/env vars         | `ark_ServerAdminPassword=<pw>` in `/etc/arkmanager/instances/main.cfg` (world-readable as 0644 by default — see Security Mistake in PITFALLS.md); `ark_ServerPassword=<pw>` if set | After seed write, `chmod 0640` on `main.cfg` and `chgrp steam` (so steam user reads it but other users on box don't). |
| Build artifacts          | None for ARK install. Phase 1 already cleaned `egg-info/`.                                                                                | None — verified Phase 1 SUMMARY.                          |

**Nothing found in category — Build artifacts:** None — Phase 1 removed all `*.egg-info/` from git tracking (PKG-06); the current `logpose_launcher.egg-info/` on disk is the result of `pip install -e .` and is gitignored.

## Apt Dependencies

### Minimum Set (Debian 13 verified per install record §4.3)

| Package         | Why                                                                       | Verified |
|-----------------|---------------------------------------------------------------------------|----------|
| `steamcmd`      | Steam install client (i386 binary)                                         | ✓ install record §4.3 |
| `libc6-i386`    | 32-bit libc — required by steamcmd & ShooterGameServer                     | ✓ install record §4.3 |
| `lib32gcc-s1`   | 32-bit libgcc                                                              | ✓ install record §4.3 (Pitfall 1's `lib32gcc1` fallback dropped — Debian 12 ships `lib32gcc-s1` since bullseye) |
| `lib32stdc++6`  | 32-bit libstdc++                                                           | ✓ install record §4.3 |
| `curl`          | netinstall.sh fetch                                                        | ✓ install record §4.3 |
| `bzip2`, `tar`, `rsync`, `sed`, `perl-modules`, `lsof` | arkmanager runtime deps                          | ✓ install record §4.3 |

### Dropped from PITFALLS.md Pitfall 1 (training-data assumption was stale)

| Package          | Why dropped                                                                                  |
|------------------|----------------------------------------------------------------------------------------------|
| `libncurses5`    | Not required by arkmanager v1.6.68 — install record §4.3 omits it; verified install was successful. |
| `libncursesw5`   | Same.                                                                                        |
| `libsdl2-2.0-0`  | Same.                                                                                        |

`[VERIFIED: docs/ark-install-reference.md §4.3]`

### EULA Pre-accept (ARK-15) — exact debconf selections

```bash
# Source: install record §4.2 — copy verbatim
echo steam steam/question select "I AGREE"     | debconf-set-selections
echo steam steam/license note ''                | debconf-set-selections
echo steamcmd steam/question select "I AGREE"   | debconf-set-selections
echo steamcmd steam/license note ''             | debconf-set-selections
```

**MUST run before** `apt-get install steamcmd`. Otherwise apt will block on a TUI dialog. The existing `_install_steamcmd()` already does the equivalent for Palworld (lines 140–149 of `logpose/main.py`) — verify it's idempotent for ARK call too, OR add a separate `_install_ark_apt_deps()` helper.

### Apt Source Configuration (Debian only)

Install record §4.1 enables `contrib non-free` on Debian 13 trixie via three `sed -i` commands targeting `trixie main`, `trixie-security main`, `trixie-updates main` lines in `/etc/apt/sources.list`. **Phase 5 must replicate this for both Debian 12 (bookworm) and Debian 13 (trixie).** Detect via `_get_os_id()` (already in `main.py:56`) — but `os-release` ID alone isn't sufficient; also need version codename. Recommend reading `VERSION_CODENAME=` from `/etc/os-release` and templating the sed commands accordingly. Ubuntu uses `multiverse` instead of `contrib non-free`; the existing `_install_steamcmd()` already does `add-apt-repository multiverse -y`, so reuse that path for Ubuntu.

`dpkg --add-architecture i386` followed by `apt-get update` is mandatory and must come before installing the i386 lib packages.

## Steam Service User

**ARK-16 is non-negotiable.** `[VERIFIED: github.com/arkmanager/ark-server-tools/blob/master/tools/install.sh]` — `install.sh` calls `getent passwd "$1"` to validate the user exists and exits non-zero if not. It does NOT call `useradd`. Logpose must create the user before invoking `netinstall.sh`:

```bash
# Idempotent — runs only if user absent
if ! getent passwd steam >/dev/null; then
    useradd -m -s /bin/bash steam
fi
```

Install record §4.4 confirms this exact form. No password is set; access is only via `sudo -u steam` from the installing user (root or the user with the sudoers fragment).

## arkmanager netinstall.sh — Idempotency Reality Check

**ARK-14 says "skip netinstall if `/usr/local/bin/arkmanager` exists."** This is correct and necessary because:

`[VERIFIED: github.com/arkmanager/ark-server-tools/blob/master/tools/install.sh]` — `install.sh` (called by netinstall.sh) is **NOT fully idempotent**:
- It uses `cp -n` (no-clobber) when copying `arkmanager.cfg.example` and `instance.cfg.example` to their final paths — so existing configs are preserved (good).
- BUT if it detects an old config layout, it creates a `.NEW` version and runs migration scripts, then **exits with code 2** (bad — would break logpose's install pipeline if `_run_command` has `check=True`).
- It does NOT create the steam user (already covered in ARK-16).

**Recommendation:** Implement ARK-14 with a presence check:

```python
def _install_arkmanager_if_absent() -> None:
    if Path("/usr/local/bin/arkmanager").exists():
        console.print("arkmanager already installed; skipping netinstall.")
        return
    _run_command(
        "curl -sL https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/netinstall.sh | bash -s steam"
    )
```

**Confidence:** HIGH — verified directly from the install.sh source on GitHub.

## The steamcmd Double-Call Quirk

**ARK-17 and the `update` verb both call arkmanager TWICE.** Install record §4.9 documents this in detail:

> the first invocation returned exit 0 after ~15 seconds with only `Restarting steamcmd by request...` in the log. This is a known steamcmd quirk — the first run self-updates and bails, returning success without downloading anything. **Always re-run once after the initial self-update.**

`[VERIFIED: docs/ark-install-reference.md §4.9]`

**Implementation pattern (mandatory for both `install` and `update` verbs):**

```python
INSTALL_CMD = "sudo -u steam /usr/local/bin/arkmanager install --beta=preaquatica --validate"
_run_command(INSTALL_CMD, check=False)   # First call — exit 0 with no payload (self-update). Don't fail.
_run_command(INSTALL_CMD)                 # Second call — actual download. Must succeed.
```

For `update`, the same pattern with `update --validate --beta=preaquatica`.

**Note on the `--beta` flag:** ARK-01 sets `branch="preaquatica"` as the default. `preaquatica` is the Aquatica beta opt-out — required for current Linux builds with mod support per install record §3. To switch to stable, the operator passes `--beta ""` (empty string) per ARK-05 wording. The branch name **must** be passed to both install calls and to update calls.

## Sudoers Fragment

**ARK-18:** The installing user (whoever runs `logpose ark install` and `logpose ark <verb>` afterward) needs passwordless `sudo -u steam` access. Drop a fragment:

```
# /etc/sudoers.d/logpose-ark
{user} ALL=(steam) NOPASSWD: /usr/local/bin/arkmanager *
```

**Critical safety rules:**
1. The file MUST be `chmod 0440` (sudoers refuses readable-by-others fragments).
2. MUST be installed via `visudo -c -f <tempfile>` first to validate syntax, then `mv` to `/etc/sudoers.d/logpose-ark`. A broken sudoers file locks out all sudo. The existing `_write_via_sudo_tee` helper does NOT validate — Phase 5 needs `_install_sudoers_fragment(user)` that uses `visudo -c -f` before atomic mv.
3. The `*` wildcard at the end is intentional — it allows any subcommand+args for `arkmanager`. Sudoers wildcards in arg position match any single token; using `*` after the binary path is the standard pattern.
4. The fragment must be removed cleanly on `logpose ark uninstall` (deferred — uninstall command is out of scope for v0.2.0; document the manual cleanup in README per PKG-08).

**Recommendation:** Build the fragment from a template at `logpose/templates/logpose-ark.sudoers.template` for symmetry with `40-logpose.rules.template` and visibility in `templates/CLAUDE.md`. The template has a single `{user}` placeholder.

## arkserver.service Template (ARK-02)

Thin wrapper unit, opt-in via `--enable-autostart`. Install record §4.10 shows arkmanager backgrounds the server (Type=forking with PID file is standard arkmanager pattern), so:

```ini
# logpose/templates/arkserver.service.template
[Unit]
Description=ARK: Survival Evolved Server (via arkmanager)
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
RemainAfterExit=yes
User=root
ExecStart=/usr/bin/sudo -u steam /usr/local/bin/arkmanager start
ExecStop=/usr/bin/sudo -u steam /usr/local/bin/arkmanager stop

[Install]
WantedBy=multi-user.target
```

**Notes:**
- `User=root` is required because the unit must `sudo -u steam` (the user must be allowed to switch users). Alternative: `User=steam` + `ExecStart=/usr/local/bin/arkmanager start` (no sudo needed). **Recommendation: prefer `User=steam` direct invocation for least-privilege** — avoids the unit-level sudo dependency entirely. Validate this works against the install record's verb model: §7 shows `sudo -u steam arkmanager start` from root, but the systemd unit doesn't need to mirror the CLI shape — it just needs to run `arkmanager start` as the steam user, which `User=steam` does directly.
- No `LimitNOFILE` per `## Don't Hand-Roll`.
- No `KillSignal=SIGINT` — arkmanager's `stop` already does graceful shutdown; the unit's default SIGTERM is fine because `ExecStop=` runs first.
- Template has NO placeholders (no `{user}`, `{port}`, etc.) — arkmanager owns all that via main.cfg. **This means `_render_service_file` for ARK is essentially a no-op `template.format()` with no kwargs.** The current factory passes 6 kwargs (`user`, `port`, `players`, etc.) which would cause `KeyError` if the template has no placeholders — Phase 5 must either (a) only pass kwargs the template references, or (b) make `_render_service_file` tolerant via inspecting `string.Formatter().parse(template)` placeholder set first. **Recommendation (b)** — mirrors the `_setup_polkit` placeholder audit pattern from Phase 4.
- No need to register this as a byte-diff golden — it's a static template with no formatting. Static comparison is enough.

## Settings Adapter — main.cfg Round-Trip

`/etc/arkmanager/instances/main.cfg` is **sourced bash**, NOT INI. Lines are either:
- Comments: `# arkmanager instance config`
- Blank
- Assignments: `key="value"` (or `key=Value` unquoted for booleans/numbers — see arkmanager `instance.cfg.example` confirmed via `[VERIFIED: github.com/arkmanager/ark-server-tools/blob/master/tools/instance.cfg.example]`)
- Commented-out assignments: `#ark_TotalConversionMod="..."`

`[VERIFIED: arkmanager instance.cfg.example]` — values are typically double-quoted; boolean/numeric values may be unquoted. Quote-when-saving discipline follows the original file's style.

### Parser (`_arkmanager_parse`)

```python
import re
_ARKMANAGER_LINE_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?(.*?)"?\s*$')

def _arkmanager_parse(path: Path) -> dict[str, str]:
    """Parse arkmanager main.cfg (sourced bash key="value")."""
    settings: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _ARKMANAGER_LINE_RE.match(line)
        if m:
            settings[m.group(1)] = m.group(2)
    return settings
```

### Saver (`_arkmanager_save`) — preserves order + comments + unrelated keys (ARK-09)

```python
def _arkmanager_save(path: Path, settings: dict[str, str]) -> None:
    """In-place rewrite: preserve all lines; mutate matching key= lines."""
    lines = path.read_text().splitlines(keepends=True)
    out = []
    seen: set[str] = set()
    for line in lines:
        m = _ARKMANAGER_LINE_RE.match(line)
        if m and m.group(1) in settings and not line.lstrip().startswith("#"):
            key = m.group(1)
            value = settings[key]
            # Preserve quoting if original was quoted; otherwise infer from value
            quoted = '"' in line.split("=", 1)[1]
            if quoted or _ark_should_quote(value):
                out.append(f'{key}="{value}"\n')
            else:
                out.append(f"{key}={value}\n")
            seen.add(key)
        else:
            out.append(line)
    # Append any keys not present in original (install-time seed for fresh main.cfg)
    for key, value in settings.items():
        if key not in seen:
            out.append(f'{key}="{value}"\n')
    path.write_text("".join(out))
```

`_ark_should_quote(value)`: quote unless value is `True`/`False`/numeric (mirrors `_palworld_save.should_quote` pattern at `logpose/main.py:265-272`).

**Edge cases (LOW confidence — needs E2E validation):**
- Values containing `"` — unlikely in practice (ARK doesn't allow them) but defensive: escape as `\"` only if observed.
- Multi-line values — arkmanager doesn't use them; explicitly do not support.
- `ark_GameModIds="123,456,789"` (comma-separated list) — parses as a single string, which is correct. Edits via `edit-settings` write back the whole comma-list verbatim.

## Install-Time main.cfg Seed (ARK-10)

If `/etc/arkmanager/instances/main.cfg` already exists (netinstall created it via `cp -n` from `instance.cfg.example`), the seed step OVERWRITES the install-flag-bearing keys via `_arkmanager_save` while preserving every other line. Required keys to seed (per ARK-10 + install record §4.7):

| Key                       | Source flag                                       | Example value         |
|---------------------------|---------------------------------------------------|-----------------------|
| `arkserverroot`           | hardcoded `/home/steam/ARK`                       | `"/home/steam/ARK"`   |
| `serverMap`               | `--map`                                            | `"TheIsland"`         |
| `ark_SessionName`         | `--session-name`                                   | `"logpose-ark"`       |
| `ark_Port`                | `--port`                                           | `"7778"`              |
| `ark_QueryPort`           | `--query-port`                                     | `"27015"`             |
| `ark_RCONEnabled`         | hardcoded `True` (ARK-13)                          | `"True"`              |
| `ark_RCONPort`            | `--rcon-port`                                      | `"27020"`             |
| `ark_ServerPassword`      | `--password` (default empty for public)            | `""`                  |
| `ark_ServerAdminPassword` | `--admin-password` (required, prompted if missing) | `"<pw>"`              |
| `ark_MaxPlayers`          | `--players`                                        | `"10"`                |

Also edit `/etc/arkmanager/arkmanager.cfg` per install record §4.6 (point at system steamcmd):

```bash
steamcmdroot="/usr/games"
steamcmdexec="steamcmd"
```

These two keys can be edited via the same `_arkmanager_save` helper pointed at `/etc/arkmanager/arkmanager.cfg`.

**Permissions:** After seeding, `chmod 0640 /etc/arkmanager/instances/main.cfg && chgrp steam /etc/arkmanager/instances/main.cfg` so the steam user can read it but other users on the box can't see the admin password (mitigates the Security Mistake from PITFALLS.md line 449).

## RCON Triad (ARK-13)

For RCON to work, three keys MUST be aligned in `main.cfg`:
1. `ark_RCONEnabled="True"`
2. `ark_RCONPort="<port>"` (default 27020)
3. `ark_ServerAdminPassword="<password>"` (NOT empty)

arkmanager appends `?RCONEnabled=True?RCONPort=<port>` to launch args automatically when these are set in main.cfg per install record §4.10 (resolved command line shows `?RCONEnabled=True?RCONPort=27020?...`).

Phase 5 install-time seed enforces all three. Validation: post-install probe via `ss -tln | grep <rcon_port>` in `--start` flow (echo a friendly hint if not listening within 10s — recall the install record noted "first map load takes 5–10 min" before the server is fully listening, so don't fail; just warn).

## Map Enum (ARK-06)

12 maps supported by arkmanager:
`TheIsland, TheCenter, ScorchedEarth_P, Aberration_P, Extinction, Ragnarok, Valguero_P, CrystalIsles, LostIsland, Fjordur, Genesis, Genesis2`

Validate at CLI boundary (Typer `Enum` or manual check before any I/O). On reject, raise `typer.BadParameter` so Typer renders the error consistently. Default: `TheIsland` (install record §3 + Pitfall 3 lower-RAM choice).

## Port Probe (ARK-07)

```python
def _probe_port_collision(ports: list[tuple[str, int]]) -> None:
    """ports: list of (proto, port). proto in {'udp','tcp'}. Raise typer.Exit if any in use."""
    out = subprocess.run(["ss", "-tuln"], capture_output=True, text=True, check=False).stdout
    for proto, port in ports:
        # Match e.g. "udp   UNCONN  0   0     0.0.0.0:7778"
        if re.search(rf"^{proto}\s+\S+\s+\S+\s+\S+\s+\S+:{port}\b", out, re.MULTILINE):
            console.print(f"[red]Port {port}/{proto} is already in use.[/red]")
            raise typer.Exit(code=1)
```

Probe set: `(udp, 7777)`, `(udp, <port>)` (raw socket = arkmanager `ark_Port`), `(udp, <query_port>)`, `(tcp, <rcon_port>)`. Run before any apt/install action so failures are early and cheap.

## Install Flag Surface (ARK-05)

```python
@sub.command()
def install(
    map: str = typer.Option("TheIsland", help="Map name (one of the 12 supported)."),
    port: int = typer.Option(7778, help="ark_Port (raw socket; game port 7777 is implicit)."),
    query_port: int = typer.Option(27015, "--query-port", help="ark_QueryPort."),
    rcon_port: int = typer.Option(27020, "--rcon-port", help="ark_RCONPort."),
    players: int = typer.Option(10, help="ark_MaxPlayers (1-70)."),
    session_name: str = typer.Option("logpose-ark", "--session-name", help="ark_SessionName."),
    admin_password: Optional[str] = typer.Option(None, "--admin-password", help="ark_ServerAdminPassword (prompted hidden if missing)."),
    password: str = typer.Option("", help="Optional ark_ServerPassword (public if empty)."),
    beta: str = typer.Option("preaquatica", help="Branch (set to '' for stable)."),
    generate_password: bool = typer.Option(False, "--generate-password", help="Generate admin password via secrets.token_urlsafe(16)."),
    enable_autostart: bool = typer.Option(False, "--enable-autostart", help="Enable arkserver.service at boot."),
    start: bool = typer.Option(False, "--start", help="Start the server after installation."),
) -> None:
    # Resolve admin_password: prompt hidden if missing AND not generate_password
    if admin_password is None:
        if generate_password:
            import secrets
            admin_password = secrets.token_urlsafe(16)
            console.print(f"[bold yellow]Generated admin password (printed once):[/bold yellow] {admin_password}")
        else:
            admin_password = typer.prompt("Admin password", hide_input=True, confirmation_prompt=False)
    # ... validation, port probe, apt, user, netinstall, double-call install, seed main.cfg, sudoers, polkit, optionally enable+start
```

## SessionName Quoting (ARK-04 + Caveat)

ARK-04 says "arkmanager already handles the quoting/escaping correctly, even for names with spaces like `bunty's game`". The install record §3 + §4.10 confirms `bunty's game` worked.

**HOWEVER:** `[CITED: arkmanager instance.cfg.example]` explicitly includes the comment *"if your session name needs special characters please use the .ini instead"* — meaning arkmanager itself flags special characters as a known caveat. Apostrophes in shell-quoted bash assignments work because `ark_SessionName="bunty's game"` is valid bash (single-quote inside double-quoted string), but characters like `"`, `$`, backtick, or `\` will break it.

**Recommendation:** At CLI boundary in `logpose ark install`:
- 63-char soft warning per ARK-04 (just print a warning; don't reject).
- Reject session names containing `"`, `$`, backtick, or `\` with a `typer.BadParameter`. This matches the safe subset that arkmanager handles transparently per the install record.
- Pass through everything else verbatim into `ark_SessionName="..."`. The `_arkmanager_save` quote-doubling logic should already handle the apostrophe case (no escaping needed).

## post_install_hooks for ARK

`GAMES["ark"].post_install_hooks = []` per ARK-12. arkmanager + apt steamcmd handle all SDK setup. Do NOT generalize `_fix_steam_sdk` for ARK; keep it Palworld-specific (`_palworld_sdk_hook` already wraps it correctly at `logpose/main.py:366-368`).

## Verb Delegation Map (ARK-19)

| logpose verb       | Palworld dispatch                          | ARK dispatch                                                              |
|--------------------|--------------------------------------------|---------------------------------------------------------------------------|
| `install`          | (custom; existing factory body)            | (custom; ARK install branch above)                                        |
| `start`            | `systemctl start palserver`                | `sudo -u steam /usr/local/bin/arkmanager start`                           |
| `stop`             | `systemctl stop palserver`                  | `sudo -u steam /usr/local/bin/arkmanager stop`                            |
| `restart`          | `systemctl restart palserver`               | `sudo -u steam /usr/local/bin/arkmanager restart`                         |
| `status`           | `systemctl status palserver` (check=False)  | `sudo -u steam /usr/local/bin/arkmanager status` (check=False)            |
| `enable`           | `systemctl enable palserver`                | `systemctl enable arkserver` (only meaningful if `--enable-autostart` was used at install) |
| `disable`          | `systemctl disable palserver`               | `systemctl disable arkserver`                                             |
| `update`           | `_run_steamcmd_update(...)`                 | `arkmanager update --validate --beta=preaquatica` × 2                     |
| `edit-settings`    | (existing — adapter-driven)                 | (same — adapter-driven; just `spec.settings_adapter` is `_arkmanager_parse`/`save`) |

## Polkit + Sudoers Posture

**Two access models coexist after Phase 5:**
1. **Polkit (Palworld):** `/etc/polkit-1/rules.d/40-logpose.rules` whitelists `palserver.service` AND `arkserver.service` for the installing user — so `systemctl <verb> palserver` AND `systemctl <verb> arkserver` (the autostart wrapper, if enabled) work without sudo. POL-05 verification via `pkcheck` covers both unit names.
2. **Sudoers (ARK runtime control):** `/etc/sudoers.d/logpose-ark` allows the installing user to run `sudo -u steam /usr/local/bin/arkmanager *` with NOPASSWD. This is what `logpose ark <start|stop|...>` relies on — those commands are NOT systemctl invocations on the arkserver unit.

**Why both:** arkmanager's runtime model is "switch to steam user, run the bash harness". `systemctl start arkserver` (only useful if autostart enabled) is a separate cold-boot path that polkit covers. `sudo -u steam arkmanager start` is the warm-control path that sudoers covers. Phase 5 must implement both.

**POL-05 update for ARK:** The verification command `pkcheck --action-id=org.freedesktop.systemd1.manage-units --process $$ --detail unit arkserver.service` only makes sense if the arkserver.service unit has been installed (i.e., `--enable-autostart` was used). Otherwise the unit doesn't exist and pkcheck returns "no such unit" rather than allowed/denied. Document this in the Phase 5 verification — POL-05 for ARK is conditional on the autostart path; the always-on path is the sudoers fragment.

## Byte-Diff Harness Plan

The four existing tests in `tests/test_palworld_golden.py`:

| # | Test                                                                       | Status after Phase 5                                                                                                                             |
|---|----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | `test_palserver_service_byte_identical_to_v0_1_19`                          | **MUST stay green** (PAL-09 invariant). `palserver.service.template` is NOT touched.                                                              |
| 2 | `test_golden_matches_v0_1_19_tag`                                          | **MUST stay green**. Same — palserver.service.template not edited.                                                                              |
| 3 | `test_render_service_file_byte_identical_to_golden`                        | **MUST stay green**. Same.                                                                                                                       |
| 4 | `test_polkit_rule_byte_identical_to_v0_2_0_golden`                          | **WILL fail when GAMES["ark"] lands** because the rendered units list grows from `["palserver.service"]` to `["palserver.service", "arkserver.service"]`. Phase 5 plan that adds GAMES["ark"] MUST also re-capture `tests/golden/40-logpose.rules.v0_2_0` to match the new render. |

**New test recommended (optional but cheap):** `test_arkserver_service_template_static` — compares `arkserver.service.template` byte-for-byte against a committed golden `tests/golden/arkserver.service.v0_2_0`. Since the template has no placeholders, this is a static-file diff, but it locks the unit definition against drift. Adds a 5th test.

**Ordering matters in the plan split:** The `GAMES["ark"]` insertion plan and the polkit golden re-capture MUST be in the same atomic commit. Otherwise the harness goes red between commits, violating the Phase 4 invariant ("byte-diff harness green at every commit boundary").

## E2E Plan (E2E-03 + E2E-04 + the deferred Phase 2/4 criteria)

Phase 2 deferred its VM E2E (Criterion 4) and Phase 4 deferred SC #2 (Palworld install on fresh Debian 12) and SC #3 (`pkcheck` VM verification) to Phase 5. These all roll up into a single fresh-VM sweep at the end of Phase 5:

| # | Test                                                                              | VM target                       | Pass criterion                                                                                                                                  |
|---|-----------------------------------------------------------------------------------|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | `logpose --help`, `logpose palworld --help`, `logpose ark --help` smoke           | both                            | Exit 0, expected sub-trees printed.                                                                                                              |
| 2 | `logpose palworld install --port 8211 --players 16 --start` (E2E-03)              | Debian 12                       | Server advertises; `systemctl stop palserver` saves intact; no sudo prompts; `pkcheck` returns allowed for `palserver.service`.                  |
| 3 | `logpose ark install --map TheIsland --admin-password XXX --start` (E2E-04)       | Debian 12 + Debian 13 (primary) | Server advertises; RCON reachable on 27020; `arkmanager stop` saves intact; no sudo prompts (sudoers fragment in place); `main.cfg` has all 10 seeded keys; `/etc/sudoers.d/logpose-ark` valid (`visudo -c`). |
| 4 | Re-run `logpose ark install` (idempotency)                                         | Debian 13                       | Exits 0; doesn't break existing main.cfg; netinstall skipped; sudoers re-rendered cleanly.                                                       |
| 5 | `pytest tests/test_palworld_golden.py -x`                                          | dev box                         | 4 (or 5 if static arkserver template test added) tests green.                                                                                    |

**VM minimum specs per install record §1:** 16 GB RAM, ~30 GB disk for ARK (server install is 18 GB), 2+ vCPU. Palworld is far lighter.

## Common Pitfalls

### Pitfall 1: Palworld byte-diff regression from accidental Palworld-side edit

**What goes wrong:** Plan author adds an ARK branch in `_build_game_app` and accidentally tweaks the Palworld branch (e.g., reformats the closure). Tests 1–3 of the byte-diff harness fail.

**Why it happens:** Phase 5 touches the same factory function as Phase 4. Editing inside `_build_game_app` is risky because Palworld closure code is right there.

**How to avoid:** Plan structure should ADD ark-specific branches via `if spec.key == "ark"` inside the factory, never EDIT the Palworld blocks. If the diff to the Palworld code is non-empty in a Phase 5 commit, halt and audit.

**Warning signs:** `git diff HEAD~ logpose/main.py` shows changes to lines under any `# Palworld` comment or to the Palworld `install` body.

### Pitfall 2: Sudoers fragment installed without `visudo -c` validation → root locked out

**What goes wrong:** A bad sudoers fragment (typo in `User`, missing `NOPASSWD:`, stray space) renders ALL sudo broken on the box. The user can't undo the install because they need sudo to do so.

**Why it happens:** `_write_via_sudo_tee` doesn't validate. A copy-paste typo is enough.

**How to avoid:** Write to a tempfile first; run `visudo -c -f /tmp/logpose-ark.sudoers`; only on success, `mv` to `/etc/sudoers.d/logpose-ark` and `chmod 0440`.

**Warning signs:** Manual test: introduce a deliberate syntax error and verify `_install_sudoers_fragment` refuses to install.

### Pitfall 3: arkmanager invoked via `sudo` from systemd unit needs `User=root`

**What goes wrong:** `arkserver.service` with `User=steam` and `ExecStart=/usr/bin/sudo -u steam ...` fails because steam can't sudo to steam without configuration. With `User=root` and `ExecStart=/usr/bin/sudo -u steam ...`, it works.

**Why it happens:** Systemd unit `User=` controls who runs the ExecStart; sudo then needs that user to be allowed to switch.

**How to avoid:** Use `User=steam` + direct `ExecStart=/usr/local/bin/arkmanager start` (no sudo). Bypasses the issue and is least-privilege. This is the recommendation from `## arkserver.service Template` above.

**Warning signs:** `journalctl -u arkserver` shows `sudo: a password is required` or similar.

### Pitfall 4: First arkmanager install call exits 0 with no payload — second call required

**What goes wrong:** Plan author writes `_run_command(install_cmd)` once and assumes success because exit code is 0. No server files downloaded. `logpose ark start` fails because `ShooterGameServer` doesn't exist.

**Why it happens:** steamcmd self-updates on first invocation and exits before doing real work. arkmanager's exit code reflects the steamcmd exit code (0).

**How to avoid:** ALWAYS run `arkmanager install` and `arkmanager update` twice. First call with `check=False` so an actual error doesn't sneak past; second call with default `check=True`.

**Warning signs:** `_run_command` log shows "Restarting steamcmd by request..." with no download lines. After install, `ls /home/steam/ARK/ShooterGame/Binaries/Linux/ShooterGameServer` reports missing file.

### Pitfall 5: main.cfg permission too permissive — admin password world-readable

**What goes wrong:** Default `cp -n` from `instance.cfg.example` creates `main.cfg` with mode 0644. After seeding `ark_ServerAdminPassword`, anyone with shell access on the box can read it.

**Why it happens:** Sourced bash configs aren't usually treated as secrets. arkmanager's installer doesn't tighten perms.

**How to avoid:** After seeding, `chmod 0640 /etc/arkmanager/instances/main.cfg && chgrp steam /etc/arkmanager/instances/main.cfg`. Steam user needs read; nobody else does.

**Warning signs:** `stat /etc/arkmanager/instances/main.cfg` shows `0644` after install.

### Pitfall 6: Polkit golden re-capture forgotten → harness goes red

**What goes wrong:** Plan that adds `GAMES["ark"]` doesn't update `tests/golden/40-logpose.rules.v0_2_0`. CI or local pytest run reports `test_polkit_rule_byte_identical_to_v0_2_0_golden` failed.

**Why it happens:** Forgetting that the test asserts byte equality against a fixture computed from `GAMES.values()`.

**How to avoid:** Same atomic commit that adds GAMES["ark"] also re-captures the golden. Plan checklist item: "after editing GAMES, re-render the polkit template via the test's own `template.format(units=units, user='foo')` call and write the bytes back to the golden file."

**Warning signs:** Diff shows GAMES touched but `tests/golden/40-logpose.rules.v0_2_0` untouched.

### Pitfall 7: `arkmanager status` returns success even when server isn't listening

**What goes wrong:** `logpose ark install --start` calls `arkmanager start` then immediately checks `arkmanager status`. Server is loading the world (5–10 minutes per install record), so `Server listening: No` but `Server running: Yes`. Plan author treats that as failure.

**Why it happens:** ARK's first map load is slow; arkmanager differentiates "process running" from "socket listening".

**How to avoid:** Don't gate install success on "listening". Print the status verbatim and warn the user that first map load takes 5–10 minutes (per install record §4.10). E2E test should poll for up to 10 minutes.

**Warning signs:** Install completion prints "ERROR: server not listening" within 30 seconds.

## Code Examples

Verified patterns from the install record + existing logpose codebase:

### Apt source enable + i386 arch (Debian)

```python
# Source: docs/ark-install-reference.md §4.1
def _enable_debian_contrib_nonfree(version_codename: str) -> None:
    """No-op on Ubuntu (uses multiverse instead)."""
    for suffix in ("", "-security", "-updates"):
        _run_command(
            f"sudo sed -i 's|{version_codename}{suffix} main non-free-firmware|"
            f"{version_codename}{suffix} main contrib non-free non-free-firmware|' "
            f"/etc/apt/sources.list",
            check=False,  # idempotent — second run is a no-op
        )
    _run_command("sudo dpkg --add-architecture i386")
    _run_command("sudo apt-get update")
```

### Steam user creation (idempotent)

```python
# Source: docs/ark-install-reference.md §4.4
def _ensure_steam_user() -> None:
    result = subprocess.run(
        ["getent", "passwd", "steam"], capture_output=True, check=False
    )
    if result.returncode != 0:
        _run_command("sudo useradd -m -s /bin/bash steam")
```

### arkmanager install double-call

```python
# Source: docs/ark-install-reference.md §4.9 — the canonical quirk
def _arkmanager_install_validate(branch: str) -> None:
    cmd = f"sudo -u steam /usr/local/bin/arkmanager install --beta={branch} --validate"
    _run_command(cmd, check=False)  # First call: self-update, exits 0 with no payload
    _run_command(cmd)                # Second call: actual download
```

### Sudoers fragment install with visudo validation

```python
# No reference in install record — this is logpose-specific (ARK-18)
def _install_sudoers_fragment(user: str) -> None:
    template = _get_template("logpose-ark.sudoers.template")
    content = template.format(user=user)
    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sudoers") as tf:
        tf.write(content)
        tmppath = tf.name
    # Validate before installing — bad sudoers locks out sudo
    result = subprocess.run(
        ["sudo", "visudo", "-c", "-f", tmppath], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        rich.print(f"sudoers validation failed: {result.stderr}", file=sys.stderr)
        raise typer.Exit(code=1)
    _run_command(f"sudo install -m 0440 -o root -g root {tmppath} /etc/sudoers.d/logpose-ark")
    _run_command(f"rm {tmppath}")
```

## State of the Art

| Old Approach (pre-2026-04-12 plan)              | Current Approach (post-pivot)                                | When Changed     | Impact                                                      |
|-------------------------------------------------|---------------------------------------------------------------|------------------|-------------------------------------------------------------|
| Native steamcmd + custom systemd + GameUserSettings.ini parser | arkmanager wrapper + main.cfg adapter                | 2026-04-12 (pivot) | Eliminates Pitfalls 3, 4, 5, 8 from PITFALLS.md. New surface: sudoers + netinstall. |
| `_fix_steam_sdk` for ARK with sdk32+sdk64+symlink | No SDK fix — arkmanager + apt steamcmd handle it             | 2026-04-12       | Pitfall 2 obsolete.                                         |
| Polkit-only access model                        | Polkit (Palworld + ARK service unit) + sudoers (ARK runtime) | 2026-04-12       | POL-05 split between models; new sudoers fragment template. |

**Deprecated/outdated (do not implement):**
- `_install_game_dependencies` with lib32gcc-s1 / lib32gcc1 fallback (PITFALLS.md Pitfall 1) — install record §4.3 confirms `lib32gcc-s1` works on Debian 13; `lib32gcc1` is no longer needed.
- Setting `LimitNOFILE=100000` on arkserver.service (PITFALLS.md Pitfall 3) — install record §8 explicitly skipped this and the install worked. arkmanager handles it.
- Setting `KillSignal=SIGINT TimeoutStopSec=300` on arkserver.service (PITFALLS.md Pitfall 4) — arkmanager's `stop` does graceful save-and-exit; ExecStop= calls it.
- Native `_ark_parse`/`_ark_save` configparser adapter (research/ARCHITECTURE.md lines 100–117) — replaced by `_arkmanager_parse`/`_arkmanager_save` regex line editor.

## Assumptions Log

| #  | Claim                                                                                                                                            | Section                                | Risk if Wrong                                                                                                       |
|----|--------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| A1 | The `_arkmanager_parse` regex `^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?(.*?)"?\s*$` correctly captures all keys arkmanager uses in `main.cfg`. | Settings Adapter — main.cfg Round-Trip | If a real key has a hyphen or other special character, the regex skips it silently. Mitigation: spot-check via `_arkmanager_parse(Path("/etc/arkmanager/instances/main.cfg"))` against a known-good install during E2E and assert the dict has all 10 seeded keys. |
| A2 | `User=steam` + `ExecStart=/usr/local/bin/arkmanager start` works in the systemd unit (no `sudo` needed inside the unit).                          | arkserver.service Template             | If arkmanager's start command needs root for any reason (e.g., to write to `/var/log/arkmanager/` if that path is root-owned), unit fails. Mitigation: validate during E2E by running `systemctl start arkserver` after `--enable-autostart` install. Fallback: `User=root` + sudo (Pitfall 3 form). |
| A3 | Debian 12 (bookworm) accepts the same `sed` rewrite of `bookworm main non-free-firmware` → `bookworm main contrib non-free non-free-firmware` as Debian 13 (trixie) does for the install record's recipe. | Apt Source Configuration               | If Debian 12's stock sources.list line is structured differently (e.g., split across files in `/etc/apt/sources.list.d/`), the sed is a no-op and apt update doesn't pull i386 libs. Mitigation: in E2E on Debian 12, verify `apt-cache policy lib32gcc-s1` shows a candidate from non-free before install. |
| A4 | The 12-map enum from REQUIREMENTS.md ARK-06 matches arkmanager's recognized set in v1.6.68.                                                       | Map Enum                               | arkmanager rejects an unsupported map at install time; user sees a confusing arkmanager error rather than logpose's enum error. Mitigation: cross-check against arkmanager's `tools/install.sh` map list during plan time, or just defer to arkmanager (pass map through and let arkmanager error out). |
| A5 | `chmod 0640 /etc/arkmanager/instances/main.cfg && chgrp steam` doesn't break arkmanager (steam user still reads it).                              | Install-Time main.cfg Seed             | If arkmanager runs as a different user or expects 0644, behavior breaks. Mitigation: install record §4.7 doesn't tighten perms; preserve current 0644 if E2E shows issues. |
| A6 | The double-call quirk for `arkmanager update` is the same as for `arkmanager install` (both bracket steamcmd self-update).                          | The steamcmd Double-Call Quirk         | If `update` doesn't trigger the same self-update path (e.g., arkmanager caches steamcmd state), the second call is wasted but harmless. Low risk. |
| A7 | Apostrophes in `ark_SessionName` work via standard double-quoted bash assignment (`ark_SessionName="bunty's game"`) without escaping.            | SessionName Quoting                    | If arkmanager re-parses with strict shell quoting in some code path, apostrophes break. Install record §4.10 verified `bunty's game` works on this version. Mitigation: encode as `[VERIFIED: install record]` for apostrophes specifically; reject `"`/`$`/backtick/`\` at CLI boundary. |

## Open Questions

1. **Should `arkserver.service` use `User=steam` + direct ExecStart, or `User=root` + sudo wrapper?**
   - What we know: install record uses `sudo -u steam` from CLI (root context). Both forms work mechanically.
   - What's unclear: whether arkmanager's `start` command writes to any root-owned path during execution.
   - Recommendation: `User=steam` + direct (least privilege). Validate in E2E. If it fails, fall back to `User=root` + sudo before merging.

2. **Should `logpose ark install` re-run be fully idempotent, or refuse if `/home/steam/ARK/ShooterGame/...` exists?**
   - What we know: `_install_arkmanager_if_absent` makes netinstall idempotent. arkmanager's own `install --validate` is idempotent (just re-validates files).
   - What's unclear: whether re-seeding `main.cfg` should overwrite existing values or refuse.
   - Recommendation: Always re-seed (idempotent overwrite of the install-flag-bearing keys; preserves all other keys per `_arkmanager_save`). This is the simplest model and matches what an operator expects from `--map TheCenter` to actually change the map.

3. **How to handle the `--enable-autostart` + Palworld-installed-already case?**
   - What we know: polkit golden re-render covers both unit names; sudoers fragment is ARK-only.
   - What's unclear: nothing — the merged polkit rule is regenerated on every install per POL-03, so installing ARK after Palworld correctly updates the rule to cover both units.
   - Recommendation: No special-casing needed; trust the existing Phase 4 architecture.

4. **Plan split — 4 or 5 atomic commits?**
   - What we know: byte-diff harness must be green at every commit. The polkit golden re-capture and the GAMES["ark"] insertion must be in the same commit.
   - Recommendation: 5 atomic plans — (1) ark template + adapter (no GAMES insertion), (2) GAMES["ark"] + polkit golden re-capture + factory ark branches for verbs only, (3) `_install_ark` helper + ark `install` command, (4) `--enable-autostart` + arkserver.service registration, (5) README per-game firewall + polkit cleanup notes (PKG-08 partial). The planner can collapse to 4 if (4) and (5) are short.

## Environment Availability

> Phase 5 development happens on this box (Debian 13 trixie per env metadata). E2E happens on fresh Debian 12 + Debian 13 VMs.

| Dependency        | Required By                                | Available on dev box | Version    | Fallback                                               |
|-------------------|--------------------------------------------|----------------------|------------|--------------------------------------------------------|
| Python 3.8+       | logpose codebase                           | ✓                    | check `python3 --version` | — |
| typer >=0.9,<0.21 | CLI                                        | ✓ (already installed via pyproject.toml) | per pyproject.toml lock | — |
| rich >=13.0,<14   | Console output                             | ✓                    | per pyproject.toml lock | — |
| pytest            | Byte-diff harness execution                 | ✓ (used in Phase 1–4)| — | Run `python tests/test_palworld_golden.py` directly (script mode supported per Phase 2). |
| git               | Phase 2 v0.1.19 tag check (test 2 in harness) | ✓                | system git | Test self-skips if tag missing per harness lines 64–69. |
| Debian 12 VM      | E2E-03, E2E-04                              | ✗ (need provisioning) | — | Use a containerized Debian 12 with systemd-in-Docker. NOT IDEAL — systemd-in-container can mask real issues. Real VM strongly preferred. |
| Debian 13 VM      | E2E-04                                      | ~ (this box IS Debian 13 but not fresh) | trixie | Provision a fresh trixie VM for clean-slate testing. |
| arkmanager v1.6.68 | E2E only (installed by code under test)   | N/A                  | — | Code installs it; pre-install on VM only if testing repeatedly. |
| 16 GB RAM, 30 GB disk | ARK E2E                                  | unknown on dev box   | — | Required on E2E VM only (see install record §1). |

**Missing dependencies with no fallback for E2E:** Fresh Debian 12 and Debian 13 VMs. The plan should explicitly note that VM provisioning is a prerequisite for the E2E plan and likely a manual user step (gsd-verify-work cannot spin up VMs autonomously).

**Missing dependencies with fallback (dev box):** None — all code-level dependencies present.

## Validation Architecture

> Skipped per `.planning/config.json` `"workflow.nyquist_validation": false`.

## Sources

### Primary (HIGH confidence)
- `/root/personal/palworld-server-launcher/docs/ark-install-reference.md` — working manual install record on Debian 13, 2026-04-12. **Primary source for every ARK command in this phase.**
- `/root/personal/palworld-server-launcher/.planning/REQUIREMENTS.md` — ARK-01..ARK-19 + traceability.
- `/root/personal/palworld-server-launcher/.planning/ROADMAP.md` — Phase 5 success criteria + pivot rationale.
- `/root/personal/palworld-server-launcher/logpose/main.py` — current architecture (Phase 4 complete).
- `/root/personal/palworld-server-launcher/.planning/research/ARCHITECTURE.md` — GameSpec schema + factory pattern (parts now superseded by pivot).
- `/root/personal/palworld-server-launcher/.planning/research/PITFALLS.md` — 12 pitfalls (some obsolete after pivot; see State of the Art).
- `/root/personal/palworld-server-launcher/.planning/research/STACK.md` — original stack research.
- `/root/personal/palworld-server-launcher/.planning/research/FEATURES.md` — competitive analysis vs arkmanager/LinuxGSM.
- `/root/personal/palworld-server-launcher/.planning/phases/04-typer-factory-merged-polkit/04-SUMMARY.md` — Phase 4 handoff.
- `/root/personal/palworld-server-launcher/tests/test_palworld_golden.py` — byte-diff harness (4 tests, must stay 4+ green).
- GitHub API: `api.github.com/repos/arkmanager/ark-server-tools/releases/latest` — verified arkmanager v1.6.68 (2025-12-13) on 2026-04-13.
- `github.com/arkmanager/ark-server-tools/blob/master/tools/install.sh` — verified `cp -n` (no overwrite) + `getent passwd` validation (no user creation) + exit 2 on migration.

### Secondary (MEDIUM confidence)
- `github.com/arkmanager/ark-server-tools/blob/master/tools/instance.cfg.example` — bash key="value" syntax confirmation; "use .ini for special chars" caveat.
- `github.com/arkmanager/ark-server-tools/blob/master/netinstall.sh` — confirms `bash -s <user>` invocation form.

### Tertiary (LOW confidence — needs E2E validation)
- Apostrophe handling in `ark_SessionName` — install record §3 confirms `bunty's game` works, but cross-version stability not verified.
- Debian 12 sed rewrite of `bookworm` sources.list (Assumption A3) — install record only covers Debian 13.
- Map enum exact match against arkmanager v1.6.68 internal list (Assumption A4).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — arkmanager v1.6.68 verified live; recipe in install record verified working; existing Python deps locked.
- Architecture: HIGH — Phase 4 factory + GAMES registry already absorbs ARK with minimal edit; pivot eliminated all schema-fit risk.
- Pitfalls: MEDIUM — most original pitfalls obsolete, but new pitfalls (sudoers validation, double-call, polkit golden) are concrete.
- Settings adapter: MEDIUM — regex pattern A1 needs E2E spot-check.
- Verb delegation: HIGH — install record §7 verifies all verbs work.
- E2E feasibility: MEDIUM — depends on VM provisioning, not code.

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (30 days; arkmanager release cadence is slow — last release 4 months prior).

## RESEARCH COMPLETE
