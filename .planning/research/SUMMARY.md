# Project Research Summary — logpose v0.2.0

**Project:** logpose (formerly palworld-server-launcher v0.1.19)
**Domain:** Multi-game dedicated server launcher CLI (Palworld + ARK: Survival Evolved) on Debian/Ubuntu
**Researched:** 2026-04-12
**Mode:** Subsequent milestone — in-place rename + generalize + add ARK
**Overall confidence:** HIGH

## TL;DR

The v0.2.0 shape is settled: a frozen `GameSpec` dataclass + `GAMES` registry, a Typer factory that composes per-game sub-apps via `add_typer`, flat `templates/`, and a single merged `40-logpose.rules` polkit file — all inside `main.py`, no `core/` split. The four critical corrections to PROJECT.md are: **PyPI name must be `logpose-launcher` (not `logpose`)**, **ARK RCON default is `27020` (not 32330)**, **`configparser` needs a specific constructor to survive ARK's INI dialect**, and **Python 3.8 support is latent-broken** (`typer>=0.21` dropped 3.8) — pin `typer>=0.9,<0.21` + `rich<14` or bump to 3.10. The top risks (silent ARK startup failures from missing 32-bit libs / sdk32 steamclient / low `LimitNOFILE`, save corruption on hard kill, Palworld behavioral regressions from the refactor) all have concrete mitigations mapped to specific phases.

## Key Decisions (Locked)

### Architecture
- **`GameSpec` frozen dataclass + `GAMES: dict[str, GameSpec]` registry.** Not a class hierarchy — a typed struct. Stdlib `dataclasses` only.
- **`SettingsAdapter` dataclass with two callables** (`parse`, `save`) per game — no `BaseAdapter` class.
- **Typer factory `_build_game_app(spec) -> typer.Typer`** called in a loop over `GAMES`, registered via `app.add_typer(sub, name=key)`. Factory pattern is mandatory — naked decorator-in-loop captures loop variables incorrectly.
- **Flat `templates/`** — `palserver.service.template` (unchanged), `arkserver.service.template` (new), `40-logpose.rules.template` (new, merged).
- **Single merged polkit rule file** `40-logpose.rules` listing all known game service units via JS `indexOf` array. Old v0.1.19 `40-palserver.rules` coexists additively. Phase 4 exit criteria includes fallback to two-file if the template proves brittle under `str.format()`.
- **Everything in `logpose/main.py`** (no `core/`, no `games/` submodules).

### Stack
- **Python 3.8+ retained** via pinned deps: `typer>=0.9,<0.21`, `rich>=13.0,<14`. No new runtime dependencies.
- **Stdlib `configparser`** for ARK INI. Comment-preservation loss acceptable (ARK's default INI is comment-free).
- **PyPI distribution name: `logpose-launcher`** (`logpose` taken by unrelated ML lib). CLI entry point + import name stay `logpose`.
- **ARK: Survival Evolved only** (app id `376030`). ASA out of scope.
- **ARK apt deps** (Debian 12 / Ubuntu 22.04+): `lib32gcc-s1 libc6-i386 libncurses5 libncursesw5 libsdl2-2.0-0 lib32stdc++6` with `lib32gcc1` fallback. Gate per-game — NOT installed for Palworld.

### CLI Shape
- **Game-first nesting:** `logpose palworld <verb>`, `logpose ark <verb>`.
- **ARK install flags:** `--map`, `--port`, `--query-port`, `--rcon-port`, `--players`, `--session-name`, `--admin-password` (required, prompted hidden), `--password`, `--no-battleye`, `--start`.
- **ARK `edit-settings`** uses Palworld's existing Rich-table + prompt-by-name UX on `[ServerSettings]`.
- **Install-time seed** `GameUserSettings.ini` so `edit-settings` works pre-first-launch.

## Corrections to PROJECT.md (must propagate into REQUIREMENTS.md)

1. **ARK RCON default port is `27020`, not `32330`** (PROJECT.md has this wrong).
2. **PyPI name `logpose` is taken.** Use **`logpose-launcher`** as distribution name.
3. **ARK apt packages** unmentioned: `lib32gcc-s1 libc6-i386 libncurses5 libncursesw5 libsdl2-2.0-0 lib32stdc++6`; per-game gated.
4. **`steamclient.so` needs both `sdk32` AND `sdk64`** for ARK plus a symlink into `Engine/Binaries/ThirdParty/SteamCMD/Linux`. Existing `_fix_steam_sdk()` only handles sdk64.
5. **ARK systemd unit extras:** `LimitNOFILE=100000`, `KillSignal=SIGINT`, `TimeoutStopSec=300`. Palworld unit stays byte-identical.
6. **`configparser` constructor is non-default:**
   ```python
   cp = configparser.RawConfigParser(
       strict=False, interpolation=None, allow_no_value=True,
       delimiters=("=",), comment_prefixes=(";", "#"),
   )
   cp.optionxform = str
   ```
7. **Python 3.8 floor is latent-broken.** `typer>=0.21` dropped 3.8 on 2025-12-25. Pin `typer>=0.9,<0.21` + `rich>=13.0,<14`, or bump `requires-python = ">=3.10"`.
8. **`palworld_server_launcher.egg-info/PKG-INFO` is tracked in git** and will corrupt `logpose-launcher` wheel build. `git rm -r` + add `*.egg-info/`, `build/`, `dist/` to `.gitignore` before any refactor commit.
9. **`from __future__ import annotations` required** on every module using PEP-585 generics (`dict[str, str]`). Current `main.py` works by accident on 3.8 (Typer lazy inspection).
10. **SessionName must NOT go on ARK command line** — only in `[SessionSettings]` of `GameUserSettings.ini`. Enforce 63-char soft warning.

## Critical Risks (Top 10)

| # | Risk | Mitigation | Phase |
|---|------|-----------|-------|
| 1 | Palworld regression from GAMES refactor (module-global leak, template placeholder drift) | **Byte-diff harness** against v0.1.19-rendered fixture (`user=foo,port=8211,players=32`). Zero diff = exit criteria. Kill all `PAL_*` globals. Every helper takes `game: str` positional required. | 2–3 |
| 2 | ARK startup fails silently — missing 32-bit libs | `_install_game_dependencies(game_key)`; try `lib32gcc-s1`, fallback `lib32gcc1` via `apt-cache show`. Per-game `apt_packages`. | 5 |
| 3 | ARK runs but never advertises — `steamclient.so` missing in `sdk32` | Generalize `_fix_steam_sdk(game)`; ARK copies to both sdk32 + sdk64 + Engine ThirdParty. Data-drive via `GAMES['ark'].steam_sdk_paths`. | 5 |
| 4 | ARK stuck loading world — `LimitNOFILE` too low | `LimitNOFILE=100000` in `arkserver.service.template` only; Palworld output byte-identical. | 5 |
| 5 | Save corruption on `systemctl stop` | `KillSignal=SIGINT`, `TimeoutStopSec=300`, `Type=exec`, direct-binary `ExecStart` (no shell wrapper). No RCON-dependent `ExecStop=`. | 5 |
| 6 | `configparser` blowup on ARK INI (interpolation / duplicates / case-folding) | `RawConfigParser(strict=False, interpolation=None, allow_no_value=True, delimiters=("=",))` + `cp.optionxform = str`. Write with `space_around_delimiters=False`. | 5 |
| 7 | Typer nested subcommands — wrong exit codes, missing help | `no_args_is_help=True` on root + sub-apps; `help=` on both `Typer()` + `add_typer()`; global flags via `@app.callback()`; `sys.exit(1)` → `raise typer.Exit(1)`. Smoke-test matrix in exit criteria. | 4 |
| 8 | Merged polkit rule — template typo breaks BOTH games | JS brace-doubling audit; old `40-palserver.rules` untouched on disk (additive); manual `pkcheck` verification per game unit in exit criteria. Fallback to two-file if brittle. | 4 |
| 9 | Stale `palworld_server_launcher.egg-info/` corrupts wheel build | `git rm -r` + `.gitignore` in Phase 1. Pre-release: `rm -rf build/ dist/ *.egg-info/` → `python -m build` → verify `Name: logpose-launcher` in METADATA. TestPyPI dry-run. | 1 + 6 |
| 10 | RCON silently off — INI vs launch-arg mismatch | Install writes triad aligned: `RCONEnabled=True`, `RCONPort=<port>`, `ServerAdminPassword=<token_urlsafe(16) if blank>`. `?RCONEnabled=True?RCONPort=<port>` in launch args. Print password once. `status` reads INI. | 5 |

Lower-tier pitfalls (port collisions, SessionName mangling, firewall docs) addressed inside Phase 5 install-flow validation and Phase 6 release polish.

## Recommended Phase Breakdown (6 phases)

Ordered so Palworld remains a working oracle at every boundary.

### Phase 1 — Rename + Hygiene
**Delivers:** `git mv palworld_server_launcher logpose`; `pyproject.toml` (`name="logpose-launcher"`, script `logpose = "logpose.main:app"`, `packages=["logpose"]`, pinned deps); delete `*.egg-info/` + `.gitignore` entries; `from __future__ import annotations` on every module; README new-install note.
**Addresses:** Corrections 2, 7, 8, 9.
**Research flag:** No.

### Phase 2 — Parameterize Helpers (no GAMES dict yet)
**Delivers:** Helpers accept dict/paths parameters; `_palworld_parse` / `_palworld_save` wrappers around existing regex (byte-identical); **byte-diff test script** as exit criteria.
**Addresses:** Risk 1 (regression harness).
**Research flag:** No.

### Phase 3 — Introduce GameSpec + GAMES dict (Palworld only)
**Delivers:** `GameSpec` + `SettingsAdapter` dataclasses; all `PAL_*` globals folded into `GAMES["palworld"]`; every helper takes `game: str` positional required; byte-diff still zero.
**Addresses:** Risk 1 (no global leaks).
**Research flag:** No.

### Phase 4 — Typer Factory + Merged Polkit
**Delivers:** `_build_game_app(spec)` factory + `add_typer` loop; `no_args_is_help=True`, `help=` everywhere; `sys.exit` → `typer.Exit`; `@app.callback()` with `--version` (via `importlib.metadata.version("logpose-launcher")`); `40-logpose.rules.template` JS array (Palworld only for now); CLI smoke-test matrix; `pkcheck` verification; README updated with game-first CLI.
**Addresses:** Risks 7, 8.
**Research flag:** Low.

### Phase 5 — Add ARK Entry + E2E
**Delivers:** `GAMES["ark"] = GameSpec(app_id=376030,...)`; `arkserver.service.template` (with `LimitNOFILE=100000`, `KillSignal=SIGINT`, `TimeoutStopSec=300`, direct-exec); `_ark_parse`/`_ark_save` (`RawConfigParser` incantation); ARK install flow (all 10 flags, SessionName to INI only, RCON triad aligned, install-time seed INI); map enum validation (12 maps; `Gen2` not `Genesis2`); port collision probe via `ss`; `--admin-password` required + generated default via `secrets.token_urlsafe(16)`; merged polkit regenerated with both units; **E2E verification** on fresh Debian 12 VM.
**Addresses:** Risks 2, 3, 4, 5, 6, 10; Corrections 1, 3, 4, 5, 6, 10.
**Research flag:** **HIGH** — recommend `/gsd-research-phase` during planning for exact 32-bit apt package names per target distro, current-year ARK signal handling, BattlEye default state, `[SessionSettings]` vs `[ServerSettings]` key placement.

### Phase 6 — Release Polish + PyPI
**Delivers:** Clean build (`rm -rf build dist *.egg-info`); wheel metadata verification (`Name: logpose-launcher`, `Version: 0.2.0`); TestPyPI dry-run + throwaway-venv install; production PyPI publish (Trusted Publishing recommended); README final pass (migration note, per-game firewall ports, manual polkit uninstall).
**Addresses:** Risk 9; Correction 2.
**Research flag:** No.

### Phase Ordering Rationale
- **Rename first** so every later diff is against new paths.
- **Parameterize before GAMES** proves the shape before the dict is locked.
- **GAMES dict before Typer factory** so the factory has something to iterate over.
- **Typer factory + polkit merge together** — both change rendered outputs and share smoke-test harness.
- **ARK last among implementation phases** — 6 of 10 top risks concentrate here; coarse phase with strong E2E exit criteria beats spreading risk.
- **Release polish after ARK** — distribution concerns depend on completed behavior.

## Research Flags Summary

| Phase | Needs `/gsd-research-phase`? | Reason |
|-------|------------------------------|--------|
| 1 Rename | No | Mechanical. |
| 2 Parameterize | No | Byte-diff test is the only novelty; spec'd here. |
| 3 GAMES dict | No | Schema fully specified in ARCHITECTURE.md. |
| 4 Typer factory + polkit merge | Low | Brief verify-on-Debian-12 of polkit JS merge. |
| **5 ARK entry** | **HIGH** | Deep risk concentration; recommend dedicated research. |
| 6 Release | No | Standard PyPI publishing. |

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | ARK deps cross-verified; PyPI name checked live; Typer version band verified against release notes. |
| Features | HIGH | Launch args, ports, INI keys cross-verified (ark.wiki.gg, ark-survival.net, arkmanager source). |
| Architecture | HIGH | Grounded in existing code; minimum-diff. Factory pattern verified against fastapi/typer source. |
| Pitfalls | HIGH for deps/paths/configparser/LimitNOFILE/polkit. MEDIUM for SIGINT/SIGTERM specifics. LOW correctly identified and rejected for unsubstantiated 25-char SessionName claim. |

## Open Questions

Only items genuinely requiring user input:

1. **Python 3.8 floor (pin deps) or bump to 3.10?** — Recommendation: pin + keep 3.8. Default to recommendation if no answer.
2. **Polkit: merged (locked) vs two-file?** — Locked merged per architecture; Phase 4 exit criteria flags fallback to two-file if brittle.

All other decisions are settled.

---

*Research completed: 2026-04-12. Ready for roadmap.*
