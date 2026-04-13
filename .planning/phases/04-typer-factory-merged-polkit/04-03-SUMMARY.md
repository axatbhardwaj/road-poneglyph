---
phase: 04-typer-factory-merged-polkit
plan: 03
subsystem: polkit
tags: [polkit, template, golden, games-driven]
requires:
  - Plan 04-02 game-first CLI
  - GAMES registry (Phase 3)
provides:
  - Merged 40-logpose.rules template driven by GAMES.values()
  - Single-arg _setup_polkit(user)
  - Fourth byte-diff golden test
affects:
  - logpose/main.py
  - logpose/templates/*
  - tests/*
tech-stack:
  added:
    - string.Formatter (placeholder audit)
  patterns:
    - JS `var units = [...]; units.indexOf(...)` merged polkit rule
key-files:
  created:
    - logpose/templates/40-logpose.rules.template
    - tests/golden/40-logpose.rules.v0_2_0
  modified:
    - logpose/main.py
    - logpose/templates/CLAUDE.md
    - tests/test_palworld_golden.py
  deleted:
    - logpose/templates/palserver.rules.template
decisions:
  - Placeholder audit via string.Formatter uses assert (programmer-error tripwire).
  - Old on-disk /etc/polkit-1/rules.d/40-palserver.rules NOT deleted by code (POL-04 additive posture).
  - Golden fixture uses user='foo' matching existing palserver fixture.
metrics:
  duration_minutes: 5
  completed_at: 2026-04-13
commit: a3e6a87
---

# Phase 04 Plan 03: Merge Polkit to 40-logpose.rules + Golden Test Summary

Replaced per-game `palserver.rules.template` with a merged `40-logpose.rules.template` using a JS `units = [...]; indexOf(...)` pattern driven by `GAMES.values()`. `_setup_polkit()` is now single-arg (`user`) and reads the unit list globally. Added a fourth byte-diff test locking the template render against the committed golden (`tests/golden/40-logpose.rules.v0_2_0`).

## Requirements closed

- **POL-01** — single merged rule file `40-logpose.rules`.
- **POL-02** — JS units/indexOf pattern with escaped braces for `str.format()`; placeholder audit via `string.Formatter().parse`.
- **POL-03** — `_setup_polkit(user: str)` reads `GAMES.values()` globally.
- **POL-04** — additive-code posture: old on-disk `40-palserver.rules` left in place by code.
- **POL-05** (static half) — rendered byte-for-byte matches golden; `pkcheck` VM verification deferred to Phase 5 E2E.

## Final `_setup_polkit` signature + body outline

```python
def _setup_polkit(user: str) -> None:
    """Allow `user` to control every registered game service without sudo."""
    console.print(...)
    policy_file = Path("/etc/polkit-1/rules.d/40-logpose.rules")
    _run_command(f"sudo mkdir -p {policy_file.parent}")
    units = ", ".join(f'"{spec.service_name}.service"' for spec in GAMES.values())
    template = _get_template("40-logpose.rules.template")
    placeholders = {f[1] for f in Formatter().parse(template) if f[1]}
    assert placeholders == {"units", "user"}, ...
    policy_content = template.format(units=units, user=user)
    _run_command(f"echo '{policy_content}' | sudo tee {policy_file}")
    _run_command("sudo systemctl restart polkit.service")
```

## Template placeholder inventory

- `{units}` — comma-separated pre-quoted JS strings (`"palserver.service"`), built from `GAMES.values()`.
- `{user}` — installing user (typically `Path.home().name`).
- All literal JS braces doubled for `str.format()` (template source has `{{` / `}}`; rendered has `{` / `}`).

## Golden fixture provenance

- **File:** `tests/golden/40-logpose.rules.v0_2_0` (253 bytes, trailing `\n`).
- **Source:** rendered from current template via `template.format(units='"palserver.service"', user='foo')`.
- **Fixture:** Palworld-only `GAMES` registry; `user='foo'` (matches existing palserver test fixture).
- **Balanced braces:** yes (open/close match).
- **No `{{`/`}}` leakage:** verified — raw rendered output has no doubled braces.

## Byte-diff harness count

- Previously: 3 tests (palserver.service template, v0.1.19 tag paranoia, real `_render_service_file` call path).
- Now: 4 tests — added `test_polkit_rule_byte_identical_to_v0_2_0_golden`.
- Script mode (`python tests/test_palworld_golden.py`) updated with matching invocation + error handling.

## Deviations from Plan

### Minor: git rename detection

**Plan expectation** (Task 4 `git diff` audit): separate `A\tlogpose/templates/40-logpose.rules.template` and `D\tlogpose/templates/palserver.rules.template` status lines.

**Actual**: git automatically detected the file rename (68% similarity) and reported a single `R` status line. This is semantically identical to the plan's intent — old deleted, new added — just represented differently.

**Fix attempted**: None — the plan's underlying intent (add new, remove old) is satisfied. The verify heuristic was over-specific for git's rename detection behavior.

**Rule applied**: None (cosmetic verification-script mismatch, not a behavior change).

## Handoff to Plan 04-04

- 4 `sys.exit` sites remaining in `logpose/main.py`: `_get_template`, `_run_command`, `_create_settings_from_default`, `_interactive_edit_loop` quit path.
- Grep audits needed: `sys.exit`=0, `@app.command`=0, `@app.callback`=1, `_build_game_app`=1, `app.add_typer`=1, `palserver.rules.template|40-palserver.rules`=0.
- README.md still shows v0.1.19 `palworld-server-launcher <verb>` invocations; Plan 04-04 updates to `logpose palworld <verb>`.

## Self-Check: PASSED

- `logpose/templates/40-logpose.rules.template` exists.
- `logpose/templates/palserver.rules.template` removed.
- `tests/golden/40-logpose.rules.v0_2_0` exists.
- Commit `a3e6a87` touches the expected file set (via rename detection).
- Byte-diff harness 4/4 green.
