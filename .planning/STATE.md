# STATE: logpose v0.2.0

*Project memory — updated at phase transitions and session boundaries.*

## Project Reference

**Project:** logpose (multi-game dedicated server launcher CLI; evolves from `palworld-server-launcher` v0.1.19 in place)
**Active Milestone:** v0.2.0 — logpose rewrite (rename + generalize + add ARK: Survival Evolved)
**Core Value:** One CLI, many games, zero sudo prompts — operators type `logpose <game> <command>` and get a working, autostart-capable dedicated server on a fresh Debian/Ubuntu box.
**Distribution name on PyPI:** `logpose-launcher` (CLI + import name stay `logpose`).
**Granularity:** coarse (6 phases)
**Current Focus:** Phase 2 — Parameterize Helpers (Phase 1 complete)

## Current Position

**Phase:** 2 — Parameterize Helpers (no GAMES dict yet)
**Plan:** TBD
**Status:** Ready to plan
**Progress:** `[███░░░░░░░░░░░░░░░░░] 17% (1/6 phases complete)`

**Next action:** `/gsd-plan-phase 2` (or `/gsd-autonomous` to resume).

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 1 / 6 |
| Phases complete | 1 / 6 |
| Plans complete | 1 |
| Requirements shipped | 6 / 56 (PKG-01..PKG-06) |
| Byte-diff harness green | — (lands in Phase 2) |

## Quick Tasks Completed

| Date | Task | Outcome |
|------|------|---------|
| _(none yet)_ | | |

## Phase Completion

| Phase | Name | Status | Completed | Notes |
|-------|------|--------|-----------|-------|
| 1 | Rename + Hygiene | ✅ Complete | 2026-04-12 | 4 atomic commits (7257387, 10add52, 643e1c6, a6c2b3c). Palworld behavior byte-identical per invariant check. |
| 2 | Parameterize Helpers (no GAMES dict yet) | Pending | — | Lands byte-diff regression harness; Palworld stays working oracle. |
| 3 | Introduce GameSpec + GAMES dict (Palworld only) | Pending | — | Dissolves `PAL_*` module globals into `GAMES["palworld"]`. |
| 4 | Typer Factory + Merged Polkit | Pending | — | Game-first CLI + merged `40-logpose.rules`. Low-priority research flag. |
| 5 | Add ARK Entry + E2E | Pending | — | **HIGH research priority** — six of ten top risks concentrate here. |
| 6 | Release Polish + PyPI | Pending | — | `logpose-launcher` v0.2.0 to PyPI; v0.1.19 left frozen. |

## Accumulated Context

### Decisions Locked (from PROJECT.md + research/SUMMARY.md)

- In-place rename (not new repo) — minimum diff, git-rename preserves history.
- `GameSpec` frozen dataclass + `GAMES: dict[str, GameSpec]` registry — no `BaseGame`, no `core/` split.
- `SettingsAdapter` dataclass with `parse` + `save` callables per game.
- Typer factory `_build_game_app(spec) -> typer.Typer` + `add_typer` loop (factory pattern is mandatory — naked decorator-in-loop misbinds).
- Game-first nested CLI: `logpose <game> <verb>`.
- PyPI distribution name: `logpose-launcher` (unqualified `logpose` is taken). CLI entry point + Python import name stay `logpose`.
- Python 3.8+ floor retained via pinned deps: `typer>=0.9,<0.21`, `rich>=13.0,<14`.
- ARK: Survival Evolved only (app id `376030`); ASA out of scope.
- ARK RCON default port: `27020` (PROJECT.md originally had `32330` — corrected).
- ARK SessionName written to `[SessionSettings]` only, never to launch args.
- `_repair_package_manager()` stays load-bearing and untouched.

### Todos Emitted

*(none yet — populated at phase-transition boundaries)*

### Blockers

*(none)*

### Known Open Questions

These are the two open items from `research/SUMMARY.md`. Both have recommended defaults — `/gsd-autonomous` will proceed with the defaults unless the user overrides.

1. **Python 3.8 floor: pin deps or bump to 3.10?**
   - **Default (recommended):** Pin `typer>=0.9,<0.21` + `rich>=13.0,<14` and keep `requires-python = ">=3.8"`. This preserves the v0.1.19 audience.
   - Revisit trigger: if a phase discovers a feature that genuinely needs Python 3.10+ syntax or typing, raise the floor in a focused Phase 6 sub-task.

2. **Polkit: merged single file or two-file split?**
   - **Default (locked):** Single merged `40-logpose.rules` covering all known game service units via JS `indexOf` array, regenerated on every install. Old v0.1.19 `40-palserver.rules` is left on disk additively; Polkit merges across files.
   - Fallback (documented in Phase 4 exit criteria): if the merged template proves brittle under `str.format()` JS brace escaping during Phase 4 verification, fall back to one polkit rule file per game (`40-palserver.rules` + `40-arkserver.rules`).

## Session Continuity

**Last session:** 2026-04-12 — project initialization. PROJECT.md, REQUIREMENTS.md, research pack (STACK/FEATURES/ARCHITECTURE/PITFALLS/SUMMARY), ROADMAP.md, STATE.md all written. 56 v1 requirements mapped across 6 phases with zero orphans.

**Resume instructions:**
- Run `/gsd-autonomous` to execute all remaining phases hands-off (auto-approve / yolo mode is set in `config.json`).
- Or run `/gsd-plan-phase 1` to plan Phase 1 explicitly before executing.
- Phase 5 planner should invoke `/gsd-research-phase` — research flag is HIGH.

**Key files to re-load at session start:**
- `.planning/PROJECT.md` — core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — 56 v1 requirements + traceability
- `.planning/ROADMAP.md` — 6 phases with goals and success criteria
- `.planning/research/SUMMARY.md` — locked decisions, corrections, top-10 risks
- `.planning/research/ARCHITECTURE.md` — `GameSpec` schema, factory pattern
- `.planning/research/PITFALLS.md` — Phase 5 risk detail
- `CLAUDE.md` — project-specific execution rules (keep `_repair_package_manager`, minimum-diff, no `BaseGame`)

---
*State initialized: 2026-04-12*
*Last updated: 2026-04-12 after roadmap creation*
