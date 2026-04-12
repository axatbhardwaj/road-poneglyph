---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 03
type: execute
wave: 2
depends_on: ["02-parameterize-helpers-no-games-dict-yet/02"]
files_modified:
  - logpose/main.py
autonomous: true
requirements: [ARCH-04, PAL-08, SET-04]
tags: [refactor, palworld, parameterization, python]

must_haves:
  truths:
    - "`_run_steamcmd_update(server_dir: Path, app_id: int)` exists; body no longer reads `PAL_SERVER_DIR` or the hardcoded `2394010` literal directly — both come from arguments."
    - "`_install_palworld(server_dir: Path, app_id: int)` exists as a thin wrapper calling `_run_steamcmd_update(server_dir, app_id)`."
    - "`_fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path)` exists; body no longer reads `STEAM_DIR` directly; both paths are arguments (PAL-08 — Palworld still passes `~/.steam/sdk64` and the steamclient.so path as args from the caller)."
    - "`_render_service_file(service_name: str, template_name: str, user: str, working_directory: Path, exec_start_path: Path, port: int, players: int) -> str` exists and RETURNS the rendered service content as a string — no I/O, no sudo, pure."
    - "`_write_service_file(service_file: Path, content: str) -> None` exists and writes via `echo ... | sudo tee` + `systemctl daemon-reload` — matching v0.1.19's side effects byte-for-byte."
    - "`_create_service_file(port, players)` no longer exists under that signature — it is replaced by the render+write split."
    - "`_setup_polkit(rules_filename: str, template_name: str, user: str)` exists with parameterized filename + template name; rule body literal (`palserver.service`) stays hardcoded per Pitfall 6 / Phase 4 boundary."
    - "`_create_settings_from_default(default_path: Path, dst_path: Path, section_rename: Optional[tuple[str, str]])` exists; body preserves the `[/Script/Pal.PalWorldSettings]` → `[/Script/Pal.PalGameWorldSettings]` string-rename verbatim via `content.replace(old, new)`."
    - "No helper body in `logpose/main.py` (other than Typer command functions themselves) reads `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`, or `STEAM_DIR` directly — grep returns zero hits inside helper bodies."
    - "Module-level `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`, `STEAM_DIR` constants STAY at module scope (Typer commands still read them — dissolution is Phase 3)."
  artifacts:
    - path: "logpose/main.py"
      provides: "Parameterized helper signatures; render/write split; module-globals untouched at module scope"
      exports: ["_run_steamcmd_update", "_install_palworld", "_fix_steam_sdk", "_render_service_file", "_write_service_file", "_setup_polkit", "_create_settings_from_default"]
      contains:
        - "def _render_service_file("
        - "def _write_service_file("
  key_links:
    - from: "logpose/main.py::_render_service_file"
      to: "logpose/main.py::_get_template"
      via: "_get_template(template_name) read + .format(**placeholders)"
      pattern: "_get_template\\(template_name\\)"
    - from: "logpose/main.py::_write_service_file"
      to: "system sudo tee + daemon-reload"
      via: "_run_command(f\"echo '{content}' | sudo tee {service_file}\") then systemctl daemon-reload"
      pattern: "sudo tee"
---

<objective>
Parameterize every remaining Palworld-specific helper in `logpose/main.py` so helper BODIES stop reading module globals (`STEAM_DIR`, `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`) and hardcoded values (`2394010`, `~/.steam/sdk64`, `steamclient.so` source path, `"40-palserver.rules"`, `"palserver.rules.template"`). Split `_create_service_file` into `_render_service_file` (pure, returns bytes-equivalent string) and `_write_service_file` (I/O sudo tee + daemon-reload). Typer command bodies and module-global constants stay untouched — Plan 04 wires the new signatures into `install()`.

Purpose: Satisfies ARCH-04 (partial; completed in Phase 3) for every helper the user can reasonably test by re-running the harness. Satisfies PAL-08 prep (`_fix_steam_sdk` Palworld-only sdk64 behavior preserved via caller argument). Satisfies SET-04 (`_create_settings_from_default` parameterized while section-rename strings stay verbatim). Enables Plan 05 (render-real-path harness test) by exposing a pure `_render_service_file` function.

Output: Refactored helper bodies; new `_render_service_file` + `_write_service_file` pair replacing `_create_service_file`; module still imports cleanly; Plan 01 harness still green (template unchanged). `install()` will have broken call signatures until Plan 04 runs — that is the intended staging.
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
@logpose/main.py
@logpose/templates/palserver.service.template
@logpose/templates/palserver.rules.template

<interfaces>
<!-- Recommended signatures from research section "Parameterization Pattern". -->
<!-- Every game-specific arg is REQUIRED (no defaults) to avoid Pitfall 2 ("default-arg game key forbidden"). -->

Target signatures (after this plan lands):

```python
def _run_steamcmd_update(server_dir: Path, app_id: int) -> None: ...
def _install_palworld(server_dir: Path, app_id: int) -> None: ...
def _fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path) -> None: ...
def _render_service_file(
    service_name: str,
    template_name: str,
    user: str,
    working_directory: Path,
    exec_start_path: Path,
    port: int,
    players: int,
) -> str: ...
def _write_service_file(service_file: Path, content: str) -> None: ...
def _setup_polkit(rules_filename: str, template_name: str, user: str) -> None: ...
def _create_settings_from_default(
    default_path: Path,
    dst_path: Path,
    section_rename: Optional[tuple[str, str]],
) -> None: ...
```

Current helper bodies to rewrite (source: logpose/main.py):

`_run_steamcmd_update` (lines 129-134):
```python
def _run_steamcmd_update():
    _run_command(f"steamcmd +force_install_dir '{PAL_SERVER_DIR}' +login anonymous +app_update 2394010 validate +quit")
    pal_server_script = PAL_SERVER_DIR / "PalServer.sh"
    if pal_server_script.exists():
        _run_command(f"chmod +x {pal_server_script}")
```

`_fix_steam_sdk` (lines 143-157):
```python
def _fix_steam_sdk() -> None:
    console.print("Fixing Steam SDK errors...")
    steam_sdk_path = Path.home() / ".steam/sdk64"
    steam_sdk_path.mkdir(parents=True, exist_ok=True)
    steam_client_so = (
        STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"
    )
    if steam_client_so.exists():
        _run_command(f"cp {steam_client_so} {steam_sdk_path}/")
    else:
        rich.print(f"Warning: {steam_client_so} not found. This might cause issues.", file=sys.stderr)
```

`_create_service_file` (lines 160-176):
```python
def _create_service_file(port: int, players: int) -> None:
    console.print("Creating Pal Server service...")
    user = Path.home().name
    service_file = Path("/etc/systemd/system/palserver.service")
    template = _get_template("palserver.service.template")
    pal_server_dir = STEAM_DIR / "steamapps/common/PalServer"
    exec_start_path = pal_server_dir / "PalServer.sh"
    service_content = template.format(
        user=user, port=port, players=players,
        exec_start_path=exec_start_path, working_directory=pal_server_dir,
    )
    _run_command(f"echo '{service_content}' | sudo tee {service_file}")
    _run_command("sudo systemctl daemon-reload")
```

`_setup_polkit` (lines 179-188):
```python
def _setup_polkit() -> None:
    console.print("Setting up policy for non-sudo control...")
    user = Path.home().name
    policy_file = Path("/etc/polkit-1/rules.d/40-palserver.rules")
    _run_command(f"sudo mkdir -p {policy_file.parent}")
    template = _get_template("palserver.rules.template")
    policy_content = template.format(user=user)
    _run_command(f"echo '{policy_content}' | sudo tee {policy_file}")
    _run_command("sudo systemctl restart polkit.service")
```

`_create_settings_from_default` (lines 229-252) — note section-rename is at lines 248-251.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Parameterize _run_steamcmd_update, _install_palworld, _fix_steam_sdk</name>
  <files>logpose/main.py</files>
  <read_first>
    - logpose/main.py (current bodies of `_run_steamcmd_update` lines 129-134, `_install_palworld` lines 137-140, `_fix_steam_sdk` lines 143-157)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Parameterization Pattern" + "Pitfall 2: default-arg game key forbidden")
  </read_first>
  <behavior>
    - `_run_steamcmd_update(Path("/home/foo/.steam/steam/steamapps/common/PalServer"), 2394010)` invokes steamcmd with EXACTLY the v0.1.19 command string when `server_dir=/home/foo/.steam/steam/steamapps/common/PalServer` and `app_id=2394010` — the rendered `_run_command` argument must be byte-identical to `steamcmd +force_install_dir '/home/foo/.steam/steam/steamapps/common/PalServer' +login anonymous +app_update 2394010 validate +quit`.
    - `_install_palworld(server_dir, app_id)` delegates to `_run_steamcmd_update(server_dir, app_id)` with a prefix `console.print("Installing Palworld dedicated server...")`.
    - `_fix_steam_sdk(steam_sdk_dst, steam_client_so)` calls `steam_sdk_dst.mkdir(parents=True, exist_ok=True)`, then `cp {steam_client_so} {steam_sdk_dst}/` via `_run_command` when the source exists; else prints warning to stderr.
    - None of the three helpers reads `PAL_SERVER_DIR`, `STEAM_DIR`, or the literal `2394010` from module scope. Grep confirms.
  </behavior>
  <action>
    In `logpose/main.py`, replace the three functions as follows.

    Replace `_run_steamcmd_update` (currently `def _run_steamcmd_update():` at ~line 129):
    ```python
    def _run_steamcmd_update(server_dir: Path, app_id: int) -> None:
        """Runs steamcmd to install/update the dedicated server for the given app."""
        _run_command(
            f"steamcmd +force_install_dir '{server_dir}' +login anonymous "
            f"+app_update {app_id} validate +quit"
        )
        server_script = server_dir / "PalServer.sh"
        if server_script.exists():
            _run_command(f"chmod +x {server_script}")
    ```

    Byte-compat note: the concatenated f-string MUST produce IDENTICAL output to the single-line v0.1.19 command. Test mentally: `f"steamcmd +force_install_dir '{server_dir}' +login anonymous " f"+app_update {app_id} validate +quit"` → with `server_dir=/home/foo/.../PalServer` and `app_id=2394010` → `steamcmd +force_install_dir '/home/foo/.../PalServer' +login anonymous +app_update 2394010 validate +quit`. Two adjacent string literals in Python concatenate with NO intervening space — the space BEFORE the closing `"` in the first literal and before `+app_update` in the second produce exactly one space between `anonymous` and `+app_update`, matching v0.1.19.

    IMPORTANT: the Palworld-specific binary name `PalServer.sh` stays hardcoded here in Phase 2. Phase 3 generalizes this via `spec.binary_rel_path` — that is explicitly out of scope. The research recommendation lists `binary_rel_path` in the Phase 3 signature; Phase 2 keeps `PalServer.sh` literal to minimize diff.

    Replace `_install_palworld` (currently `def _install_palworld() -> None:` at ~line 137):
    ```python
    def _install_palworld(server_dir: Path, app_id: int) -> None:
        """Install Palworld dedicated server using steamcmd."""
        console.print("Installing Palworld dedicated server...")
        _run_steamcmd_update(server_dir, app_id)
    ```

    Replace `_fix_steam_sdk` (currently `def _fix_steam_sdk() -> None:` at ~line 143):
    ```python
    def _fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path) -> None:
        """Copy steamclient.so into the game's Steam SDK directory (Palworld: sdk64 only)."""
        console.print("Fixing Steam SDK errors...")
        steam_sdk_dst.mkdir(parents=True, exist_ok=True)
        if steam_client_so.exists():
            _run_command(f"cp {steam_client_so} {steam_sdk_dst}/")
        else:
            rich.print(
                f"Warning: {steam_client_so} not found. This might cause issues.",
                file=sys.stderr,
            )
    ```

    No defaults on any parameter — per Pitfall 2, passing defaults here would silently mis-configure ARK in Phase 5.

    After editing, grep invariants:
    ```bash
    ! grep -qE 'STEAM_DIR|PAL_SERVER_DIR|2394010' <(sed -n '/^def _run_steamcmd_update/,/^def /p' logpose/main.py | head -n -1)
    ! grep -qE 'STEAM_DIR' <(sed -n '/^def _fix_steam_sdk/,/^def /p' logpose/main.py | head -n -1)
    ```
    (These greps check that the three helper bodies no longer read module globals. Module-scope constants are untouched.)
  </action>
  <verify>
    <automated>grep -qE '^def _run_steamcmd_update\(server_dir: Path, app_id: int\) -> None:' logpose/main.py && grep -qE '^def _install_palworld\(server_dir: Path, app_id: int\) -> None:' logpose/main.py && grep -qE '^def _fix_steam_sdk\(steam_sdk_dst: Path, steam_client_so: Path\) -> None:' logpose/main.py && python -c "import ast; ast.parse(open('logpose/main.py').read())"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '^def _run_steamcmd_update(server_dir: Path, app_id: int) -> None:' logpose/main.py` returns `1`.
    - `grep -c '^def _install_palworld(server_dir: Path, app_id: int) -> None:' logpose/main.py` returns `1`.
    - `grep -c '^def _fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path) -> None:' logpose/main.py` returns `1`.
    - Inside the body of `_run_steamcmd_update` (lines from `def _run_steamcmd_update` to the next `^def `): zero occurrences of `PAL_SERVER_DIR`, zero occurrences of `2394010`, zero occurrences of `STEAM_DIR`.
    - Inside the body of `_fix_steam_sdk`: zero occurrences of `STEAM_DIR`, zero occurrences of the literal string `".steam/sdk64"` (extract path comes from argument now).
    - Inside `_install_palworld`: exactly ONE call to `_run_steamcmd_update(server_dir, app_id)`.
    - The f-string in `_run_steamcmd_update` produces the byte-identical v0.1.19 command when interpolated — assert by unit check: `python -c "server_dir='/tmp/x'; app_id=2394010; cmd = f\"steamcmd +force_install_dir '{server_dir}' +login anonymous \" f\"+app_update {app_id} validate +quit\"; assert cmd == \"steamcmd +force_install_dir '/tmp/x' +login anonymous +app_update 2394010 validate +quit\", cmd"` exits 0.
    - No default arguments on any parameter: `grep -E 'def (_run_steamcmd_update|_install_palworld|_fix_steam_sdk)\(' logpose/main.py | grep -qE '=' && exit 1 || true` (the grep for `=` inside the signature line MUST fail).
    - `python -c "import logpose.main"` exits 0.
  </acceptance_criteria>
  <done>
    All three helpers parameterized; no module-globals read inside their bodies; no default arguments; module parses.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Split _create_service_file into _render_service_file + _write_service_file</name>
  <files>logpose/main.py</files>
  <read_first>
    - logpose/main.py (current `_create_service_file` at lines 160-176)
    - logpose/templates/palserver.service.template (the 5-placeholder template being rendered)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (Pitfall 4: "harness passes because it's running the helper unused code path" — this task's split is the fix)
  </read_first>
  <behavior>
    - `_render_service_file(service_name="palserver", template_name="palserver.service.template", user="foo", working_directory=Path("/home/foo/.steam/steam/steamapps/common/PalServer"), exec_start_path=Path("/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh"), port=8211, players=32)` returns a `str` which, when encoded as UTF-8, equals the bytes of `tests/golden/palserver.service.v0_1_19` EXACTLY.
    - `_render_service_file` has NO side effects: no `_run_command`, no `console.print`, no filesystem writes. Pure.
    - `_write_service_file(service_file=Path("/etc/systemd/system/palserver.service"), content="...")` runs `echo '{content}' | sudo tee {service_file}` then `sudo systemctl daemon-reload` via `_run_command` — matching v0.1.19 side effects.
    - The old `_create_service_file(port, players)` no longer exists.
    - `service_name` parameter is accepted but UNUSED inside `_render_service_file` in Phase 2 (the template doesn't reference it). Retained in the signature because Phase 3 will need it to derive the `service_file` path from `spec.service_name` when the caller is a factory; accepting it now matches the Phase 3 signature and avoids a re-parameterization churn. Suppress unused-warnings by an underscore rename `_service_name` OR document in a `# noqa` comment OR simply let it be (it is not wired to anything that warns).
  </behavior>
  <action>
    In `logpose/main.py`, replace the single `_create_service_file(port, players)` function (at ~line 160) with TWO new functions. Insert them in the same location (preserving surrounding function order):

    ```python
    def _render_service_file(
        service_name: str,
        template_name: str,
        user: str,
        working_directory: Path,
        exec_start_path: Path,
        port: int,
        players: int,
    ) -> str:
        """Render a systemd unit file from a template. Pure: no I/O side effects."""
        # `service_name` is accepted for signature symmetry with Phase 3 (caller derives
        # the install path from it); the service template itself does not reference it.
        _ = service_name  # silence "unused parameter" linters; kept for Phase 3 shape
        template = _get_template(template_name)
        return template.format(
            user=user,
            port=port,
            players=players,
            exec_start_path=exec_start_path,
            working_directory=working_directory,
        )


    def _write_service_file(service_file: Path, content: str) -> None:
        """Write rendered service content to disk via sudo tee and reload systemd."""
        console.print("Creating Pal Server service...")
        _run_command(f"echo '{content}' | sudo tee {service_file}")
        _run_command("sudo systemctl daemon-reload")
    ```

    Byte-compat invariants:
    - `_get_template(template_name)` is called with the parameter (not a hardcoded `"palserver.service.template"`). This means Plan 05's harness can exercise `_render_service_file` directly by passing the fixture values — and the harness will read the same template the install path reads.
    - `template.format(...)` keyword argument order is EXACTLY the v0.1.19 order: `user, port, players, exec_start_path, working_directory`. `str.format` is order-insensitive for keyword args, but matching order keeps `git blame` clean.
    - `console.print("Creating Pal Server service...")` MOVES from the old `_create_service_file` into `_write_service_file` — it is an I/O-adjacent side effect and belongs with the write half. Plan 05's harness tests `_render_service_file` and so will NOT trigger this print (harness is side-effect-free — the right property).
    - Plan 01 golden was captured by `template.format(**FIXTURE)`, identical to the method call chain `_get_template(tn).format(**placeholders)` inside `_render_service_file`. Therefore `_render_service_file(...).encode("utf-8") == tests/golden/palserver.service.v0_1_19.read_bytes()`. Plan 05 validates this.
    - The `Path("/etc/systemd/system/palserver.service")` literal MOVES OUT of the helper; the CALLER (Plan 04 wires `install()`) constructs it from `Path("/etc/systemd/system") / f"{service_name}.service"`. In Plan 03, we simply do not reinstantiate it inside `_write_service_file` — the path is an argument.
    - `_install_palworld`, `_fix_steam_sdk`, `_setup_polkit` call chain inside `install()` will BREAK after this task because `_create_service_file(port, players)` no longer exists. This is expected. Plan 04 fixes it. DO NOT update `install()` in this task — that is Plan 04's responsibility.

    After editing, grep invariants:
    ```bash
    ! grep -qE '^def _create_service_file' logpose/main.py    # old function deleted
    grep -qE '^def _render_service_file' logpose/main.py      # new pure function exists
    grep -qE '^def _write_service_file' logpose/main.py       # new write function exists
    grep -c '_get_template(template_name)' logpose/main.py    # exactly 1 (inside _render_service_file)
    ```
  </action>
  <verify>
    <automated>! grep -qE '^def _create_service_file' logpose/main.py && grep -qE '^def _render_service_file\(' logpose/main.py && grep -qE '^def _write_service_file\(service_file: Path, content: str\) -> None:' logpose/main.py && python -c "import ast; ast.parse(open('logpose/main.py').read())" && python -c "import logpose.main; out = logpose.main._render_service_file('palserver', 'palserver.service.template', 'foo', __import__('pathlib').Path('/home/foo/.steam/steam/steamapps/common/PalServer'), __import__('pathlib').Path('/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh'), 8211, 32); import pathlib; golden = pathlib.Path('tests/golden/palserver.service.v0_1_19').read_bytes(); assert out.encode('utf-8') == golden, f'drift: {len(out.encode())} vs {len(golden)}'"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '^def _create_service_file' logpose/main.py` returns `0` (old function deleted).
    - `grep -c '^def _render_service_file(' logpose/main.py` returns `1`.
    - `grep -c '^def _write_service_file(service_file: Path, content: str) -> None:' logpose/main.py` returns `1`.
    - `_render_service_file` body contains ZERO calls to `_run_command` (grep within its body returns 0).
    - `_render_service_file` body contains ZERO calls to `console.print` (grep within its body returns 0).
    - `_render_service_file` signature has 7 parameters in exactly this order: `service_name, template_name, user, working_directory, exec_start_path, port, players`.
    - `_write_service_file` body contains `_run_command(f"echo '{content}' | sudo tee {service_file}")` (byte-identical to v0.1.19's `sudo tee` invocation).
    - `_write_service_file` body contains `_run_command("sudo systemctl daemon-reload")`.
    - `python -c "import logpose.main"` exits 0.
    - Direct functional test — call `_render_service_file` with the Plan 01 FIXTURE and assert the UTF-8 encoded output equals `tests/golden/palserver.service.v0_1_19`:
      ```bash
      python - <<'PY'
      from pathlib import Path
      import logpose.main as m
      out = m._render_service_file(
          "palserver", "palserver.service.template", "foo",
          Path("/home/foo/.steam/steam/steamapps/common/PalServer"),
          Path("/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh"),
          8211, 32,
      )
      assert out.encode("utf-8") == Path("tests/golden/palserver.service.v0_1_19").read_bytes()
      print("OK")
      PY
      ```
      MUST print `OK`.
    - Plan 01 harness still green: `pytest tests/test_palworld_golden.py -x` exits 0.
  </acceptance_criteria>
  <done>
    `_create_service_file` deleted; `_render_service_file` pure + byte-compat with v0.1.19; `_write_service_file` preserves sudo tee + daemon-reload side effects; direct golden equality check passes.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Parameterize _setup_polkit and _create_settings_from_default</name>
  <files>logpose/main.py</files>
  <read_first>
    - logpose/main.py (current `_setup_polkit` at ~line 179, `_create_settings_from_default` at ~line 229)
    - logpose/templates/palserver.rules.template (the polkit rule template)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (sections on `_setup_polkit` light touch + Pitfall 6: Section-rename string drift)
  </read_first>
  <behavior>
    - `_setup_polkit(rules_filename="40-palserver.rules", template_name="palserver.rules.template", user="foo")` writes `/etc/polkit-1/rules.d/40-palserver.rules` with rule body containing `palserver.service` literal (unchanged from v0.1.19). Phase 4 merges this into `40-logpose.rules`; Phase 2 only parameterizes the filename + template name.
    - The polkit rule body STILL references `palserver.service` as a hardcoded string inside the template (not parameterized in Phase 2). This is deliberate per research recommendation 3 ("Light touch in Phase 2").
    - `_create_settings_from_default(default_path, dst_path, section_rename)` reads `default_path`, conditionally applies the section-rename via `content.replace(old, new)`, writes to `dst_path`. When `section_rename` is `None`, no replacement occurs (generalizes for ARK in Phase 5, which passes `None`).
    - The hardcoded Palworld section-rename strings `"[/Script/Pal.PalWorldSettings]"` and `"[/Script/Pal.PalGameWorldSettings]"` MOVE OUT of the helper body and into the CALLER (Plan 04 wires them from `edit_settings`). Inside the helper, the replacement is `content = content.replace(section_rename[0], section_rename[1])` — byte-compat with v0.1.19.
    - Neither helper body reads `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`, or `STEAM_DIR` anywhere.
  </behavior>
  <action>
    In `logpose/main.py`, replace `_setup_polkit` (at ~line 179) with:

    ```python
    def _setup_polkit(rules_filename: str, template_name: str, user: str) -> None:
        """Allow `user` to control the service without sudo via a polkit rule file."""
        console.print("Setting up policy for non-sudo control...")
        policy_file = Path("/etc/polkit-1/rules.d") / rules_filename
        _run_command(f"sudo mkdir -p {policy_file.parent}")
        template = _get_template(template_name)
        policy_content = template.format(user=user)
        _run_command(f"echo '{policy_content}' | sudo tee {policy_file}")
        _run_command("sudo systemctl restart polkit.service")
    ```

    Byte-compat notes:
    - `Path("/etc/polkit-1/rules.d") / rules_filename` is EQUIVALENT to `Path(f"/etc/polkit-1/rules.d/{rules_filename}")`. Using the `/` operator matches pathlib conventions already in use at `logpose/main.py:22` (`STEAM_DIR / "steamapps/common/PalServer"`). With `rules_filename="40-palserver.rules"`, the resulting path is `/etc/polkit-1/rules.d/40-palserver.rules` — byte-identical to v0.1.19.
    - `user = Path.home().name` is DELETED from this helper body. The caller (Plan 04 wires `install()`) now passes `Path.home().name` explicitly.
    - The template body (which references `palserver.service`) is UNCHANGED — Phase 2 does NOT touch `palserver.rules.template`. Phase 4 introduces `40-logpose.rules.template` with a JS array pattern; the old template stays on disk until then.

    Replace `_create_settings_from_default` (at ~line 229) with:

    ```python
    def _create_settings_from_default(
        default_path: Path,
        dst_path: Path,
        section_rename: Optional[tuple[str, str]],
    ) -> None:
        """Create a settings file from a default template, optionally renaming a section header."""
        if not default_path.exists():
            console.print(
                f"Default configuration file not found at {default_path}",
                file=sys.stderr,
            )
            console.print(
                "Cannot create a new settings file. Please run `install` first or run the server once.",
                file=sys.stderr,
            )
            sys.exit(1)

        console.print(
            "Configuration file is missing, empty, or corrupted. Creating a new one from default settings."
        )
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        content = default_path.read_text()
        if section_rename is not None:
            # Palworld-specific behavior: game uses PalGameWorldSettings in the saved config,
            # so the section header is renamed at create-time. ARK passes None.
            content = content.replace(section_rename[0], section_rename[1])
        dst_path.write_text(content)
    ```

    Byte-compat notes:
    - The error messages are COPIED BYTE-FOR-BYTE from v0.1.19 ("Default configuration file not found at ...", "Cannot create a new settings file. Please run `install` first or run the server once.", "Configuration file is missing, empty, or corrupted. Creating a new one from default settings.").
    - `sys.exit(1)` preserved — Phase 4 converts to `typer.Exit`, not Phase 2.
    - `dst_path.parent.mkdir(parents=True, exist_ok=True)` preserved as a direct method call on the dst_path parameter (replaces v0.1.19's `PAL_SETTINGS_PATH.parent.mkdir(...)`).
    - The `section_rename` parameter is `Optional[tuple[str, str]]`; `None` disables the rename. Plan 04's caller passes `("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]")` for Palworld. This matches the Phase 3 `GameSpec.settings_section_rename` field shape.
    - `from typing import Optional` is ALREADY imported at top of file (verified: line 10 `from typing import Optional`). Do NOT re-import.

    After editing, grep invariants:
    ```bash
    # _setup_polkit signature
    grep -qE '^def _setup_polkit\(rules_filename: str, template_name: str, user: str\) -> None:' logpose/main.py

    # _setup_polkit body has NO Path.home().name read (caller passes user now)
    sed -n '/^def _setup_polkit/,/^def /p' logpose/main.py | head -n -1 | grep -qE 'Path\.home\(\)\.name' && echo FAIL || echo OK
    # MUST print OK

    # _create_settings_from_default signature
    grep -qE '^def _create_settings_from_default\(' logpose/main.py

    # Section-rename strings MOVED OUT of helper body
    sed -n '/^def _create_settings_from_default/,/^def /p' logpose/main.py | head -n -1 | grep -qE 'PalWorldSettings|PalGameWorldSettings' && echo FAIL || echo OK
    # MUST print OK — the literals are now in the caller (Plan 04)
    ```
  </action>
  <verify>
    <automated>grep -qE '^def _setup_polkit\(rules_filename: str, template_name: str, user: str\) -> None:' logpose/main.py && grep -qE '^def _create_settings_from_default\(' logpose/main.py && ! ( sed -n '/^def _create_settings_from_default/,/^def /p' logpose/main.py | head -n -1 | grep -qE 'PalWorldSettings|PalGameWorldSettings' ) && ! ( sed -n '/^def _setup_polkit/,/^def /p' logpose/main.py | head -n -1 | grep -qE 'Path\.home\(\)\.name' ) && python -c "import ast; ast.parse(open('logpose/main.py').read())"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '^def _setup_polkit(rules_filename: str, template_name: str, user: str) -> None:' logpose/main.py` returns `1`.
    - `grep -c '^def _create_settings_from_default(' logpose/main.py` returns `1`.
    - `_setup_polkit` body does NOT contain `Path.home().name` (user comes from parameter).
    - `_setup_polkit` body does NOT contain the hardcoded string `"40-palserver.rules"` (filename comes from parameter).
    - `_setup_polkit` body does NOT contain the hardcoded string `"palserver.rules.template"` (template name comes from parameter).
    - `_create_settings_from_default` body does NOT contain the literal strings `"[/Script/Pal.PalWorldSettings]"` OR `"[/Script/Pal.PalGameWorldSettings]"` — they are now supplied by the caller.
    - `_create_settings_from_default` body does NOT contain `DEFAULT_PAL_SETTINGS_PATH` or `PAL_SETTINGS_PATH` references.
    - `_create_settings_from_default` body contains `content.replace(section_rename[0], section_rename[1])` verbatim.
    - Error message strings are verbatim from v0.1.19: `grep -qF 'Default configuration file not found at' logpose/main.py` succeeds; `grep -qF 'Cannot create a new settings file' logpose/main.py` succeeds; `grep -qF 'Configuration file is missing, empty, or corrupted' logpose/main.py` succeeds.
    - `from typing import Optional` is present at the top of `logpose/main.py` (should already be there from Phase 1).
    - `python -c "import logpose.main"` exits 0.
    - Plan 01 harness still green: `pytest tests/test_palworld_golden.py -x` exits 0 (template unchanged).
  </acceptance_criteria>
  <done>
    Both helpers parameterized per research "light touch" recommendation; section-rename moved to caller; polkit rule body template still references `palserver.service` literal (Phase 4's job to merge); error strings byte-identical; module imports cleanly.
  </done>
</task>

</tasks>

<verification>
```bash
# 1. Signatures
grep -qE '^def _run_steamcmd_update\(server_dir: Path, app_id: int\) -> None:' logpose/main.py
grep -qE '^def _install_palworld\(server_dir: Path, app_id: int\) -> None:' logpose/main.py
grep -qE '^def _fix_steam_sdk\(steam_sdk_dst: Path, steam_client_so: Path\) -> None:' logpose/main.py
grep -qE '^def _render_service_file\(' logpose/main.py
grep -qE '^def _write_service_file\(service_file: Path, content: str\) -> None:' logpose/main.py
grep -qE '^def _setup_polkit\(rules_filename: str, template_name: str, user: str\) -> None:' logpose/main.py
grep -qE '^def _create_settings_from_default\(' logpose/main.py

# 2. Old function gone
! grep -qE '^def _create_service_file' logpose/main.py

# 3. Helper bodies no longer read module globals (check each body scoped region)
# _fix_steam_sdk body — no STEAM_DIR
! ( sed -n '/^def _fix_steam_sdk/,/^def /p' logpose/main.py | head -n -1 | grep -q 'STEAM_DIR' )
# _run_steamcmd_update body — no PAL_SERVER_DIR and no 2394010
! ( sed -n '/^def _run_steamcmd_update/,/^def /p' logpose/main.py | head -n -1 | grep -qE 'PAL_SERVER_DIR|2394010' )
# _create_settings_from_default body — no PAL_SETTINGS_PATH or DEFAULT_PAL_SETTINGS_PATH, no section strings
! ( sed -n '/^def _create_settings_from_default/,/^def /p' logpose/main.py | head -n -1 | grep -qE 'PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH|PalWorldSettings|PalGameWorldSettings' )

# 4. Module-scope constants still present (dissolution is Phase 3)
grep -q '^STEAM_DIR = ' logpose/main.py
grep -q '^PAL_SERVER_DIR = ' logpose/main.py
grep -q '^PAL_SETTINGS_PATH = ' logpose/main.py
grep -q '^DEFAULT_PAL_SETTINGS_PATH = ' logpose/main.py

# 5. Module parses & imports
python -c "import logpose.main"

# 6. _render_service_file produces byte-identical output to Plan 01 golden
python - <<'PY'
from pathlib import Path
import logpose.main as m
out = m._render_service_file(
    "palserver", "palserver.service.template", "foo",
    Path("/home/foo/.steam/steam/steamapps/common/PalServer"),
    Path("/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh"),
    8211, 32,
)
golden = Path("tests/golden/palserver.service.v0_1_19").read_bytes()
assert out.encode("utf-8") == golden, f"drift: rendered={len(out.encode())}, golden={len(golden)}"
print("OK")
PY

# 7. Plan 01 harness still green
pytest tests/test_palworld_golden.py -x
```

Expected status after this plan: `install()` Typer command is currently CALLING deleted/changed signatures (`_install_palworld()`, `_fix_steam_sdk()`, `_create_service_file(port, players)`, `_setup_polkit()`). Invoking `logpose install` would raise TypeError. This is intentional — Plan 04 wires `install()` in the next wave. Plan 01's harness does NOT invoke `install()` so it stays green.
</verification>

<success_criteria>
- ARCH-04 (partial): All game-aware helpers (`_run_steamcmd_update`, `_install_palworld`, `_fix_steam_sdk`, `_render_service_file`, `_write_service_file`, `_setup_polkit`, `_create_settings_from_default`) take game-specific values as parameters; helper bodies do not read `PAL_*` or `STEAM_DIR` directly.
- PAL-08 prep: `_fix_steam_sdk` accepts `steam_sdk_dst` and `steam_client_so` as arguments — Palworld callers will pass `Path.home() / ".steam/sdk64"` and the `steamclient.so` path; Phase 5 ARK callers add sdk32.
- SET-04: `_create_settings_from_default` parameterized with `Optional[tuple[str, str]]` section-rename — Palworld passes the rename tuple; ARK will pass `None` (Phase 5).
- Plan 01 harness invariant preserved (template unchanged).
- `_render_service_file` is pure and byte-equivalent to Plan 01 golden when called with the fixture — Plan 05 tests this directly as the "real code path" oracle.
</success_criteria>

<output>
After completion, create `.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-03-SUMMARY.md` documenting:
- All 7 new signatures confirmed via grep.
- Helper-body grep results proving zero `PAL_*`/`STEAM_DIR` reads inside helper bodies.
- Direct functional check: `_render_service_file(fixture).encode() == golden.read_bytes()` with exit code.
- Note that `install()` command is intentionally broken pending Plan 04 wiring.
</output>
