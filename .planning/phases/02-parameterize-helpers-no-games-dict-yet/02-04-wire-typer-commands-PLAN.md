---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 04
type: execute
wave: 3
depends_on:
  - "02-parameterize-helpers-no-games-dict-yet/02"
  - "02-parameterize-helpers-no-games-dict-yet/03"
files_modified:
  - logpose/main.py
autonomous: true
requirements: [ARCH-04, SET-01, PAL-08, SET-04]
tags: [typer, wiring, palworld, python]

must_haves:
  truths:
    - "`install` command calls the new helper signatures with Palworld values threaded from module-scope constants: `_install_palworld(PAL_SERVER_DIR, 2394010)`, `_fix_steam_sdk(Path.home() / '.steam/sdk64', STEAM_DIR / 'steamapps/common/Steamworks SDK Redist/linux64/steamclient.so')`, `_write_service_file(Path('/etc/systemd/system/palserver.service'), _render_service_file(...))`, `_setup_polkit('40-palserver.rules', 'palserver.rules.template', Path.home().name)`."
    - "`update` command calls `_run_steamcmd_update(PAL_SERVER_DIR, 2394010)` — the sole non-install call site."
    - "`edit_settings` command's `_create_settings_from_default()` call becomes `_create_settings_from_default(DEFAULT_PAL_SETTINGS_PATH, PAL_SETTINGS_PATH, ('[/Script/Pal.PalWorldSettings]', '[/Script/Pal.PalGameWorldSettings]'))` — the section-rename tuple moves to the caller."
    - "After this plan, `python -c 'import logpose.main; logpose.main.install.__wrapped__'` raises no TypeError on reference lookups; importing succeeds cleanly."
    - "No helper call inside any Typer command function passes a wrong number of arguments or mismatched types — `mypy --strict logpose/main.py` (if run) would type-check cleanly on the helpers' signatures (mypy not required, but the type-matching is a hand-verifiable invariant)."
    - "Plan 01 byte-diff harness still exits 0 when invoked: `pytest tests/test_palworld_golden.py -x`."
  artifacts:
    - path: "logpose/main.py"
      provides: "Typer commands call parameterized helpers with Palworld values sourced from module-scope constants"
      exports: ["install", "update", "edit_settings"]
      contains: "_install_palworld(PAL_SERVER_DIR, 2394010)"
  key_links:
    - from: "logpose/main.py::install"
      to: "logpose/main.py::_install_palworld"
      via: "call with PAL_SERVER_DIR module-global + literal app_id 2394010"
      pattern: "_install_palworld\\(PAL_SERVER_DIR, 2394010\\)"
    - from: "logpose/main.py::install"
      to: "logpose/main.py::_render_service_file, _write_service_file"
      via: "render returns string, passed to write with /etc/systemd/system/palserver.service path"
      pattern: "_write_service_file\\(.*, _render_service_file\\("
    - from: "logpose/main.py::edit_settings"
      to: "logpose/main.py::_create_settings_from_default"
      via: "explicit default_path + dst_path + section_rename tuple"
      pattern: "_create_settings_from_default\\(DEFAULT_PAL_SETTINGS_PATH, PAL_SETTINGS_PATH,"
---

<objective>
Wire the three Typer commands (`install`, `update`, `edit_settings`) to call the new parameterized helper signatures. Values come from module-scope constants (`PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`, `STEAM_DIR`) and the hardcoded Palworld literals (`2394010`, `.steam/sdk64`, `40-palserver.rules`, `palserver.rules.template`, `palserver.service.template`, the section-rename tuple). Module globals STAY at module scope — Plan 03 moved them out of helper BODIES; Plan 04 keeps them as the source that command functions read from. Phase 3 will dissolve these globals into `GAMES["palworld"]`.

Purpose: Closes ARCH-04's Phase 2 partial scope (helpers no longer read module globals), preserves SET-01 (Palworld `edit-settings` still works end-to-end), confirms PAL-08 (`_fix_steam_sdk` Palworld-only sdk64 behavior preserved via caller argument), SET-04 (`_create_settings_from_default` Palworld section-rename preserved via caller argument). After this plan, the module is a complete, cohesive snapshot that behaves byte-identically to v0.1.19 but with parameterized internals ready for Phase 3's `GameSpec` migration.

Output: Updated `install`, `update`, `edit_settings` command bodies in `logpose/main.py`. `logpose install` runs (mechanically) the same sequence as v0.1.19 with byte-identical systemd/polkit output.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md
@.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-02-extract-palworld-parse-save-PLAN.md
@.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-03-parameterize-helpers-PLAN.md
@logpose/main.py

<interfaces>
<!-- Helper signatures after Plan 02 + Plan 03 land (these are what Plan 04 calls into): -->

```python
def _palworld_parse(path: Path) -> dict[str, str]: ...              # Plan 02
def _palworld_save(path: Path, settings: dict[str, str]) -> None: ... # Plan 02
def _run_steamcmd_update(server_dir: Path, app_id: int) -> None: ...   # Plan 03
def _install_palworld(server_dir: Path, app_id: int) -> None: ...      # Plan 03
def _fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path) -> None: ...  # Plan 03
def _render_service_file(
    service_name: str, template_name: str, user: str,
    working_directory: Path, exec_start_path: Path,
    port: int, players: int,
) -> str: ...  # Plan 03
def _write_service_file(service_file: Path, content: str) -> None: ...  # Plan 03
def _setup_polkit(rules_filename: str, template_name: str, user: str) -> None: ...  # Plan 03
def _create_settings_from_default(
    default_path: Path, dst_path: Path,
    section_rename: Optional[tuple[str, str]],
) -> None: ...  # Plan 03
```

Module-scope constants (UNCHANGED by this plan):
```python
STEAM_DIR = Path.home() / ".steam/steam"
PAL_SERVER_DIR = STEAM_DIR / "steamapps/common/PalServer"
PAL_SETTINGS_PATH = PAL_SERVER_DIR / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini"
DEFAULT_PAL_SETTINGS_PATH = PAL_SERVER_DIR / "DefaultPalWorldSettings.ini"
```

v0.1.19 Palworld-specific literals that MUST be threaded via command bodies:
- app_id: `2394010`
- SDK destination: `Path.home() / ".steam/sdk64"`
- steamclient.so source: `STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"`
- service file path: `Path("/etc/systemd/system/palserver.service")`
- service template name: `"palserver.service.template"`
- service name (for `_render_service_file` signature): `"palserver"`
- polkit rules filename: `"40-palserver.rules"`
- polkit rules template name: `"palserver.rules.template"`
- Palworld section-rename tuple: `("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]")`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite install() and update() commands to call parameterized helpers</name>
  <files>logpose/main.py</files>
  <read_first>
    - logpose/main.py (current `install` command at ~line 296 and `update` at ~line 367 after Plan 03 lands; verify Plan 03's new helper signatures are already in place by `grep '^def _render_service_file' logpose/main.py`)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Call Sites")
  </read_first>
  <action>
    In `logpose/main.py`, replace the `install` command body (decorated `@app.command()`, currently at ~line 296). Before edit, verify Plan 03 landed: `grep -q '^def _render_service_file' logpose/main.py` MUST succeed. If not, STOP — Plan 03 has not yet been executed.

    Before:
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

        _install_steamcmd()
        _install_palworld()
        _fix_steam_sdk()
        _create_service_file(port, players)
        _setup_polkit()

        console.print("Installation complete!")
        ...
    ```

    After (only the five helper calls change; preamble and postamble preserved verbatim):
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

        _install_steamcmd()
        _install_palworld(PAL_SERVER_DIR, 2394010)
        _fix_steam_sdk(
            Path.home() / ".steam/sdk64",
            STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so",
        )
        service_content = _render_service_file(
            service_name="palserver",
            template_name="palserver.service.template",
            user=Path.home().name,
            working_directory=PAL_SERVER_DIR,
            exec_start_path=PAL_SERVER_DIR / "PalServer.sh",
            port=port,
            players=players,
        )
        _write_service_file(Path("/etc/systemd/system/palserver.service"), service_content)
        _setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)

        console.print("Installation complete!")

        if start:
            console.print("Starting the server...")
            _run_command("systemctl start palserver")
            console.print("Server started successfully!")
        else:
            console.print(
                "You can now start the server with: palworld-server-launcher start"
            )

        console.print(
            "To enable the server to start on boot, run: palworld-server-launcher enable"
        )
    ```

    Byte-compat notes:
    - `working_directory=PAL_SERVER_DIR` and `exec_start_path=PAL_SERVER_DIR / "PalServer.sh"` match v0.1.19's in-helper derivation exactly. `PAL_SERVER_DIR` is already defined at module scope (line 20).
    - The SDK destination path `Path.home() / ".steam/sdk64"` matches v0.1.19's in-helper literal `Path.home() / ".steam/sdk64"` — byte-identical.
    - The steamclient.so source path reproduces v0.1.19's in-helper expression `STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"` — character-for-character, including the two embedded spaces in `Steamworks SDK Redist`.
    - Keyword-argument calling style for `_render_service_file` is chosen over positional for clarity (7 parameters; positional would be a readability footgun). Both are functionally equivalent.
    - The post-install text strings (`"Installation complete!"`, `"You can now start the server with: palworld-server-launcher start"`, `"To enable the server to start on boot, run: palworld-server-launcher enable"`) are PRESERVED verbatim — Phase 2 does NOT update these to say `logpose palworld ...`; Phase 4 (CLI restructure) does that.
    - `sys.exit(1)` preserved; `typer.Exit` migration is Phase 4 (CLI-05).

    Replace `update` command (at ~line 367):

    Before:
    ```python
    @app.command()
    def update() -> None:
        """Update the Palworld dedicated server."""
        console.print("Updating Palworld dedicated server...")
        _run_steamcmd_update()
        console.print("Update complete! Restart the server for the changes to take effect.")
    ```

    After:
    ```python
    @app.command()
    def update() -> None:
        """Update the Palworld dedicated server."""
        console.print("Updating Palworld dedicated server...")
        _run_steamcmd_update(PAL_SERVER_DIR, 2394010)
        console.print("Update complete! Restart the server for the changes to take effect.")
    ```

    One-line delta — only the `_run_steamcmd_update()` → `_run_steamcmd_update(PAL_SERVER_DIR, 2394010)` change.

    DO NOT touch `start`, `stop`, `restart`, `status`, `enable`, `disable` — they are game-agnostic (`_run_command` calls only) and outside Phase 2's ARCH-04 scope.

    Verify after editing:
    ```bash
    # install() wiring grep hits
    grep -qF '_install_palworld(PAL_SERVER_DIR, 2394010)' logpose/main.py
    grep -qF 'Path.home() / ".steam/sdk64"' logpose/main.py
    grep -qF 'STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"' logpose/main.py
    grep -qF "_write_service_file(Path(\"/etc/systemd/system/palserver.service\"), service_content)" logpose/main.py
    grep -qF '_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)' logpose/main.py

    # update() wiring
    grep -qF '_run_steamcmd_update(PAL_SERVER_DIR, 2394010)' logpose/main.py

    # No stale zero-arg calls
    ! grep -qE '_install_palworld\(\)|_fix_steam_sdk\(\)|_setup_polkit\(\)|_create_service_file\(|_run_steamcmd_update\(\)' logpose/main.py

    # Module imports cleanly
    python -c "import logpose.main"

    # Plan 01 harness still green
    pytest tests/test_palworld_golden.py -x
    ```
  </action>
  <verify>
    <automated>grep -qF '_install_palworld(PAL_SERVER_DIR, 2394010)' logpose/main.py && grep -qF 'Path.home() / ".steam/sdk64"' logpose/main.py && grep -qF 'STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"' logpose/main.py && grep -qF '_run_steamcmd_update(PAL_SERVER_DIR, 2394010)' logpose/main.py && ! grep -qE '_install_palworld\(\)|_fix_steam_sdk\(\)|_setup_polkit\(\)|_create_service_file\(|_run_steamcmd_update\(\)' logpose/main.py && python -c "import logpose.main" && pytest tests/test_palworld_golden.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '_install_palworld(PAL_SERVER_DIR, 2394010)' logpose/main.py` returns `1`.
    - `grep -c '_fix_steam_sdk(' logpose/main.py` returns `1` (only call is inside `install`).
    - `grep -qF 'STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"' logpose/main.py` succeeds.
    - `grep -qF '_render_service_file(' logpose/main.py` succeeds AND the call site uses keyword arguments (`service_name=`, `template_name=`, `user=`, `working_directory=`, `exec_start_path=`, `port=`, `players=` all present in the `install` function body).
    - `grep -qF '_write_service_file(Path("/etc/systemd/system/palserver.service"), service_content)' logpose/main.py` succeeds.
    - `grep -qF '_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)' logpose/main.py` succeeds.
    - `grep -c '_run_steamcmd_update(PAL_SERVER_DIR, 2394010)' logpose/main.py` returns `1` (inside `update` command).
    - ZERO zero-arg calls to old signatures: `grep -cE '_install_palworld\(\)|_fix_steam_sdk\(\)|_setup_polkit\(\)|_create_service_file\(|_run_steamcmd_update\(\)' logpose/main.py` returns `0`.
    - `python -c "import logpose.main"` exits 0.
    - `pytest tests/test_palworld_golden.py -x` exits 0 (template + Plan 03's `_render_service_file` function unchanged — harness still green).
  </acceptance_criteria>
  <done>
    `install` and `update` commands wire to new parameterized helpers with Palworld values sourced from module globals; zero stale zero-arg calls; module imports cleanly; Plan 01 harness unaffected.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update edit_settings to pass section-rename tuple to _create_settings_from_default</name>
  <files>logpose/main.py</files>
  <read_first>
    - logpose/main.py (current `edit_settings` command after Plan 02 landed — it calls `_create_settings_from_default()` with zero args)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Call Sites" — shows exact replacement pattern)
  </read_first>
  <action>
    In `logpose/main.py`, locate the `edit_settings` function (decorated `@app.command(name="edit-settings")`, around line 375). Plan 02 already updated the `_parse_settings`/`_save_settings` calls to `_palworld_parse(PAL_SETTINGS_PATH)` / `_palworld_save(PAL_SETTINGS_PATH, settings)`. This task updates the ONE remaining stale call: `_create_settings_from_default()` → `_create_settings_from_default(DEFAULT_PAL_SETTINGS_PATH, PAL_SETTINGS_PATH, ("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]"))`.

    Before (post-Plan-02):
    ```python
    @app.command(name="edit-settings")
    def edit_settings() -> None:
        """Edit the PalWorldSettings.ini file."""
        try:
            settings = _palworld_parse(PAL_SETTINGS_PATH)
        except (FileNotFoundError, ValueError):
            _create_settings_from_default()       # ← stale zero-arg call
            try:
                settings = _palworld_parse(PAL_SETTINGS_PATH)
            except (ValueError, FileNotFoundError) as e:
                rich.print(
                    f"An error occurred after creating default settings: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)

        try:
            _interactive_edit_loop(settings)
            _palworld_save(PAL_SETTINGS_PATH, settings)
        except Exception as e:
            rich.print(f"An error occurred during settings edit: {e}", file=sys.stderr)
            sys.exit(1)
    ```

    After (section-rename tuple threaded as caller argument):
    ```python
    @app.command(name="edit-settings")
    def edit_settings() -> None:
        """Edit the PalWorldSettings.ini file."""
        try:
            settings = _palworld_parse(PAL_SETTINGS_PATH)
        except (FileNotFoundError, ValueError):
            _create_settings_from_default(
                DEFAULT_PAL_SETTINGS_PATH,
                PAL_SETTINGS_PATH,
                (
                    "[/Script/Pal.PalWorldSettings]",
                    "[/Script/Pal.PalGameWorldSettings]",
                ),
            )
            try:
                settings = _palworld_parse(PAL_SETTINGS_PATH)
            except (ValueError, FileNotFoundError) as e:
                rich.print(
                    f"An error occurred after creating default settings: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)

        try:
            _interactive_edit_loop(settings)
            _palworld_save(PAL_SETTINGS_PATH, settings)
        except Exception as e:
            rich.print(f"An error occurred during settings edit: {e}", file=sys.stderr)
            sys.exit(1)
    ```

    Byte-compat notes:
    - The tuple literal uses EXACT string content matching v0.1.19's inline `replace()`. The surrounding `[` and `]` characters are part of the section header syntax (required). The slashes and dots are literal — do not "fix" any character.
    - Multi-line tuple formatting is recommended for readability; equivalent to `("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]")` on one line. Either form is acceptable; this spec uses multi-line for consistency with the rest of the function.
    - The PAL-05 invariant — Palworld's section-rename behavior — is preserved because `_create_settings_from_default` in Plan 03 applies `content.replace(section_rename[0], section_rename[1])` verbatim when the tuple is non-None.
    - No other changes in `edit_settings`. Specifically, the `_palworld_parse(PAL_SETTINGS_PATH)` calls and the `_palworld_save(PAL_SETTINGS_PATH, settings)` call from Plan 02 stay intact.

    Verify after editing:
    ```bash
    # Section-rename tuple wired
    grep -qF '"[/Script/Pal.PalWorldSettings]"' logpose/main.py
    grep -qF '"[/Script/Pal.PalGameWorldSettings]"' logpose/main.py

    # No stale zero-arg call
    ! grep -qE '_create_settings_from_default\(\s*\)' logpose/main.py

    # Exact call site grep
    grep -c '_create_settings_from_default(' logpose/main.py  # MUST return exactly 1

    # Module imports cleanly
    python -c "import logpose.main"

    # Plan 01 harness still green
    pytest tests/test_palworld_golden.py -x
    ```
  </action>
  <verify>
    <automated>grep -qF '"[/Script/Pal.PalWorldSettings]"' logpose/main.py && grep -qF '"[/Script/Pal.PalGameWorldSettings]"' logpose/main.py && ! grep -qE '_create_settings_from_default\(\s*\)' logpose/main.py && test "$(grep -c '_create_settings_from_default(' logpose/main.py)" = "1" && python -c "import logpose.main" && pytest tests/test_palworld_golden.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -qF '"[/Script/Pal.PalWorldSettings]"' logpose/main.py` succeeds (original section string appears as caller argument).
    - `grep -qF '"[/Script/Pal.PalGameWorldSettings]"' logpose/main.py` succeeds (target section string appears as caller argument).
    - ZERO zero-arg calls: `grep -cE '_create_settings_from_default\(\s*\)' logpose/main.py` returns `0`.
    - EXACTLY one `_create_settings_from_default(` call site: `grep -c '_create_settings_from_default(' logpose/main.py` returns `1`.
    - The call site passes exactly three arguments: `DEFAULT_PAL_SETTINGS_PATH`, `PAL_SETTINGS_PATH`, and the two-tuple. Hand-verify by reading the hunk.
    - `python -c "import logpose.main"` exits 0.
    - `pytest tests/test_palworld_golden.py -x` exits 0 (template + harness unaffected).
    - End-to-end grep sweep on the WHOLE module returns ZERO occurrences of any old helper signature usage:
      ```bash
      ! grep -qE '_parse_settings|_save_settings|_create_service_file|_install_palworld\(\)|_fix_steam_sdk\(\)|_setup_polkit\(\)|_run_steamcmd_update\(\)' logpose/main.py
      ```
  </acceptance_criteria>
  <done>
    `edit_settings` passes the Palworld section-rename tuple as caller argument; zero stale zero-arg calls anywhere in the module; module imports; harness green.
  </done>
</task>

</tasks>

<verification>
```bash
# 1. install() wired correctly
grep -qF '_install_palworld(PAL_SERVER_DIR, 2394010)' logpose/main.py
grep -qF 'Path.home() / ".steam/sdk64"' logpose/main.py
grep -qF 'STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"' logpose/main.py
grep -qF 'service_name="palserver"' logpose/main.py
grep -qF 'template_name="palserver.service.template"' logpose/main.py
grep -qF 'exec_start_path=PAL_SERVER_DIR / "PalServer.sh"' logpose/main.py
grep -qF '_write_service_file(Path("/etc/systemd/system/palserver.service"), service_content)' logpose/main.py
grep -qF '_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)' logpose/main.py

# 2. update() wired
grep -qF '_run_steamcmd_update(PAL_SERVER_DIR, 2394010)' logpose/main.py

# 3. edit_settings() wired
grep -qF '"[/Script/Pal.PalWorldSettings]"' logpose/main.py
grep -qF '"[/Script/Pal.PalGameWorldSettings]"' logpose/main.py

# 4. Zero stale calls anywhere in module
! grep -qE '_parse_settings|_save_settings|_create_service_file|_install_palworld\(\)|_fix_steam_sdk\(\)|_setup_polkit\(\)|_run_steamcmd_update\(\)|_create_settings_from_default\(\s*\)' logpose/main.py

# 5. Module-scope constants still present (Phase 3 will dissolve them)
grep -q '^PAL_SERVER_DIR = ' logpose/main.py
grep -q '^PAL_SETTINGS_PATH = ' logpose/main.py
grep -q '^DEFAULT_PAL_SETTINGS_PATH = ' logpose/main.py

# 6. Module imports + all commands reachable
python -c "import logpose.main; logpose.main.install; logpose.main.update; logpose.main.edit_settings"

# 7. Plan 01 harness still green
pytest tests/test_palworld_golden.py -x

# 8. CLI --help exits 0 (smoke test that typer can still introspect the app)
python -c "
import subprocess, sys
r = subprocess.run([sys.executable, '-m', 'logpose.main', '--help'], capture_output=True, text=True)
assert r.returncode == 0, f'help failed: {r.stderr}'
assert 'install' in r.stdout and 'edit-settings' in r.stdout, f'unexpected help: {r.stdout}'
print('OK')
"
```
</verification>

<success_criteria>
- ARCH-04 (Phase 2 partial scope complete): Every helper in `logpose/main.py` takes game-specific values as arguments; helper bodies read zero Palworld-named module globals. Phase 3 completes ARCH-04 by eliminating the module-scope globals themselves.
- SET-01: `edit_settings` command works end-to-end with the new `_palworld_parse`/`_palworld_save` + `_create_settings_from_default(..., section_rename)` wiring.
- PAL-08: `_fix_steam_sdk` Palworld-only sdk64 behavior is preserved because `install()` passes exactly `Path.home() / ".steam/sdk64"` and the Palworld `steamclient.so` source path.
- SET-04: `_create_settings_from_default` Palworld section-rename preserved — caller threads the exact v0.1.19 tuple.
- Plan 01 harness still green (template unchanged, `_render_service_file` unchanged by this plan).
- CLI smoke: `python -m logpose.main --help` exits 0 and lists all commands.
</success_criteria>

<output>
After completion, create `.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-04-SUMMARY.md` documenting:
- All helper call sites updated (grep output counts per helper).
- Zero stale zero-arg call grep confirms clean sweep.
- `python -c "import logpose.main"` exit code.
- `python -m logpose.main --help` smoke test stdout head.
- Plan 01 harness re-run exit code.
</output>
