---
phase: 04-typer-factory-merged-polkit
fixed_at: 2026-04-13T00:00:00Z
review_path: .planning/phases/04-typer-factory-merged-polkit/04-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-04-13
**Source review:** `.planning/phases/04-typer-factory-merged-polkit/04-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (all 2 Warning + all 4 Info)
- Fixed: 6
- Skipped: 0
- Golden harness: 4 passed (byte-diff preserved throughout)

Fixes were applied in order: IN-03 first (Phase-5 blocker per objective), then WR-01, IN-01, WR-02, IN-02, IN-04. Every fix was followed by `pytest tests/test_palworld_golden.py -x` and committed atomically. No rollbacks were required.

## Fixed Issues

### IN-03: Factory silently accepts port/players defaults of 0

**Files modified:** `logpose/main.py`
**Commit:** bd6dc01
**Applied fix:** Replaced `.get("port_default", 0)` / `.get("players_default", 0)` with `["port_default"]` / `["players_default"]` lookups wrapped in `try/except KeyError`, raising `RuntimeError(f"GameSpec for {spec.key!r} missing required install_options key: {e}")` with `from e` chaining. Palworld's spec already sets both keys (8211, 32), so behavior for the existing game is unchanged — the failure mode converts from "silent 0 default" to "loud RuntimeError at module import" for any future GameSpec that omits them. This was the Phase-5 blocker called out in the objective.

### WR-01: `assert` used for runtime template-drift check

**Files modified:** `logpose/main.py`
**Commit:** 1c1761d
**Applied fix:** Replaced the `assert placeholders == {"units", "user"}, ...` in `_setup_polkit` with an explicit `if placeholders != {"units", "user"}: raise RuntimeError(...)`. The check is now always active regardless of `python -O` / `PYTHONOPTIMIZE`. Error message text is identical.

### IN-01: `_setup_polkit` forward-references module-level `GAMES`

**Files modified:** `logpose/main.py`
**Commit:** 3e68d8d
**Applied fix:** Added `Iterable` to the existing `typing` import, changed `_setup_polkit`'s signature from `(user: str)` to `(user: str, specs: Iterable[GameSpec])`, and replaced the body's `GAMES.values()` reference with the parameter `specs`. Updated the single call site inside `_build_game_app.install` to pass `GAMES.values()` explicitly. Helper is no longer coupled to module-global state constructed later in the file.

### WR-02: Shell-injection surface from `echo '...' | sudo tee`

**Files modified:** `logpose/main.py`
**Commit:** c40faf1
**Applied fix:** Added new helper `_write_via_sudo_tee(path, content)` that runs `subprocess.run(["sudo", "tee", str(path)], input=content, text=True, capture_output=True)` — no `shell=True`, content passed via stdin so single quotes / arbitrary bytes can't break the command line. On non-zero exit it emits `rich.print(..., file=sys.stderr)` and `raise typer.Exit(code=1)`. Replaced both interpolated call sites (`_write_service_file` and `_setup_polkit`) to use the new helper. The daemon-reload / polkit-restart follow-up commands still use `_run_command` unchanged.

### IN-02: `console.print(..., file=sys.stderr)` silently wrong

**Files modified:** `logpose/main.py`
**Commit:** 16bc2df
**Applied fix:** Changed both `console.print(..., file=sys.stderr)` calls in `_create_settings_from_default` to `rich.print(..., file=sys.stderr)`. `rich.print` accepts `file=`; `Console.print` does not. This brings the block in line with every other stderr path in the module.

### IN-04: `_version_cb` consistency

**Files modified:** `logpose/main.py`
**Commit:** 3ef4f10
**Applied fix:** Changed `_version_cb(value: bool)` to `_version_cb(value: Optional[bool])` (the callback is invoked with `None` when the flag is absent — `Optional[bool]` is the honest annotation), and swapped `typer.echo(f"logpose {v}")` for `console.print(f"logpose {v}")` to route through the same Console as the rest of the module. `Optional` was already imported.

## Skipped Issues

None — all six in-scope findings were fixed successfully.

## Verification

- `uv run pytest tests/test_palworld_golden.py -x` → `4 passed` after every fix (baseline + 6 post-fix runs).
- `uv run python -c "import logpose.main"` succeeds after the full stack of fixes.
- All byte-diff goldens (`palserver.service.v0_1_19`, `40-logpose.rules.v0_2_0`) remained byte-identical — no template or render-path semantics were touched.
- `_render_service_file` signature and body untouched; `GAMES` dict unchanged; the `add_typer` loop at module scope unchanged.

---

_Fixed: 2026-04-13_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
