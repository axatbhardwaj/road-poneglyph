---
phase: 03-introduce-gamespec-games-dict-palworld-only
plan: 02
type: execute
wave: 2
depends_on: ["03-introduce-gamespec-games-dict-palworld-only/01"]
files_modified:
  - logpose/main.py
autonomous: true
requirements: [ARCH-04, PAL-05]
tags: [refactor, dissolve-globals, call-sites, python, palworld]

must_haves:
  truths:
    - "No PAL_*-prefixed module-level constants remain in logpose/main.py (PAL_SERVER_DIR, PAL_SETTINGS_PATH, DEFAULT_PAL_SETTINGS_PATH are removed)."
    - "Every @app.command() body and every game-aware helper reads Palworld values exclusively from GAMES['palworld'] — no literal '2394010', no literal '\"palserver\"' (except the GAMES['palworld'] construction block and the /etc/systemd/system path), no inline section-rename tuple outside GAMES."
    - "_install_palworld thin wrapper is deleted (its sole caller install() now calls _run_steamcmd_update(spec.server_dir, spec.app_id) directly)."
    - "Palworld's settings-section-rename tuple is read from spec.settings_section_rename in edit_settings — PAL-05 closed."
    - "pytest tests/test_palworld_golden.py -x exits 0 (3 tests) — byte-diff exit gate."
    - "Grep sanity: `grep -nE 'PAL_SERVER_DIR|PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH|_install_palworld' logpose/main.py` returns zero hits after the plan lands."
  artifacts:
    - path: "logpose/main.py"
      provides: "Dissolved PAL_* module globals; install/update/edit_settings read from GAMES['palworld']"
      min_lines: 300
    - path: "logpose/main.py"
      provides: "_install_palworld wrapper removed; install() calls _run_steamcmd_update directly"
      contains: "spec = GAMES\\[\"palworld\"\\]"
  key_links:
    - from: "install() command body"
      to: "GAMES['palworld']"
      via: "spec = GAMES['palworld'] at top of function"
      pattern: "spec = GAMES\\[.palworld.\\]"
    - from: "edit_settings() section-rename"
      to: "spec.settings_section_rename"
      via: "argument to _create_settings_from_default"
      pattern: "spec\\.settings_section_rename"
    - from: "update() steamcmd call"
      to: "spec.server_dir + spec.app_id"
      via: "_run_steamcmd_update(spec.server_dir, spec.app_id)"
      pattern: "_run_steamcmd_update\\(spec\\.server_dir, spec\\.app_id\\)"
    - from: "systemctl verbs (start/stop/restart/status/enable/disable)"
      to: "spec.service_name"
      via: "f-string in _run_command call"
      pattern: "systemctl \\w+ \\{spec\\.service_name\\}"
---

<objective>
Dissolve the three Palworld-specific module globals (`PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`) and the `_install_palworld` thin wrapper. Rewire every Typer command body and every inline Palworld literal to read from `GAMES["palworld"]` (added by Plan 03-01). This closes ARCH-04 (no hardcoded palworld values in helper/command bodies) and PAL-05 (section-rename expressed via `GameSpec.settings_section_rename`).

Purpose: Finish the "single source of truth" migration the research recommends as commit 2/3. Once this plan lands, grepping for `PAL_SERVER_DIR` / `PAL_SETTINGS_PATH` / `DEFAULT_PAL_SETTINGS_PATH` / `_install_palworld` / the raw `2394010` literal / the inline section-rename tuple in `logpose/main.py` must return zero hits.

Output: A single atomic commit that deletes ~4 lines (the three PAL_* globals + the `_install_palworld` wrapper), rewrites ~8 call sites inside `install()`, `update()`, `edit_settings()`, `start()`, `stop()`, `restart()`, `status()`, `enable()`, `disable()`, and leaves the byte-diff harness green.
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
@logpose/main.py
@tests/test_palworld_golden.py

<interfaces>
<!-- Target call-site shapes. Extracted verbatim from 03-RESEARCH.md Examples 3 and 4. -->

## Refactored install() (after Plan 03-02)

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
    _fix_steam_sdk(
        Path.home() / ".steam/sdk64",
        STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so",
    )
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
    _setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)  # Phase 4 merges

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

**Note:** The `_fix_steam_sdk` call stays as a direct invocation in this plan. Plan 03-03 replaces it with the `for hook in spec.post_install_hooks: hook()` loop. Keeping it direct here is intentional — it isolates Plan 03-03's PAL-08 change as its own verifiable commit.

## Refactored update()

```python
@app.command()
def update() -> None:
    """Update the Palworld dedicated server."""
    spec = GAMES["palworld"]
    console.print("Updating Palworld dedicated server...")
    _run_steamcmd_update(spec.server_dir, spec.app_id)
    console.print("Update complete! Restart the server for the changes to take effect.")
```

## Refactored edit_settings() (PAL-05 closure)

```python
@app.command(name="edit-settings")
def edit_settings() -> None:
    """Edit the PalWorldSettings.ini file."""
    spec = GAMES["palworld"]
    try:
        settings = spec.settings_adapter.parse(spec.settings_path)
    except (FileNotFoundError, ValueError):
        _create_settings_from_default(
            spec.default_settings_path,
            spec.settings_path,
            spec.settings_section_rename,
        )
        try:
            settings = spec.settings_adapter.parse(spec.settings_path)
        except (ValueError, FileNotFoundError) as e:
            rich.print(
                f"An error occurred after creating default settings: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        _interactive_edit_loop(settings)
        spec.settings_adapter.save(spec.settings_path, settings)
    except Exception as e:
        rich.print(f"An error occurred during settings edit: {e}", file=sys.stderr)
        sys.exit(1)
```

Note `spec.default_settings_path` is typed `Optional[Path]`; Palworld's spec populates it with a real Path so `_create_settings_from_default` receives a non-None value as v0.1.19 did.

## Refactored start/stop/restart/status/enable/disable

Every short systemctl-delegating command dissolves `"palserver"` literals into `spec.service_name`:

```python
@app.command()
def start() -> None:
    """Start the Palworld server."""
    spec = GAMES["palworld"]
    _run_command(f"systemctl start {spec.service_name}")


@app.command()
def stop() -> None:
    """Stop the Palworld server."""
    spec = GAMES["palworld"]
    _run_command(f"systemctl stop {spec.service_name}")


@app.command()
def restart() -> None:
    """Restart the Palworld server."""
    spec = GAMES["palworld"]
    _run_command(f"systemctl restart {spec.service_name}")


@app.command()
def status() -> None:
    """Check the status of the Palworld server."""
    spec = GAMES["palworld"]
    _run_command(f"systemctl status {spec.service_name}", check=False)


@app.command()
def enable() -> None:
    """Enable the Palworld server to start on boot."""
    spec = GAMES["palworld"]
    _run_command(f"systemctl enable {spec.service_name}")


@app.command()
def disable() -> None:
    """Disable the Palworld server from starting on boot."""
    spec = GAMES["palworld"]
    _run_command(f"systemctl disable {spec.service_name}")
```

## Deletions

1. Lines 20–22 of current `logpose/main.py`:
   ```python
   PAL_SERVER_DIR = STEAM_DIR / "steamapps/common/PalServer"
   PAL_SETTINGS_PATH = PAL_SERVER_DIR / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini"
   DEFAULT_PAL_SETTINGS_PATH = PAL_SERVER_DIR / "DefaultPalWorldSettings.ini"
   ```
   All three deleted entirely.

2. Lines 140–143 of current `logpose/main.py`:
   ```python
   def _install_palworld(server_dir: Path, app_id: int) -> None:
       """Install Palworld dedicated server using steamcmd."""
       console.print("Installing Palworld dedicated server...")
       _run_steamcmd_update(server_dir, app_id)
   ```
   Entire function deleted. Its sole caller (`install()` line 324) now calls `_run_steamcmd_update(spec.server_dir, spec.app_id)` directly — see refactored `install()` above.

## Preserved verbatim (byte-diff invariants)

- `STEAM_DIR = Path.home() / ".steam/steam"` — logpose/main.py:19. Still module-scope; still referenced by `_PAL_STEAM_CLIENT_SO` in the Plan 03-01 block and by `install()`'s direct `_fix_steam_sdk` call.
- `_palworld_parse`, `_palworld_save` bodies — unchanged. Only their call sites move (`edit_settings()` now calls `spec.settings_adapter.parse(spec.settings_path)` instead of `_palworld_parse(PAL_SETTINGS_PATH)`).
- `_fix_steam_sdk` body — unchanged (signature unchanged since Phase 2). Still called directly from `install()` in this plan; Plan 03-03 routes it through `post_install_hooks`.
- `_setup_polkit("40-palserver.rules", "palserver.rules.template", ...)` — literal strings stay in this plan. Phase 4 merges them into `40-logpose.rules`.
- `palserver.service.template` — must stay byte-identical. Test #3 of the harness fires if the render drifts.
- The service file path `Path(f"/etc/systemd/system/{spec.service_name}.service")` renders to `/etc/systemd/system/palserver.service` — byte-identical to the current hardcoded `Path("/etc/systemd/system/palserver.service")`.

## What Phase 2 already did (do NOT redo)

Per Plan 02-03 and 02-04 summaries, the helpers `_run_steamcmd_update`, `_create_service_file` (now `_render_service_file`), `_fix_steam_sdk`, `_setup_polkit`, `_create_settings_from_default` all already accept parameters — they do NOT read any module-level Palworld constant. This plan only switches the CALLERS (Typer commands) from reading `PAL_*` globals to reading `GAMES["palworld"]` fields. Helper signatures are invariant.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Dissolve PAL_* module globals + delete _install_palworld wrapper</name>
  <files>logpose/main.py</files>
  <action>
Two structural deletions in `logpose/main.py`:

1. **Delete the three PAL_* module globals** (currently lines 20–22):
   ```python
   PAL_SERVER_DIR = STEAM_DIR / "steamapps/common/PalServer"
   PAL_SETTINGS_PATH = PAL_SERVER_DIR / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini"
   DEFAULT_PAL_SETTINGS_PATH = PAL_SERVER_DIR / "DefaultPalWorldSettings.ini"
   ```

   Leave `STEAM_DIR = Path.home() / ".steam/steam"` (line 19) UNTOUCHED — it is game-agnostic (both games share `~/.steam/steam`) per Assumption A5 in `03-RESEARCH.md`, and the `_PAL_*` block added in Plan 03-01 references it.

2. **Delete `_install_palworld`** (currently lines 140–143):
   ```python
   def _install_palworld(server_dir: Path, app_id: int) -> None:
       """Install Palworld dedicated server using steamcmd."""
       console.print("Installing Palworld dedicated server...")
       _run_steamcmd_update(server_dir, app_id)
   ```

   Its single caller (`install()` line 324) will be updated in Task 2 to call `_run_steamcmd_update(spec.server_dir, spec.app_id)` directly. This removes one Palworld-named symbol from the module per `03-RESEARCH.md` Open Question #2 recommendation.

**Verify no caller was missed:** Before running the next task, run
```bash
grep -nE 'PAL_SERVER_DIR|PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH|_install_palworld' logpose/main.py
```

Expected hits AFTER this task:
- Inside `install()`, `update()`, `edit_settings()` Typer commands — these are the references that Task 2 will rewrite. Expected: 4–6 hits.

If hits include any line OUTSIDE the Typer command bodies (e.g., inside a helper function), STOP — Phase 2 was supposed to have eliminated those. Do not invent new parameters; investigate the unexpected caller before proceeding.

**Do not run tests yet.** The file will temporarily have broken references inside the Typer commands; Task 2 fixes them before the harness is run.
  </action>
  <verify>
    <automated>cd /root/personal/palworld-server-launcher && ! grep -nE '^PAL_SERVER_DIR|^PAL_SETTINGS_PATH|^DEFAULT_PAL_SETTINGS_PATH' logpose/main.py && ! grep -nE 'def _install_palworld\(' logpose/main.py && echo "OK: PAL_* globals + _install_palworld removed at module scope."</automated>
  </verify>
  <done>
- `PAL_SERVER_DIR = …`, `PAL_SETTINGS_PATH = …`, `DEFAULT_PAL_SETTINGS_PATH = …` no longer appear as module-level assignments.
- `def _install_palworld(...)` no longer appears in the file.
- `STEAM_DIR = Path.home() / ".steam/steam"` remains at line 19.
- The file is expected to have stale references inside Typer commands; those are fixed in Task 2.
  </done>
</task>

<task type="auto">
  <name>Task 2: Rewire Typer command bodies to read from GAMES["palworld"]</name>
  <files>logpose/main.py</files>
  <action>
Rewrite nine `@app.command()` bodies in `logpose/main.py` to read every Palworld value from `GAMES["palworld"]`. Use the refactored bodies from the `<interfaces>` block above VERBATIM (copy-paste, adjust only if a local style convention differs from the research — e.g., string quote style).

1. **`install()`** (current lines ~310–354): Bind `spec = GAMES["palworld"]` after the `/root` guard. Replace:
   - `_install_palworld(PAL_SERVER_DIR, 2394010)` → `_run_steamcmd_update(spec.server_dir, spec.app_id)`
   - `_render_service_file(service_name="palserver", template_name="palserver.service.template", working_directory=PAL_SERVER_DIR, exec_start_path=PAL_SERVER_DIR / "PalServer.sh", …)` → `_render_service_file(service_name=spec.service_name, template_name=spec.service_template_name, working_directory=spec.server_dir, exec_start_path=spec.server_dir / spec.binary_rel_path, …)`
   - `_write_service_file(Path("/etc/systemd/system/palserver.service"), service_content)` → `_write_service_file(Path(f"/etc/systemd/system/{spec.service_name}.service"), service_content)`
   - `_run_command("systemctl start palserver")` → `_run_command(f"systemctl start {spec.service_name}")`
   - **KEEP** the `_fix_steam_sdk(Path.home() / ".steam/sdk64", STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so")` call as a direct invocation — Plan 03-03 routes it through `post_install_hooks`.
   - **KEEP** the `_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)` line with the literal strings — Phase 4 merges the polkit rule.

2. **`update()`** (current lines ~393–398): Add `spec = GAMES["palworld"]`, replace `_run_steamcmd_update(PAL_SERVER_DIR, 2394010)` with `_run_steamcmd_update(spec.server_dir, spec.app_id)`.

3. **`edit_settings()`** (current lines ~401–429): Add `spec = GAMES["palworld"]` as the first line in the body. Replace:
   - `_palworld_parse(PAL_SETTINGS_PATH)` (both occurrences — initial + post-creation retry) → `spec.settings_adapter.parse(spec.settings_path)`
   - `_create_settings_from_default(DEFAULT_PAL_SETTINGS_PATH, PAL_SETTINGS_PATH, (<inline tuple>))` → `_create_settings_from_default(spec.default_settings_path, spec.settings_path, spec.settings_section_rename)` — **PAL-05 closure**.
   - `_palworld_save(PAL_SETTINGS_PATH, settings)` → `spec.settings_adapter.save(spec.settings_path, settings)`.

4. **`start()`**, **`stop()`**, **`restart()`**, **`status()`**, **`enable()`**, **`disable()`** (current lines 357–390): Replace the literal `"palserver"` in each `_run_command(...)` with `{spec.service_name}` inside an f-string, bound from `spec = GAMES["palworld"]` at the top of each function body. See refactored commands in the `<interfaces>` block.

**Sanity grep after all edits:**
```bash
grep -nE 'PAL_SERVER_DIR|PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH|_install_palworld|"palserver"|2394010' logpose/main.py
```

Expected hits AFTER Task 2:
- Inside the `GAMES["palworld"]` construction block only: one `app_id=2394010`, one `service_name="palserver"`, one `service_template_name="palserver.service.template"`, zero hits for `PAL_SERVER_DIR`/`PAL_SETTINGS_PATH`/`DEFAULT_PAL_SETTINGS_PATH`/`_install_palworld`.
- Inside `_setup_polkit("40-palserver.rules", "palserver.rules.template", …)` call in `install()`: the literal `"palserver.rules.template"` and `"40-palserver.rules"` are allowed in this plan (Phase 4 merges these).

If any literal `"palserver"` appears in a `_run_command("systemctl …")` call OUTSIDE the GAMES construction, the refactor is incomplete — fix before running tests.

**WHY NOT remove `service_name` / `service_template_name` strings from the GAMES construction**: They must exist as field values somewhere. The `GAMES["palworld"]` literal is the canonical location per ARCH-03 — this is where the strings are supposed to live.

**WHY NOT pre-compute `f"{spec.service_name}.service"` inside `GameSpec`**: Adds a derived field that duplicates data. Caller's f-string is cheap and explicit; research Pitfall 4 recommends `service_name = "palserver"` (no suffix) and caller constructs the filename.
  </action>
  <verify>
    <automated>cd /root/personal/palworld-server-launcher && .venv/bin/python -c "import ast, re; src = open('logpose/main.py').read(); tree = ast.parse(src); commands = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in {'install','update','edit_settings','start','stop','restart','status','enable','disable'}]; assert len(commands) == 9, f'expected 9 commands, got {len(commands)}'; [print(f'OK {c.name}') for c in commands]; bad = re.findall(r'\b(PAL_SERVER_DIR|PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH|_install_palworld)\b', src); assert not bad, f'stale references: {bad}'; import logpose.main as m; assert m.GAMES['palworld'].service_name == 'palserver'; print('OK: nine commands rewired, no PAL_* / _install_palworld references, GAMES intact.')"</automated>
  </verify>
  <done>
- Every `@app.command()` function body (install, update, edit_settings, start, stop, restart, status, enable, disable) binds `spec = GAMES["palworld"]` and references Palworld values exclusively via `spec.<field>` — EXCEPT the surviving `_setup_polkit("40-palserver.rules", "palserver.rules.template", …)` literals (Phase 4 merges) and the direct `_fix_steam_sdk` call (Plan 03-03 routes via hooks).
- No `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`, `_install_palworld` references anywhere in the file.
- The literal `2394010` appears exactly once (inside `GAMES["palworld"]` construction), never inside a command body.
- The literal `"palserver"` appears only inside the `GAMES["palworld"]` construction (as `service_name="palserver"`) and in the `_setup_polkit` call (Phase 4 target). It does NOT appear inside any `_run_command(f"systemctl …")` string.
- PAL-05 closed: `spec.settings_section_rename` is the only place the section-rename tuple is read; no inline tuple at `edit_settings` call site.
  </done>
</task>

<task type="auto">
  <name>Task 3: Byte-diff exit gate + grep invariants + commit</name>
  <files>logpose/main.py</files>
  <action>
Run the full regression harness:

```bash
cd /root/personal/palworld-server-launcher
.venv/bin/python -m pytest tests/test_palworld_golden.py -x
```

Expected: `3 passed in ~0.05s`, exit code 0.

```bash
cd /root/personal/palworld-server-launcher
.venv/bin/python tests/test_palworld_golden.py
```

Expected: `OK: palserver.service matches v0.1.19 golden (template + real render path)`, exit 0.

[BLOCKING] If `test_render_service_file_byte_identical_to_golden` (test #3) fails, the `install()` call to `_render_service_file` drifted — the most likely cause is a typo in one of the `spec.<field>` substitutions that changed the argument values. Check in order:
1. `service_name=spec.service_name` — must resolve to `"palserver"` (no `.service` suffix).
2. `template_name=spec.service_template_name` — must resolve to `"palserver.service.template"`.
3. `working_directory=spec.server_dir` — must resolve to `STEAM_DIR / "steamapps/common/PalServer"` (same path as the deleted `PAL_SERVER_DIR` global).
4. `exec_start_path=spec.server_dir / spec.binary_rel_path` — must resolve to `.../PalServer/PalServer.sh`.
5. `user=Path.home().name`, `port=port`, `players=players` — unchanged from v0.1.19.

If test #3 still fails after verifying all five, diff against `main~1` and the golden fixture.

**Grep invariant audit** (PAL-05 + ARCH-04 closure verification):

```bash
cd /root/personal/palworld-server-launcher
# Must return ZERO hits — all Palworld-prefixed globals and the _install_palworld wrapper are dissolved.
grep -nE '^PAL_SERVER_DIR|^PAL_SETTINGS_PATH|^DEFAULT_PAL_SETTINGS_PATH|def _install_palworld\b' logpose/main.py

# Must return exactly ONE hit (inside GAMES construction) — raw app_id literal.
grep -cE '\b2394010\b' logpose/main.py

# Must return exactly ONE hit (inside GAMES construction) for the section-rename OLD header.
grep -cE '\[/Script/Pal\.PalWorldSettings\]' logpose/main.py
```

Expected results:
- First grep: 0 lines.
- Second grep: `1` (only in `app_id=2394010` inside `GAMES["palworld"]`).
- Third grep: `1` (only inside `settings_section_rename=(...)` tuple in `GAMES["palworld"]`).

If the third grep returns 2 or more, the section-rename tuple was not dissolved from `edit_settings` — fix before committing.

**Commit** (atomic, per research 3-commit recommendation):

```bash
cd /root/personal/palworld-server-launcher
git add logpose/main.py
git commit -m "$(cat <<'EOF'
refactor(03-02): dissolve PAL_* globals, rewire commands to read GAMES["palworld"]

Removes PAL_SERVER_DIR, PAL_SETTINGS_PATH, DEFAULT_PAL_SETTINGS_PATH module
globals and the _install_palworld thin wrapper. Every Typer command now binds
spec = GAMES["palworld"] and reads Palworld values exclusively via spec.<field>
— the registry added in Plan 03-01 becomes load-bearing.

Closes ARCH-04 (no Palworld-specific module globals; helpers and commands read
from GAMES) and PAL-05 (section-rename tuple is expressed via
GameSpec.settings_section_rename; edit_settings() reads spec.settings_section_rename).

_fix_steam_sdk is still called directly from install() in this commit; Plan
03-03 routes it through GAMES["palworld"].post_install_hooks to close PAL-08.
_setup_polkit still uses literal "40-palserver.rules" / "palserver.rules.template"
strings; Phase 4 merges them into 40-logpose.rules.

pytest tests/test_palworld_golden.py -x: 3 passed (byte-diff exit gate green).
EOF
)"
```
  </action>
  <verify>
    <automated>cd /root/personal/palworld-server-launcher && .venv/bin/python -m pytest tests/test_palworld_golden.py -x && .venv/bin/python tests/test_palworld_golden.py && test "$(grep -cE '\b2394010\b' logpose/main.py)" -eq 1 && test "$(grep -cE 'PalWorldSettings\]' logpose/main.py)" -eq 1 && ! grep -nE '^PAL_SERVER_DIR|^PAL_SETTINGS_PATH|^DEFAULT_PAL_SETTINGS_PATH|def _install_palworld\b' logpose/main.py && git log -1 --pretty=%s | grep -qE '^refactor\(03-02\)' && echo "OK: dissolution complete + byte-diff green + commit landed."</automated>
  </verify>
  <done>
- `pytest tests/test_palworld_golden.py -x` exits 0 with 3 tests passing.
- `python tests/test_palworld_golden.py` exits 0.
- Zero module-scope `PAL_SERVER_DIR` / `PAL_SETTINGS_PATH` / `DEFAULT_PAL_SETTINGS_PATH` / `_install_palworld` references in `logpose/main.py`.
- Exactly one `2394010` literal and one `[/Script/Pal.PalWorldSettings]` literal, both inside `GAMES["palworld"]`.
- A single commit lands with subject `refactor(03-02): dissolve PAL_* globals, rewire commands to read GAMES["palworld"]`.
- All nine Typer command bodies bind `spec = GAMES["palworld"]` and read Palworld values from `spec.<field>`.
- ARCH-04 closed. PAL-05 closed.
  </done>
</task>

</tasks>

<verification>
Overall plan checks (all must pass before Task 3 commit):

1. `grep -nE '^PAL_SERVER_DIR|^PAL_SETTINGS_PATH|^DEFAULT_PAL_SETTINGS_PATH|def _install_palworld\b' logpose/main.py` returns zero hits.
2. `grep -cE '\b2394010\b' logpose/main.py` returns exactly 1 (inside GAMES construction).
3. `grep -cE '\[/Script/Pal\.PalWorldSettings\]' logpose/main.py` returns exactly 1 (inside GAMES construction).
4. Every `@app.command()` body in `install`, `update`, `edit_settings`, `start`, `stop`, `restart`, `status`, `enable`, `disable` binds `spec = GAMES["palworld"]` and references Palworld values via `spec.<field>`.
5. `_setup_polkit("40-palserver.rules", "palserver.rules.template", …)` literals survive unchanged in `install()` — these are Phase 4's target.
6. `_fix_steam_sdk` is still called directly (not via hook) in `install()` — this is Plan 03-03's target.
7. `pytest tests/test_palworld_golden.py -x` exits 0 with 3 tests passing.
8. `python -c "import logpose.main"` exits 0.
9. A single commit landed with subject `refactor(03-02): …`.
</verification>

<success_criteria>
Plan complete when:
- [ ] `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` module globals are removed.
- [ ] `_install_palworld` wrapper is removed.
- [ ] Every Typer command body binds `spec = GAMES["palworld"]` once and reads Palworld values exclusively through `spec.<field>`.
- [ ] `edit_settings()` passes `spec.settings_section_rename` to `_create_settings_from_default` (no inline tuple) — PAL-05 closed.
- [ ] `update()` calls `_run_steamcmd_update(spec.server_dir, spec.app_id)` directly (no wrapper) — no game-specific constants.
- [ ] Grep invariants hold: 0 hits for dissolved globals; exactly 1 hit for `2394010` and `[/Script/Pal.PalWorldSettings]`, both inside GAMES construction.
- [ ] Byte-diff harness green (3 tests passing).
- [ ] One atomic commit with subject `refactor(03-02): dissolve PAL_* globals, rewire commands to read GAMES["palworld"]`.
</success_criteria>

<output>
After completion, create `.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-02-SUMMARY.md` per the template. Record:
- Commit SHA.
- Confirm ARCH-04 and PAL-05 closed.
- Grep audit results (zero stale references; single-hit for `2394010` and section-rename).
- Byte-diff harness result (expected: 3 passed).
- Handoff note for Plan 03-03: `_fix_steam_sdk` still called directly inside `install()`; Plan 03-03 routes it through `post_install_hooks` to close PAL-08.
</output>
