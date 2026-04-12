---
phase: 03-introduce-gamespec-games-dict-palworld-only
plan: 03
type: execute
wave: 3
depends_on: ["03-introduce-gamespec-games-dict-palworld-only/02"]
files_modified:
  - logpose/main.py
autonomous: true
requirements: [PAL-08]
tags: [refactor, post-install-hooks, palworld, python]

must_haves:
  truths:
    - "install() no longer calls _fix_steam_sdk directly — it iterates spec.post_install_hooks instead."
    - "_palworld_sdk_hook is the only invoker of _fix_steam_sdk on the Palworld install path."
    - "Hardcoded grep of the Palworld SDK paths (sdk64, steamclient.so) returns zero hits inside any @app.command() body; all such paths are bound through _palworld_sdk_hook + the _PAL_STEAM_CLIENT_SO / _PAL_SDK64_DST module-private helpers added in Plan 03-01."
    - "pytest tests/test_palworld_golden.py -x exits 0 (3 tests) — byte-diff exit gate."
    - "PAL-08 closed: _fix_steam_sdk wired as a Palworld-only post_install_hook."
  artifacts:
    - path: "logpose/main.py"
      provides: "install() iterates spec.post_install_hooks; no direct _fix_steam_sdk call"
      contains: "for hook in spec.post_install_hooks"
  key_links:
    - from: "install() Typer command"
      to: "_palworld_sdk_hook"
      via: "iteration over GAMES['palworld'].post_install_hooks"
      pattern: "for hook in spec\\.post_install_hooks:\\s*\\n\\s+hook\\(\\)"
    - from: "_palworld_sdk_hook"
      to: "_fix_steam_sdk"
      via: "closure calling _fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)"
      pattern: "_fix_steam_sdk\\(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO\\)"
---

<objective>
Remove the direct `_fix_steam_sdk(...)` invocation from `install()` and replace it with an iteration over `spec.post_install_hooks`. Palworld's hook list (populated in Plan 03-01 with `[_palworld_sdk_hook]`) becomes the sole driver of Palworld's steam SDK fix. This is the third and final atomic commit of Phase 3 and closes PAL-08.

Purpose: PAL-08 requires `_fix_steam_sdk` to be expressed as a Palworld-only `post_install_hook` rather than a direct call. Plan 03-01 registered the hook; Plan 03-02 kept the direct call in place to isolate this change. Plan 03-03 flips the switch: the direct call is removed and the hook list becomes the only path.

Output: A single atomic commit that (a) deletes the `_fix_steam_sdk(Path.home() / ".steam/sdk64", STEAM_DIR / "steamapps/common/...")` block inside `install()`, (b) replaces it with `for hook in spec.post_install_hooks: hook()`, and (c) keeps the byte-diff harness green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/research/ARCHITECTURE.md
@.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-RESEARCH.md
@.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-01-SUMMARY.md
@.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-02-SUMMARY.md
@logpose/main.py
@tests/test_palworld_golden.py

<interfaces>
<!-- Target install() body (after Plan 03-03). Extracted from 03-RESEARCH.md Example 3. -->

## Refactored install() (final Phase 3 shape)

```python
@app.command()
def install(
    port: int = typer.Option(8211, help="Port to run the server on."),
    players: int = typer.Option(32, help="Maximum number of players."),
    start: bool = typer.Option(
        False, "--start", help="Start the server immediately after installation."
    ),
) -> None:
    """Install the Palworld dedicated server and create a systemd service."""
    if Path.home() == Path("/root"):
        rich.print("This script should not be run as root. Exiting.", file=sys.stderr)
        sys.exit(1)

    spec = GAMES["palworld"]

    _install_steamcmd()
    _run_steamcmd_update(spec.server_dir, spec.app_id)
    for hook in spec.post_install_hooks:
        hook()
    service_content = _render_service_file(
        service_name=spec.service_name,
        template_name=spec.service_template_name,
        user=Path.home().name,
        working_directory=spec.server_dir,
        exec_start_path=spec.server_dir / spec.binary_rel_path,
        port=port,
        players=players,
    )
    _write_service_file(Path(f"/etc/systemd/system/{spec.service_name}.service"), service_content)
    _setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)

    console.print("Installation complete!")

    if start:
        console.print("Starting the server...")
        _run_command(f"systemctl start {spec.service_name}")
        console.print("Server started successfully!")
    else:
        console.print(
            "You can now start the server with: palworld-server-launcher start"
        )

    console.print(
        "To enable the server to start on boot, run: palworld-server-launcher enable"
    )
```

## Delta from Plan 03-02's install() body

**Remove** (4 lines):
```python
    _fix_steam_sdk(
        Path.home() / ".steam/sdk64",
        STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so",
    )
```

**Insert** (2 lines) at the same location (between `_run_steamcmd_update(...)` and `_render_service_file(...)`):
```python
    for hook in spec.post_install_hooks:
        hook()
```

That is the ENTIRE change for this plan. Everything else in `install()` — the `/root` guard, `_install_steamcmd()`, the `_render_service_file` call, the `_write_service_file` call, the `_setup_polkit` call, the `if start:` block — stays byte-identical to Plan 03-02's output.

## Behavioral equivalence proof

- **Plan 03-02's install() calls:** `_install_steamcmd()` → `_run_steamcmd_update(spec.server_dir, spec.app_id)` → `_fix_steam_sdk(Path.home() / ".steam/sdk64", STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so")` → `_render_service_file(...)`.
- **Plan 03-03's install() calls:** `_install_steamcmd()` → `_run_steamcmd_update(spec.server_dir, spec.app_id)` → `hook()` (where `hook` is `_palworld_sdk_hook` from `spec.post_install_hooks`) → `_render_service_file(...)`.
- **`_palworld_sdk_hook` body** (from Plan 03-01):
  ```python
  def _palworld_sdk_hook() -> None:
      _fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)
  ```
- **`_PAL_SDK64_DST` equals** `Path.home() / ".steam/sdk64"` (Plan 03-01 binding).
- **`_PAL_STEAM_CLIENT_SO` equals** `STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"` (Plan 03-01 binding).

Therefore the two call chains produce identical `_fix_steam_sdk(...)` invocations. No observable behavioral drift. `install()`'s side effects are byte-identical pre/post Plan 03-03.

## What does NOT change in this plan

- `_palworld_sdk_hook`, `_PAL_SDK64_DST`, `_PAL_STEAM_CLIENT_SO` — all added by Plan 03-01 already; unchanged.
- `GAMES["palworld"].post_install_hooks = [_palworld_sdk_hook]` — set by Plan 03-01; unchanged.
- `_fix_steam_sdk` function body — unchanged.
- `_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)` — still uses literal strings (Phase 4 target).
- All other `@app.command()` bodies (`update`, `edit_settings`, `start`, `stop`, `restart`, `status`, `enable`, `disable`) — unchanged from Plan 03-02.
- `palserver.service.template` — untouched (byte-diff harness fires if touched).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace _fix_steam_sdk direct call with post_install_hooks iteration in install()</name>
  <files>logpose/main.py</files>
  <action>
Locate the `install()` body in `logpose/main.py`. After Plan 03-02, the first few lines after the `/root` guard look like:

```python
    spec = GAMES["palworld"]

    _install_steamcmd()
    _run_steamcmd_update(spec.server_dir, spec.app_id)
    _fix_steam_sdk(
        Path.home() / ".steam/sdk64",
        STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so",
    )
    service_content = _render_service_file(
        ...
    )
```

Replace the 4-line `_fix_steam_sdk(...)` block with a 2-line hook-iteration loop:

```python
    spec = GAMES["palworld"]

    _install_steamcmd()
    _run_steamcmd_update(spec.server_dir, spec.app_id)
    for hook in spec.post_install_hooks:
        hook()
    service_content = _render_service_file(
        ...
    )
```

That is the only edit in this plan. Do NOT:
- Rename, delete, or modify `_fix_steam_sdk`, `_palworld_sdk_hook`, `_PAL_SDK64_DST`, `_PAL_STEAM_CLIENT_SO`, or any field of `GAMES["palworld"]`.
- Touch any other Typer command body.
- Touch `palserver.service.template`, `palserver.rules.template`, or any file under `tests/`.

**WHY iterate over `spec.post_install_hooks` rather than call `_palworld_sdk_hook()` directly**: Direct call would leak Palworld-specific naming into a command body that is meant to be game-agnostic-via-spec. The iteration form mirrors the Phase 4/5 factory pattern — the same loop body works unchanged for ARK's `GAMES["ark"]` (whose `post_install_hooks` will be `[]` per ARK-12 since arkmanager handles SDK setup).

**WHY NOT make `_fix_steam_sdk` read `spec.steam_sdk_paths` and put `_fix_steam_sdk` itself in the hook list**: Would require changing `_fix_steam_sdk`'s signature from `(steam_sdk_dst: Path, steam_client_so: Path) -> None` to something like `(paths: list[tuple[Path, Path]]) -> None`. That is a separate refactor with its own byte-diff risk (the function body changes). `03-RESEARCH.md` Pattern 2 explicitly recommends the zero-arg closure approach used here: keep `_fix_steam_sdk` signature unchanged, let the closure adapt.

**Sanity grep after edit:**
```bash
grep -nE '_fix_steam_sdk' logpose/main.py
```

Expected hits:
- `def _fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path)` — the function definition itself (~line 146).
- `_fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)` inside `_palworld_sdk_hook` body — the closure.

Expected NON-hits:
- ANY call with `Path.home() / ".steam/sdk64"` as a literal first argument (this is what Plan 03-02 left behind and Plan 03-03 removes).

If the grep shows a literal-path call surviving inside `install()` or any other command body, the edit was incomplete — fix before running tests.
  </action>
  <verify>
    <automated>cd /root/personal/palworld-server-launcher && .venv/bin/python -c "import ast, re; src = open('logpose/main.py').read(); tree = ast.parse(src); install_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'install'); install_src = ast.unparse(install_fn); assert 'for hook in spec.post_install_hooks' in install_src, 'install() does not iterate post_install_hooks'; assert '_fix_steam_sdk' not in install_src, f'install() still directly references _fix_steam_sdk: {install_src}'; direct_calls = re.findall(r'_fix_steam_sdk\(Path\.home\(\)', src); assert not direct_calls, f'literal-path _fix_steam_sdk call still present: {direct_calls}'; print('OK: install() iterates post_install_hooks; no direct _fix_steam_sdk call remains.')"</automated>
  </verify>
  <done>
- `install()` body contains `for hook in spec.post_install_hooks: hook()` between `_run_steamcmd_update(...)` and `_render_service_file(...)`.
- `install()` body contains zero direct `_fix_steam_sdk(...)` calls.
- No literal-path `_fix_steam_sdk(Path.home() / ".steam/sdk64", ...)` invocation remains anywhere in `logpose/main.py`.
- `_fix_steam_sdk` is still called exactly once at runtime — inside `_palworld_sdk_hook` — and its function definition is untouched.
- All other Typer command bodies are byte-identical to Plan 03-02's output.
  </done>
</task>

<task type="auto">
  <name>Task 2: Byte-diff exit gate + final Phase 3 audit + commit</name>
  <files>logpose/main.py</files>
  <action>
Run the byte-diff regression harness:

```bash
cd /root/personal/palworld-server-launcher
.venv/bin/python -m pytest tests/test_palworld_golden.py -x
```

Expected: `3 passed`, exit 0.

```bash
cd /root/personal/palworld-server-launcher
.venv/bin/python tests/test_palworld_golden.py
```

Expected: `OK: palserver.service matches v0.1.19 golden (template + real render path)`, exit 0.

[BLOCKING] If either fails, STOP. The hook loop replaces only the `_fix_steam_sdk` call — `_render_service_file` and its arguments are unchanged — so byte-diff failure here would be extremely surprising. Likely causes:
- A typo in the hook loop accidentally altered a different line.
- The insertion overwrote/indented the following `service_content = _render_service_file(...)` block incorrectly.

Inspect `git diff HEAD -- logpose/main.py` and revert any non-intended change.

**Full Phase 3 audit** (now that all three plans have landed):

Run each grep below and confirm the expected count. These are the locked exit criteria for Phase 3:

```bash
cd /root/personal/palworld-server-launcher

# Criterion #2: no PAL_* module-level constants remain.
grep -nE '^(PAL_SERVER_DIR|PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH)\b' logpose/main.py
# Expected: zero lines.

# Criterion #3: no hardcoded palserver/PalWorld/2394010 in helper bodies.
# Permitted locations: inside GAMES construction; inside _setup_polkit literals (Phase 4 target).
grep -cE '\b2394010\b' logpose/main.py
# Expected: 1

grep -cE '"palserver\.service\.template"' logpose/main.py
# Expected: 1 (inside service_template_name field of GAMES)

# Criterion #4: PAL-08 closed — _fix_steam_sdk wired as hook.
grep -cE 'for hook in spec\.post_install_hooks' logpose/main.py
# Expected: 1 (inside install())

# Criterion #5: byte-diff harness green.
.venv/bin/python -m pytest tests/test_palworld_golden.py -x
# Expected: 3 passed, exit 0.

# GameSpec has 15 fields (the 14 named in ROADMAP Phase 3 Success Criterion #1).
.venv/bin/python -c "from logpose.main import GameSpec; import dataclasses; print(len(dataclasses.fields(GameSpec)))"
# Expected: 15
```

If all audits pass, commit the final Phase 3 atomic change:

```bash
cd /root/personal/palworld-server-launcher
git add logpose/main.py
git commit -m "$(cat <<'EOF'
refactor(03-03): wire _fix_steam_sdk as Palworld post_install_hook

Removes the direct _fix_steam_sdk(Path.home() / ".steam/sdk64", STEAM_DIR /
".../steamclient.so") call from install() and replaces it with a two-line
iteration over spec.post_install_hooks. Palworld's hook list (registered as
[_palworld_sdk_hook] in Plan 03-01) is now the sole driver of the steam SDK
fix.

Behavioral equivalence: _palworld_sdk_hook is a zero-arg closure that calls
_fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO) with the exact same Path
values the direct call used. No observable drift.

Closes PAL-08. With Plans 03-01 (ARCH-01/02/03) and 03-02 (ARCH-04, PAL-05),
this commit completes Phase 3 — GAMES["palworld"] is the single source of
truth for Palworld configuration, and _fix_steam_sdk is declaratively
Palworld-only via the hook registry.

pytest tests/test_palworld_golden.py -x: 3 passed (byte-diff exit gate green).
EOF
)"
```

After committing, do one final sanity check with `git log --oneline -5` to confirm three consecutive atomic commits (`refactor(03-01)`, `refactor(03-02)`, `refactor(03-03)`) landed in order.
  </action>
  <verify>
    <automated>cd /root/personal/palworld-server-launcher && .venv/bin/python -m pytest tests/test_palworld_golden.py -x && .venv/bin/python tests/test_palworld_golden.py && ! grep -nE '^(PAL_SERVER_DIR|PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH)\b' logpose/main.py && test "$(grep -cE '\b2394010\b' logpose/main.py)" -eq 1 && test "$(grep -cE 'for hook in spec\.post_install_hooks' logpose/main.py)" -eq 1 && test "$(.venv/bin/python -c 'from logpose.main import GameSpec; import dataclasses; print(len(dataclasses.fields(GameSpec)))')" -eq 15 && git log -1 --pretty=%s | grep -qE '^refactor\(03-03\)' && git log --oneline -3 | grep -qE 'refactor\(03-01\)' && echo "OK: Phase 3 complete — all success criteria closed, byte-diff green."</automated>
  </verify>
  <done>
- `pytest tests/test_palworld_golden.py -x` exits 0 with 3 tests passing.
- `python tests/test_palworld_golden.py` exits 0.
- Zero `PAL_SERVER_DIR` / `PAL_SETTINGS_PATH` / `DEFAULT_PAL_SETTINGS_PATH` module-level assignments.
- Exactly one `2394010` literal and one `for hook in spec.post_install_hooks` iteration in `logpose/main.py`.
- `GameSpec` has exactly 15 fields.
- A single commit lands with subject `refactor(03-03): wire _fix_steam_sdk as Palworld post_install_hook`.
- The last three commits on `main` are `refactor(03-01)`, `refactor(03-02)`, `refactor(03-03)` in order.
- PAL-08 closed. Phase 3 complete.
  </done>
</task>

</tasks>

<verification>
Phase 3 end-of-plan closure audit (must all be TRUE after Task 2 commits):

1. **ARCH-01**: `GameSpec` is a frozen dataclass with the 14 named fields from ROADMAP Phase 3 Success Criterion #1 (15 dataclass fields total — the ROADMAP enumeration lists 15 names).
2. **ARCH-02**: `SettingsAdapter` is a frozen dataclass with `parse` + `save` callable fields.
3. **ARCH-03**: `GAMES: dict[str, GameSpec]` is module-scope in `logpose/main.py` with one entry `"palworld"`.
4. **ARCH-04**: No `PAL_*` module globals; every game-aware helper reads from `GAMES["palworld"]` (verified: `grep -nE '^(PAL_SERVER_DIR|PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH)\b' logpose/main.py` returns zero lines; `2394010` and section-rename tuple appear exactly once each inside `GAMES` construction).
5. **PAL-05**: `edit_settings()` reads `spec.settings_section_rename` (verified: `grep -cE '\[/Script/Pal\.PalWorldSettings\]' logpose/main.py` returns 1, all inside GAMES).
6. **PAL-08**: `_fix_steam_sdk` is wired as a Palworld-only `post_install_hook` via `_palworld_sdk_hook` closure; `install()` iterates `spec.post_install_hooks`; no direct call remains.
7. **Byte-diff exit gate**: `pytest tests/test_palworld_golden.py -x` exits 0 with 3 tests passing after each of the three Phase 3 commits.
8. **Invariants preserved**: `palserver.service.template` byte-identical (PAL-02); `palserver.service` render byte-identical (PAL-09 half); Palworld regex/saver bodies unchanged (PAL-03, PAL-04); `_run_command`, `_install_steamcmd`, `_repair_package_manager` signatures unchanged (ARCH-06); no `BaseGame` class, no `core/` split (ARCH-05); `logpose/main.py` is still the single implementation file per `logpose/CLAUDE.md`.
</verification>

<success_criteria>
Plan complete when:
- [ ] `install()` iterates `spec.post_install_hooks` instead of calling `_fix_steam_sdk` directly.
- [ ] No literal-path `_fix_steam_sdk(Path.home() / ".steam/sdk64", …)` call remains in `logpose/main.py`.
- [ ] `_fix_steam_sdk` is referenced in exactly two places: its own `def` and inside `_palworld_sdk_hook`.
- [ ] `pytest tests/test_palworld_golden.py -x` exits 0 with 3 tests passing.
- [ ] One atomic commit with subject `refactor(03-03): wire _fix_steam_sdk as Palworld post_install_hook` landed on `main`.
- [ ] All Phase 3 success criteria (ARCH-01, ARCH-02, ARCH-03, ARCH-04, PAL-05, PAL-08; continuous invariants ARCH-05, ARCH-06, PAL-01, PAL-02, PAL-06) are satisfied.
</success_criteria>

<output>
After completion, create `.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-03-SUMMARY.md` per the template. Record:
- Commit SHA.
- Confirm PAL-08 closed.
- Byte-diff harness result (expected: 3 passed).
- Final Phase 3 audit: all six phase-owned requirements (ARCH-01, ARCH-02, ARCH-03, ARCH-04, PAL-05, PAL-08) closed.
- Handoff note for Phase 4: `_setup_polkit("40-palserver.rules", "palserver.rules.template", ...)` literal strings survive — Phase 4's merged polkit rule work targets them.
</output>
