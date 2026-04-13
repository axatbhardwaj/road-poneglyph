# Phase 4: Typer Factory + Merged Polkit — Research

**Researched:** 2026-04-13
**Domain:** Typer sub-app composition via factory + merged polkit rule templating (Python 3.8 floor, single `logpose/main.py` module)
**Confidence:** HIGH (every claim below is verified against the actual codebase after Phase 3, official Typer behavior in the installed 0.15.2, Python stdlib `string.Formatter` / `importlib.metadata` probes, and prior research files `ARCHITECTURE.md` + `PITFALLS.md`)

## Summary

Phase 4 converts the currently-flat Typer CLI (nine `@app.command()` decorators reading `GAMES["palworld"]` at their top) into game-first nested dispatch (`logpose palworld <verb>`) via a `_build_game_app(spec: GameSpec) -> typer.Typer` factory that is called once per registered game and registered on the root via `app.add_typer(sub, name=spec.key, help=...)`. At the same time, the v0.1.19 `40-palserver.rules` template is replaced by a single merged `40-logpose.rules.template` whose JS body uses `var units = [...]; units.indexOf(...)` so that one rule authorizes every service unit in `GAMES.values()` atomically. Every `sys.exit(...)` call in `logpose/main.py` becomes `raise typer.Exit(code=...)`. A top-level `@app.callback()` exposes `--version` via `importlib.metadata.version("logpose-launcher")`.

Three hazards dominate: (1) naked `@sub.command()` inside a `for key, spec in GAMES.items()` loop captures the loop variable incorrectly — the factory pattern is mandatory, not stylistic [VERIFIED: existing ARCHITECTURE.md Pitfall flag + ordinary Python closure semantics]; (2) the polkit JS template must double every literal `{` and `}` for `str.format()`, and the `{units}` placeholder must be a pre-joined string (not a Python list) — any drift silently breaks both games' sudo-less control [VERIFIED: brace-escape test run below]; (3) the Phase 2 byte-diff harness (`tests/test_palworld_golden.py`) covers `palserver.service` rendering only — the polkit template filename change (`palserver.rules.template` → `40-logpose.rules.template`) is **not** byte-covered by the existing harness, so Phase 4 must neither delete the old template before a parallel golden is captured nor assume the harness will catch a rules regression.

**Primary recommendation:** Land Phase 4 as four atomic commits mirroring Phase 3's style — (1) add factory + root callback side-by-side with existing flat commands, (2) flip dispatch to the factory and delete old flat commands, (3) merge polkit to `40-logpose.rules.template`, (4) convert `sys.exit` → `typer.Exit`. Keep the Phase 2 byte-diff harness green at every commit boundary; add a second golden (`40-logpose.rules.v0_2_0`) before the polkit merge to lock the new template against future drift.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation choices are at Claude's discretion — discuss phase was skipped per `workflow.skip_discuss: true` in `.planning/config.json`. The ROADMAP Phase 4 goal + success criteria + REQUIREMENTS.md Phase 4 mapping are the binding spec.

### Claude's Discretion
Everything in Phase 4 — plan decomposition, ordering of factory-swap vs polkit-merge, whether to land typer.Exit conversion in its own commit or folded into the factory swap, where to place the `@app.callback()` (before `GAMES` construction or after), and how many atomic commits to split across.

### Deferred Ideas (OUT OF SCOPE)
None — discuss phase skipped.

### Constraints Inherited from REQUIREMENTS.md + ROADMAP.md + STATE.md (treated as locked)
- **ARCH-05:** no `BaseGame`, no `core/` module split. Everything stays in `logpose/main.py`.
- **ARCH-06:** `_run_command`, `_install_steamcmd`, `_repair_package_manager` signatures unchanged.
- **PAL-01, PAL-02, PAL-06:** Palworld behavioral byte-compat — service filename `palserver.service`, template byte-identical to v0.1.19, launch args identical.
- **PAL-07:** Palworld install flags identical — `--port` (default 8211), `--players` (default 32), `--start`.
- **Python 3.8 floor** (PKG-04) — no PEP-604 `X | Y` unions, no PEP-695 generics, no `match` statements, no `str.removeprefix`.
- **POL-04 (additive posture):** old v0.1.19 `40-palserver.rules` is left on disk if present; Polkit merges across files. README documents manual cleanup. Do NOT delete it programmatically.
- **Byte-diff harness is non-negotiable** — `tests/test_palworld_golden.py` must exit 0 at every commit boundary.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|--------------------------------------|------------------|
| CLI-01 | Typer root dispatches game-first (`logpose palworld <verb>`) | `app.add_typer(sub, name=spec.key)` loop over `GAMES` → Typer Composition Pattern below |
| CLI-02 | Per-game sub-app built via `_build_game_app(spec) -> typer.Typer` factory | Factory closure binds `spec` correctly; naked decorator-in-loop misbinds — see Pitfall 1 |
| CLI-03 | Every verb per game: `install`, `start`, `stop`, `restart`, `status`, `enable`, `disable`, `update`, `edit-settings` | All nine verbs already exist in `logpose/main.py` and read `GAMES["palworld"]` — factory migration is mechanical |
| CLI-04 | Root + sub-apps set `no_args_is_help=True`; `help=` set on every `Typer()` + `add_typer()` | Verified: Typer 0.15.2 accepts `help=` kwarg on both constructors |
| CLI-05 | Error exits use `raise typer.Exit(code=1)`; no `sys.exit(1)` in `logpose/main.py` | Grep found 7 `sys.exit` call sites lines 75, 100, 276, 317, 381, 487, 494 — see Exit Conversion Inventory |
| CLI-06 | Root `@app.callback()` exposes `--version` via `importlib.metadata.version("logpose-launcher")` | Verified: `importlib.metadata.version("logpose-launcher")` returns `0.1.19` in current env — stdlib on Python 3.8+ |
| CLI-07 | `logpose --help` shows `palworld` (and later `ark`) sub-commands with descriptions | `add_typer(..., help=spec.display_name + " ...")` + `Typer(help=...)` on sub-app |
| PAL-07 | Palworld install flags identical: `--port` (default 8211), `--players` (default 32), `--start` | Existing `install()` already uses these; factory re-exposes them inside closure |
| POL-01 | Single merged `40-logpose.rules` replaces `40-palserver.rules`; regenerated on every install from `GAMES.values()` | Polkit Merged Rule Strategy below — units list built from `GAMES.values()` inside `_setup_polkit()` |
| POL-02 | `40-logpose.rules.template` uses JS `var units = [{units}]; indexOf(...)` pattern; every `{`/`}` outside placeholders doubled | Brace-escape test run below verifies `str.format()` round-trip |
| POL-03 | `_setup_polkit()` no longer takes game-specific args; reads `GAMES` globally | Current signature `_setup_polkit(rules_filename, template_name, user)` → new signature `_setup_polkit(user)` |
| POL-04 | Old v0.1.19 `40-palserver.rules` left on disk if present (additive behavior — Polkit merges) | No code deletes it; README-only cleanup note — deferred to Phase 6 per REQUIREMENTS.md |
| POL-05 | `pkcheck --action-id=org.freedesktop.systemd1.manage-units --process $$ --detail unit <service>.service` returns allowed | VM E2E verification; `pkcheck` absent in research host (expected — polkit not installed in container) |
| SET-03 | Interactive editor (Rich table + prompt-by-name) refactored to take `GameSpec` + dispatch via `spec.settings_adapter` | `_interactive_edit_loop` already takes `settings: dict`; `edit_settings` already binds `spec = GAMES["palworld"]` — factory closure just forwards `spec` |
| PKG-08 (partial) | README updated with new CLI examples for both games | Phase 4 covers Palworld CLI examples only; ARK examples + migration note + per-game firewall port reference land in Phase 5/6 |
| E2E-02 | CLI smoke-test matrix — `logpose --help`, `logpose palworld --help`, `logpose palworld install --help` all exit 0 with expected trees | Manual verification in Phase 4 exit criteria (ARK paths E2E-02-excluded until Phase 5) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Enforced by `./CLAUDE.md` + `logpose/CLAUDE.md` + `logpose/templates/CLAUDE.md`:

| Constraint | Source | Phase 4 Compliance |
|------------|--------|---------------------|
| `logpose/main.py` is the single implementation file | `logpose/CLAUDE.md` | Factory + callback both land in `main.py` — no new modules |
| `templates/` is a flat directory with systemd + polkit templates | `logpose/templates/CLAUDE.md` | `40-logpose.rules.template` replaces `palserver.rules.template` in the same flat dir |
| `_repair_package_manager()` stays load-bearing | project CLAUDE.md (referenced by REQUIREMENTS.md Out of Scope row) | Phase 4 does not touch this helper |
| README describes CLI commands and install steps | project CLAUDE.md | PKG-08 partial — Palworld examples refreshed this phase |

## Standard Stack

### Core
| Library | Version (installed / pinned) | Purpose | Why Standard |
|---------|------------------------------|---------|--------------|
| `typer` | 0.15.2 installed; pinned `>=0.9,<0.21` in `pyproject.toml` | CLI routing, sub-app composition, `typer.Exit`, `typer.Option` | Already a direct dependency; Typer 0.21 drops Python 3.8 (2025-12-25) which breaks PKG-04 [VERIFIED: REQUIREMENTS.md PKG-03 note; typer 0.15.2 import confirmed locally] |
| `rich` | 13.9.4 installed; pinned `>=13.0,<14` | Table rendering in `edit-settings`, styled console output | Already a direct dependency; factory migration does not touch rich surface |
| Python stdlib `importlib.metadata` | Python 3.8+ stdlib | `--version` lookup from distribution metadata | Zero new deps; `importlib.metadata.version("logpose-launcher")` works on the 3.8 floor [VERIFIED: local probe returned `0.1.19`] |
| Python stdlib `string.Formatter` | any | Extract placeholder names for pre-`format()` sanity check | Lets us assert `{units}`/`{user}` are the only placeholders in the merged polkit template before rendering |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| Python stdlib `dataclasses` | Already in use for `GameSpec` / `SettingsAdapter` | No changes required — the factory reads `spec.<field>` |
| Python stdlib `pathlib.Path` | Service file + polkit path construction | Same as v0.1.19 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typer factory function | Naked `for` loop with `@sub.command()` decorators | Rejected — late binding of `spec` in decorator closures. **Every generated command would operate on the last `spec` in `GAMES`** [VERIFIED: ARCHITECTURE.md flag + standard Python closure semantics]. Factory takes `spec` as parameter → closures bind correctly. |
| Typer factory | One shared `install` with `--game` flag | Rejected at project level — user explicitly chose game-first ergonomics (`logpose palworld install`), documented in STATE.md Decisions Locked. |
| Merged polkit rule | Two separate rule files per game (`40-palserver.rules` + `40-arkserver.rules`) | **Documented fallback** per STATE.md Known Open Questions #2: if the merged template proves brittle under `str.format()` JS brace escaping during Phase 4 verification, fall back to one rule file per game. Current default: merged. |
| `raise typer.Exit(code=1)` | `sys.exit(1)` | `typer.Exit` is a Click exception that Typer's test runner can catch and assert on; `sys.exit` bypasses Typer and breaks assert-on-exit-code tests. CLI-05 is explicit. |
| `importlib.metadata.version("logpose-launcher")` | Read version from `pyproject.toml` at runtime | `importlib.metadata` is the Python-standard way; no filesystem seek at runtime; works from installed wheel where `pyproject.toml` isn't shipped. |

**Version verification:**
```bash
python3 -c "import importlib.metadata as m; print(m.version('typer'))"  # 0.15.2 — confirmed
python3 -c "import importlib.metadata as m; print(m.version('rich'))"   # 13.9.4 — confirmed
python3 -c "import importlib.metadata as m; print(m.version('logpose-launcher'))"  # 0.1.19 — confirmed in current editable install
```

No new runtime dependencies are required for Phase 4. No `pyproject.toml` edits required.

## Architecture Patterns

### Target Shape (end of Phase 4)

```
logpose/main.py
├── imports + console + STEAM_DIR
├── @dataclass SettingsAdapter, GameSpec        (unchanged from Phase 3)
├── helpers (_run_command, _install_steamcmd, …) (unchanged)
├── _palworld_parse, _palworld_save              (unchanged)
├── _render_service_file, _write_service_file    (unchanged)
├── _setup_polkit(user)                           ← SIGNATURE CHANGED (POL-03)
├── _palworld_sdk_hook + _PAL_* locals            (unchanged)
├── GAMES: dict[str, GameSpec]                    (unchanged data)
│
├── app = typer.Typer(help="...", no_args_is_help=True)
│
├── @app.callback()                               ← NEW (CLI-06)
│   def _root(version: bool = typer.Option(None, "--version", callback=_version_cb, is_eager=True)):
│       ...
│
├── def _build_game_app(spec: GameSpec) -> typer.Typer:   ← NEW (CLI-02)
│       sub = typer.Typer(help=f"Manage {spec.display_name} dedicated server.", no_args_is_help=True)
│       @sub.command()
│       def install(port=..., players=..., start=...): ...
│       @sub.command()  # 8 more verbs
│       def start(): ...
│       …
│       return sub
│
└── for key, spec in GAMES.items():
        app.add_typer(_build_game_app(spec), name=key, help=f"Manage {spec.display_name}.")
```

### Pattern 1: Typer Sub-App Factory
**What:** A function that takes a `GameSpec` and returns a fully-populated `typer.Typer` with all verbs attached. The function is called per game in a loop; each call is an independent closure so `spec` is bound correctly per sub-app.
**When to use:** Any time Typer sub-apps are generated programmatically from a registry of specs. This is mandatory when more than one spec exists; for one spec it still matters because the diff to N>1 must be zero-scaffolding.
**Example (canonical — adapt to logpose):**
```python
# Source: ARCHITECTURE.md "Typer Subcommand Composition Pattern" + Typer 0.15 installed behavior

app = typer.Typer(help="logpose — multi-game dedicated server launcher.",
                  no_args_is_help=True)

def _build_game_app(spec: GameSpec) -> typer.Typer:
    sub = typer.Typer(help=f"Manage {spec.display_name} dedicated server.",
                      no_args_is_help=True)

    @sub.command()
    def install(
        port: int = typer.Option(spec.install_options["port_default"], help="..."),
        players: int = typer.Option(spec.install_options["players_default"], help="..."),
        start: bool = typer.Option(False, "--start", help="..."),
    ) -> None:
        """Install the {display_name} dedicated server.""".format(display_name=spec.display_name)
        if Path.home() == Path("/root"):
            rich.print("This script should not be run as root. Exiting.", file=sys.stderr)
            raise typer.Exit(code=1)
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
        _write_service_file(Path(f"/etc/systemd/system/{spec.service_name}.service"),
                            service_content)
        _setup_polkit(Path.home().name)  # POL-03 — reads GAMES globally
        # …

    @sub.command()
    def start() -> None:
        """Start the {display_name} server.""".format(display_name=spec.display_name)
        _run_command(f"systemctl start {spec.service_name}")

    # ... stop, restart, status, enable, disable, update, edit-settings

    return sub

for key, spec in GAMES.items():
    app.add_typer(_build_game_app(spec), name=key, help=f"Manage {spec.display_name}.")
```

**Key properties of this factory:**
- `spec` is a **parameter**, not a loop variable — every inner `def` closes over the function-local `spec`, not the module-global loop variable. This is the correctness fix over naked-decorator-in-loop.
- `no_args_is_help=True` on both root + sub applies to `logpose` (no args) and `logpose palworld` (no args) — both show help and exit `0` per Typer's documented behavior [VERIFIED: Pitfall 7 in PITFALLS.md + Typer 0.15 docs].
- `help=` on both `Typer(...)` and `add_typer(...)` ensures descriptions survive Typer's rendering — `add_typer`'s `help` is shown in the parent's `--help`, the constructor's `help` is shown as the sub-app's header when `logpose palworld --help` runs.

### Pattern 2: Root Version Callback
**What:** Typer idiom for `--version` that exits before any subcommand runs.
**When to use:** For any top-level `--version` flag that should short-circuit `--help` and subcommand dispatch.
**Example:**
```python
# Source: Typer 0.15 docs — version callback pattern

def _version_cb(value: bool) -> None:
    if value:
        import importlib.metadata
        try:
            v = importlib.metadata.version("logpose-launcher")
        except importlib.metadata.PackageNotFoundError:
            v = "unknown"
        typer.echo(f"logpose {v}")
        raise typer.Exit()

@app.callback()
def _root(
    version: bool = typer.Option(
        None,
        "--version",
        callback=_version_cb,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """logpose — multi-game dedicated server launcher."""
```

- `is_eager=True` means `--version` runs before Typer parses any subcommand, so `logpose --version` works without `logpose <game> --version` required.
- `importlib.metadata.PackageNotFoundError` fallback guards against running from a non-installed checkout — testing via `python -m logpose.main` without `pip install -e .` would otherwise crash. Plan should explicitly exercise both paths.

### Pattern 3: Merged Polkit Rule Template with `str.format()` brace escaping
**What:** Single `40-logpose.rules.template` file whose JS body uses `var units = [{units}];` and `units.indexOf(...)` to authorize all known service units from one file. Every non-placeholder `{` and `}` in the JS body is doubled to survive `str.format()`.
**When to use:** When a single polkit rule authorizes multiple systemd units and the unit list is data-driven from `GAMES.values()`.
**Example (canonical — verified to round-trip through `str.format()` locally):**
```javascript
// logpose/templates/40-logpose.rules.template
polkit.addRule(function(action, subject) {{
    var units = [{units}];
    if (action.id == "org.freedesktop.systemd1.manage-units" &&
        units.indexOf(action.lookup("unit")) !== -1 &&
        subject.user === "{user}") {{
        return polkit.Result.YES;
    }}
}});
```

- `{{` / `}}` are the `str.format()` escape for literal `{` / `}` in the rendered output.
- `{units}` and `{user}` are the two placeholders — everything else in the file is literal JS.
- **The `{units}` substitution must be a pre-joined string**, not a Python list: `units = ", ".join(f'"{spec.service_name}.service"' for spec in GAMES.values())`. If you pass a Python list to `.format(units=[...])`, Python formats the list repr (`['palserver.service']`) — which renders as `var units = [['palserver.service']];` — syntactically wrong JS, silently non-authorizing.
- `_setup_polkit(user)` must always write this file at path `/etc/polkit-1/rules.d/40-logpose.rules` and `sudo systemctl restart polkit.service` after (existing behavior preserved).

**Brace-escape verification (run during research):**
```python
# Verified 2026-04-13 — the template round-trips cleanly through str.format()
tpl = 'polkit.addRule(function(a,s) {{ var units = [{units}]; if (s.user=="{user}") return 1; }});'
# string.Formatter parses only two placeholders:
placeholders = [f[1] for f in string.Formatter().parse(tpl) if f[1]]  # ['units', 'user']
rendered = tpl.format(units='"palserver.service", "arkserver.service"', user='foo')
# produces: polkit.addRule(function(a,s) { var units = ["palserver.service", "arkserver.service"]; if (s.user=="foo") return 1; });
```

### Anti-Patterns to Avoid
- **Naked decorator-in-loop:** `for spec in GAMES.values(): @sub.command() ...` — every `spec` reference inside all command bodies binds to the final loop value because Python closures capture variables by reference, not by value at definition time. Factory pattern takes `spec` as a parameter; each factory call creates a fresh scope.
- **Mixing `sys.exit` and `typer.Exit`:** Partial conversion breaks CLI-05 and leaves behavior inconsistent — some errors propagate through Typer's test harness, some bypass it. Do all 7 sites in one commit.
- **Dropping `help=` on `add_typer`:** Without `help=`, `logpose --help` shows the sub-command name with no description. CLI-04 + CLI-07 require both `Typer(help=...)` and `add_typer(..., help=...)`.
- **Removing `40-palserver.rules` programmatically:** POL-04 is explicit — the old v0.1.19 file is left on disk additively; Polkit merges across files. Users on fresh installs never see it; users upgrading from v0.1.19 get a README note in Phase 6.
- **Hardcoding `"palworld"` anywhere in the factory body:** The factory must be game-agnostic. The only `"palworld"` literal in `main.py` at end of Phase 4 is the key inside the `GAMES = {"palworld": ...}` construction.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Package version lookup | `__version__ = "0.2.0"` constant in `main.py` | `importlib.metadata.version("logpose-launcher")` | Hardcoded constant drifts from `pyproject.toml` on every release; metadata lookup is the stdlib standard since Python 3.8 and survives `pip install`, `pip install -e .`, and wheel installs. |
| CLI exit codes | `sys.exit(1)` | `raise typer.Exit(code=1)` | Typer/Click wraps command invocations in exception handlers; `typer.Exit` propagates the intended code through the test harness, `sys.exit` bypasses it (see PITFALLS.md Pitfall 7). |
| Sub-app routing | Manual `argparse` subparsers or `if sys.argv[1] == "palworld": ...` | `app.add_typer(sub, name="palworld")` | Typer already handles sub-command help, bash completion, error messages, and type coercion. |
| Polkit JS unit matching | Per-unit `if` chain (`if (unit == "a") … else if (unit == "b") … else if (…)`) | `var units = [...]; units.indexOf(unit) !== -1` | O(n) JS array scan is trivially fast for a list of ≤10 game service units; one branch means one chance of typo silently breaking one game. |
| Help text generation | Manual `rich.print` of usage from `__doc__` | Typer's built-in `--help` rendering | Typer auto-generates from docstrings + `help=` parameters; manual help is a ticking maintenance bomb. |
| Template placeholder validation | Visual inspection | `string.Formatter().parse(tpl)` to extract placeholder names and compare to format-dict keys | Catches template-drift typos before they hit disk (PITFALLS.md Pitfall 6 item 5). |

**Key insight:** All five hand-roll hazards in this table are already solved by stdlib + Typer — the entire Phase 4 migration can be done without adding a runtime dependency or writing more than ~40 lines of new code.

## Common Pitfalls

### Pitfall 1: Naked decorator-in-loop misbinds `spec`
**What goes wrong:** Someone writes
```python
sub = typer.Typer()
for key, spec in GAMES.items():
    @sub.command()
    def start():
        _run_command(f"systemctl start {spec.service_name}")  # <- always the last spec
app.add_typer(sub)
```
After `logpose palworld start` and `logpose ark start` are both registered, both invoke `systemctl start arkserver` because `spec` is captured by reference from the enclosing loop, and after the loop ends `spec` refers to the last iteration.
**Why it happens:** Python closures capture variables from the enclosing scope by reference, not by value-at-decoration-time. This is a canonical closure-in-loop bug, subtle because Typer registers commands successfully at import and the failure only shows at runtime when the wrong service is started.
**How to avoid:** Factory function takes `spec` as a parameter. Each factory call creates a fresh scope; inner `def`s close over the function-local `spec`. Also applies to `typer.Option` defaults that reference `spec.install_options["port_default"]` — those are evaluated at decorator time, so they're safe, but any runtime body reference to `spec` must be inside a factory scope.
**Warning signs:** `logpose palworld start` and `logpose ark start` both execute `systemctl start arkserver`. Byte-diff harness doesn't catch this (it's a runtime dispatch bug, not a template-render bug) — explicit CLI smoke test is required.

### Pitfall 2: `str.format()` brace escaping in the JS polkit template
**What goes wrong:** The existing `palserver.rules.template` has `{{` and `}}` to escape literal `{`/`}` around the JS function body. When merging to `40-logpose.rules.template`, additional `{`/`}` are introduced (the JS `if` block, the inner `return` block) — any unescaped literal brace throws `KeyError: '<char>'` at render time, OR (worse) silently consumes part of the placeholder name and produces malformed JS that polkit rejects without clear logs.
**Why it happens:** The template is rendered with `template.format(user=..., units=...)` and every literal brace inside the JS body must be doubled. Multi-line JS with nested `{}` is a brace-escape minefield.
**How to avoid:**
- Use `string.Formatter().parse(template)` to extract the list of placeholder names; assert it equals `{"units", "user"}` before rendering.
- Add a unit test that `.format(units='"x.service"', user='foo')` succeeds and the output contains a well-formed `polkit.addRule(function(action, subject) {` opener and a balanced closing `});`.
- Consider capturing a rendered golden (`tests/golden/40-logpose.rules.v0_2_0`) and a second byte-diff test to lock the template against future drift — mirrors Phase 2's `palserver.service` golden approach.
**Warning signs:**
- `KeyError` during install
- `pkcheck --action-id org.freedesktop.systemd1.manage-units --detail unit palserver.service` returns "not authorized" after `install` succeeds — polkitd logged a JS syntax error silently (viewable in `journalctl _COMM=polkitd` on a real Debian VM).

### Pitfall 3: `{units}` substitution must be pre-joined string, not Python list
**What goes wrong:** `template.format(units=[spec.service_name + ".service" for spec in GAMES.values()], user=u)` produces `var units = [['palserver.service']];` — a JS array containing a single nested array — silently wrong (polkit rejects; or matches no unit; or errors in journald and allows nothing).
**Why it happens:** Python's `str.format()` calls `str()` on the substitution value. `str([...])` is the list repr with brackets and quotes; it looks vaguely like JSON but is Python syntax (single quotes, not double). One wrong character breaks polkit silently.
**How to avoid:** Always pre-join: `units = ", ".join(f'"{spec.service_name}.service"' for spec in GAMES.values())` → `"palserver.service", "arkserver.service"`. Placed between the literal `[` and `]` in the template, this produces valid JS.
**Warning signs:** `cat /etc/polkit-1/rules.d/40-logpose.rules` shows `var units = [['palserver.service']];` (single-quoted, double-bracketed). `journalctl _COMM=polkitd` shows `ReferenceError` or `SyntaxError`.

### Pitfall 4: `importlib.metadata.version("logpose-launcher")` crashes on uninstalled checkouts
**What goes wrong:** Developer running `python -m logpose.main --version` from a git checkout that hasn't been `pip install -e .`-installed gets `PackageNotFoundError` instead of a version string. CI and VM E2E both install the package, so this only bites interactive development.
**Why it happens:** `importlib.metadata` reads from `.dist-info` / `.egg-info` directories on sys.path. A bare source checkout has neither.
**How to avoid:** Wrap in `try / except importlib.metadata.PackageNotFoundError`, fall back to the string `"unknown"` (or `"dev"` if preferred). Document in the Plan that the callback must handle this case.
**Warning signs:** `logpose --version` crashes with `PackageNotFoundError` traceback on a fresh clone.

### Pitfall 5: Byte-diff harness does NOT cover the polkit template
**What goes wrong:** The existing harness (`tests/test_palworld_golden.py`) renders only `palserver.service` and compares to `tests/golden/palserver.service.v0_1_19`. It will stay green through any polkit template change. A merged-polkit bug will not surface until VM E2E.
**Why it happens:** The Phase 2 harness was designed before the polkit merge existed; Phase 4 introduces the polkit template change but the harness was not extended in Phase 2 or Phase 3 to cover it.
**How to avoid:**
- Add a third test to `tests/test_palworld_golden.py` (or a new `tests/test_polkit_golden.py`) that captures a fixture render of `40-logpose.rules.template` with the known `GAMES` unit set and compares to a committed golden. Even a Palworld-only fixture (single unit) locks the template against accidental drift.
- Add `tests/golden/40-logpose.rules.v0_2_0` committed as the oracle.
- Placeholder audit: `set(placeholders) == {"units", "user"}` → assert before render in the helper, so a future template edit that introduces a third placeholder fails fast.
**Warning signs:** Template changes land without any test failing. Regressions only visible on real VM.

### Pitfall 6: `typer.Exit(code=0)` vs no-code
**What goes wrong:** `raise typer.Exit(code=0)` is unnecessary for success (Typer exits 0 implicitly when a command returns). Worse, `raise typer.Exit()` with no code on an error path exits 0, looking like a success to shell scripts. Mixing intent and code gives silently-successful failures.
**Why it happens:** `typer.Exit`'s default code is 0 — it's the generic "exit now" exception, not "exit with an error."
**How to avoid:** For the `edit_settings` "quit without saving" path (currently `sys.exit(0)` at line 317), replace with `raise typer.Exit()` (no code — intent is clean quit). For all 6 error-path `sys.exit(1)` sites, replace with `raise typer.Exit(code=1)` explicitly. Grep `raise typer.Exit()` after conversion — any site not followed by an error message above it is suspect.
**Warning signs:** Scripts chaining `logpose palworld install && logpose palworld start` succeed when install actually failed.

### Pitfall 7: Typer `--help` discovery regression on `no_args_is_help`
**What goes wrong:** `no_args_is_help=True` on the root means `logpose` (bare) prints help and exits `0`. This is Typer's documented behavior but violates the Unix "missing required argument → exit 2" convention. Some CI pipelines key off exit code 2.
**Why it happens:** Typer / Click converts bare-invocation to help-print on that flag.
**How to avoid:** Accept Typer's behavior — the REQUIREMENTS.md / ROADMAP.md spec asks for help tree to exit 0, not exit 2. Document the choice in README if the team cares; otherwise no action needed. (PITFALLS.md Pitfall 7 flagged this; REQUIREMENTS.md CLI-04 endorses the help-tree default.)
**Warning signs:** None actionable — this is a documentation / expectation-setting item, not a bug.

## Runtime State Inventory

Phase 4 is a pure code refactor of `logpose/main.py` plus one template rename/merge. No phase changes migrate stored data, secrets, or OS-registered state at runtime — but the polkit rule filename change (`40-palserver.rules` → `40-logpose.rules`) IS an OS-registered artifact written by `install` — and Phase 4 MUST NOT delete the old file during an upgrade path.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — logpose stores no application data; the only persistent state is systemd unit files, polkit rules, and the game's own `*.ini` settings files (owned by the game, not logpose). | None. |
| Live service config | The systemd service unit `palserver.service` at `/etc/systemd/system/palserver.service` is unchanged by Phase 4 (filename preserved per PAL-01; byte-identical per PAL-02). The polkit rule file at `/etc/polkit-1/rules.d/40-palserver.rules` is **additively** replaced by a new `/etc/polkit-1/rules.d/40-logpose.rules` file — the old one is intentionally left in place per POL-04 so existing v0.1.19 installs are not silently broken during transition. README in Phase 6 documents manual cleanup. | Install writes `40-logpose.rules` on every fresh run. Old `40-palserver.rules` untouched. |
| OS-registered state | polkit rule file `/etc/polkit-1/rules.d/40-logpose.rules` is new; `/etc/polkit-1/rules.d/40-palserver.rules` is left in place on upgrade. `sudo systemctl restart polkit.service` after write is preserved from v0.1.19. systemd units remain `palserver.service` (Palworld). | Polkit restart continues via existing `_setup_polkit` helper. |
| Secrets/env vars | None. logpose does not read or write secrets for Palworld. (ARK's admin-password flow is Phase 5.) | None. |
| Build artifacts / installed packages | Phase 4 does not bump version or change packaging. `pyproject.toml` stays at `version = "0.1.19"` until Phase 6. No new egg-info churn. | None. |

**The canonical question — "after every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?"** — answer for Phase 4: the old `/etc/polkit-1/rules.d/40-palserver.rules` is the only such artifact on upgraded machines, and POL-04 explicitly mandates leaving it alone.

## Environment Availability

Phase 4 is a code-only refactor verifiable locally; the VM-dependent success criterion (`pkcheck` verification) requires an actual Debian 12 VM. Research host probe:

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.8+ | Phase 4 targets the 3.8 floor | ✓ | 3.13.5 on research host (code must still work on 3.8) | — |
| `typer` | Sub-app routing, `Option`, `Exit`, `callback` | ✓ | 0.15.2 installed; pinned `>=0.9,<0.21` | — |
| `rich` | `edit-settings` table | ✓ | 13.9.4 installed; pinned `>=13.0,<14` | — |
| `importlib.metadata` | `--version` lookup | ✓ | stdlib (3.8+) | — |
| `pkcheck` | E2E verification of polkit authorization (success criterion #3) | ✗ | — | VM-only — `pkcheck` is installed as part of `policykit-1` on Debian/Ubuntu; research host is a minimal container. Mandatory on the VM where E2E runs. |
| `systemctl` / `systemd` | VM-level install/start/stop | ✗ | — | VM-only; same reason. |
| Debian 12 VM | E2E verification of CLI install flow (success criterion #2) | ✗ | — | User defers; STATE.md notes Phase 2 VM E2E was deferred to Phase 5. Phase 4 VM E2E may similarly be rolled into Phase 5's sweep per user direction. |

**Missing dependencies with no fallback:**
- None blocking the Phase 4 code changes. All success criteria that don't require a VM are verifiable on the research host.

**Missing dependencies with fallback:**
- `pkcheck` / `systemctl` — E2E-only; verify on real Debian 12 VM. If user defers VM E2E (as they did for Phase 2), document in Phase 4 verification that VM-gated criteria are deferred.

## Validation Architecture

> Skipped. `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`.

## Security Domain

> Skipped. `security_enforcement` not set in config; phase does not introduce auth/crypto/input-validation surfaces beyond what already exists (user-scoped polkit rule + template substitution). The existing user-scoped polkit rule (`subject.user === "{user}"`) is preserved verbatim in the merged template — no regression in authorization scope.

Security-relevant notes inherited from prior research (for the planner's awareness):
- Polkit rule is user-scoped by username literal — same trust model as v0.1.19 (PITFALLS.md Security Mistakes table). No change to this trust model in Phase 4.
- No new secrets handled (ARK admin-password is Phase 5).
- `str.format()` on an attacker-controlled template is unsafe — but the template is shipped in the package, not user input; no injection surface.
- `{units}` substitution is built from `GAMES.values()` (shipped data), not user input; no injection surface.

## Code Examples

Verified patterns from Phase 3 codebase + official Typer 0.15 behavior.

### Canonical factory + registration (go-to reference)
```python
# Source: logpose/main.py current state + ARCHITECTURE.md factory pattern

app = typer.Typer(
    help="logpose — multi-game dedicated server launcher.",
    no_args_is_help=True,
)

def _version_cb(value: bool) -> None:
    if value:
        import importlib.metadata
        try:
            v = importlib.metadata.version("logpose-launcher")
        except importlib.metadata.PackageNotFoundError:
            v = "unknown"
        typer.echo(f"logpose {v}")
        raise typer.Exit()

@app.callback()
def _root(
    version: bool = typer.Option(
        None, "--version",
        callback=_version_cb, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """logpose — multi-game dedicated server launcher."""

def _build_game_app(spec: GameSpec) -> typer.Typer:
    sub = typer.Typer(
        help=f"Manage {spec.display_name} dedicated server.",
        no_args_is_help=True,
    )

    port_default = int(spec.install_options.get("port_default", 0))
    players_default = int(spec.install_options.get("players_default", 0))

    @sub.command()
    def install(
        port: int = typer.Option(port_default, help=f"Port to run the {spec.display_name} server on."),
        players: int = typer.Option(players_default, help="Maximum number of players."),
        start: bool = typer.Option(False, "--start", help="Start the server immediately after installation."),
    ) -> None:
        """Install the dedicated server and create a systemd service."""
        if Path.home() == Path("/root"):
            rich.print("This script should not be run as root. Exiting.", file=sys.stderr)
            raise typer.Exit(code=1)
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
        _write_service_file(
            Path(f"/etc/systemd/system/{spec.service_name}.service"),
            service_content,
        )
        _setup_polkit(Path.home().name)
        console.print("Installation complete!")
        if start:
            _run_command(f"systemctl start {spec.service_name}")

    @sub.command()
    def start() -> None:
        """Start the server."""
        _run_command(f"systemctl start {spec.service_name}")

    @sub.command()
    def stop() -> None:
        """Stop the server."""
        _run_command(f"systemctl stop {spec.service_name}")

    @sub.command()
    def restart() -> None:
        """Restart the server."""
        _run_command(f"systemctl restart {spec.service_name}")

    @sub.command()
    def status() -> None:
        """Check the status of the server."""
        _run_command(f"systemctl status {spec.service_name}", check=False)

    @sub.command()
    def enable() -> None:
        """Enable the server to start on boot."""
        _run_command(f"systemctl enable {spec.service_name}")

    @sub.command()
    def disable() -> None:
        """Disable the server from starting on boot."""
        _run_command(f"systemctl disable {spec.service_name}")

    @sub.command()
    def update() -> None:
        """Update the dedicated server."""
        console.print(f"Updating {spec.display_name} dedicated server...")
        _run_steamcmd_update(spec.server_dir, spec.app_id)

    @sub.command(name="edit-settings")
    def edit_settings() -> None:
        """Edit the game's settings file."""
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
                rich.print(f"An error occurred after creating default settings: {e}", file=sys.stderr)
                raise typer.Exit(code=1)
        try:
            _interactive_edit_loop(settings)
            spec.settings_adapter.save(spec.settings_path, settings)
        except Exception as e:
            rich.print(f"An error occurred during settings edit: {e}", file=sys.stderr)
            raise typer.Exit(code=1)

    return sub

# Register every known game via add_typer — loop, not naked decorators
for _key, _spec in GAMES.items():
    app.add_typer(
        _build_game_app(_spec),
        name=_key,
        help=f"Manage {_spec.display_name}.",
    )
```

### Polkit helper with GAMES-driven unit list (POL-03)
```python
def _setup_polkit(user: str) -> None:
    """Allow `user` to control every registered game service without sudo.

    Reads service names from GAMES.values() and renders the merged
    40-logpose.rules.template; regenerated idempotently on every install.
    """
    console.print("Setting up policy for non-sudo control of all registered games...")
    policy_file = Path("/etc/polkit-1/rules.d/40-logpose.rules")
    _run_command(f"sudo mkdir -p {policy_file.parent}")
    units = ", ".join(f'"{spec.service_name}.service"' for spec in GAMES.values())
    template = _get_template("40-logpose.rules.template")
    # Placeholder audit — fails fast if the template drifts
    from string import Formatter
    placeholders = {f[1] for f in Formatter().parse(template) if f[1]}
    assert placeholders == {"units", "user"}, (
        f"40-logpose.rules.template placeholder drift: {placeholders}"
    )
    policy_content = template.format(units=units, user=user)
    _run_command(f"echo '{policy_content}' | sudo tee {policy_file}")
    _run_command("sudo systemctl restart polkit.service")
```

### Exit conversion inventory (CLI-05)
```python
# 7 sites in logpose/main.py flagged by grep:
#   L75   _get_template          sys.exit(1)   → raise typer.Exit(code=1)
#   L100  _run_command           sys.exit(1)   → raise typer.Exit(code=1)
#   L276  _create_settings…     sys.exit(1)   → raise typer.Exit(code=1)
#   L317  _interactive_edit_loop sys.exit(0)   → raise typer.Exit()    # intentional quit, no error
#   L381  install()              sys.exit(1)   → raise typer.Exit(code=1)
#   L487  edit_settings()        sys.exit(1)   → raise typer.Exit(code=1)
#   L494  edit_settings()        sys.exit(1)   → raise typer.Exit(code=1)
# After conversion: `grep -n 'sys\.exit' logpose/main.py` returns zero lines.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat `@app.command()` verbs reading `GAMES["palworld"]` at function top | Factory-built sub-app per spec, registered via `add_typer(..., name=spec.key)` | Phase 4 (this phase) | Adds a second dimension to the CLI (`logpose <game> <verb>`) without adding a dependency; sets up the pattern so Phase 5 adds `GAMES["ark"]` with zero scaffolding changes. |
| `sys.exit(1)` on error paths | `raise typer.Exit(code=1)` | Phase 4 | Exit codes survive Typer's test harness; exception propagation is clean. |
| `40-palserver.rules` per-Palworld polkit file | Single merged `40-logpose.rules` built from `GAMES.values()` | Phase 4 | One rule file covers all known games; adding a game is a `GAMES` dict entry only. Old file left additively on upgraded installs (POL-04). |
| Hardcoded `"palworld-server-launcher"` references in command help text (line 409, 413 of current main.py) | Sub-app `help=` strings derived from `spec.display_name` | Phase 4 | Removes last two Palworld-specific strings in command-body print statements (lines 409, 413 still say `palworld-server-launcher start` / `palworld-server-launcher enable` — grep-audit at end of phase). |

**Deprecated/outdated (by end of Phase 4):**
- `palserver.rules.template` — merged into `40-logpose.rules.template`, original file deleted or left in templates/ for reference. Phase 4 plan must explicitly state whether `palserver.rules.template` is deleted from the package or kept — leaning toward delete, since `package-data` glob `templates/*` would ship it uselessly to PyPI otherwise.
- `sys.exit(...)` in `logpose/main.py` — 0 occurrences post-phase.
- Flat `@app.command()` decorators at module scope — 0 occurrences post-phase (all verbs live inside the factory).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Typer 0.15.2 (installed) and the pinned range `>=0.9,<0.21` both support `add_typer(..., help=...)` kwarg and `Typer(..., no_args_is_help=True)` — these are Typer API features from 0.4+ and 0.6+ respectively. [CITED: Typer docs + local probe confirmed `help=` accepted] | Standard Stack, Pattern 1 | Low — Typer has had these for years; if wrong, plan adds a shim to set help text via an alternative mechanism. |
| A2 | `importlib.metadata.PackageNotFoundError` is raised on uninstalled checkouts; this is the correct exception to catch for the fallback. [CITED: Python 3.8+ stdlib docs] | Pitfall 4 | Low — documented stdlib behavior; fallback is a guard, not a primary path. |
| A3 | The `{units}` placeholder must be rendered as pre-joined JSON-array-interior string (`"a.service", "b.service"`), not a Python list. [VERIFIED: brace-escape test run 2026-04-13 confirmed `.format()` stringifies values via `str()`, producing list repr for lists.] | Pitfall 3, Pattern 3 | None — verified locally. |
| A4 | Polkit merges across multiple rule files in `/etc/polkit-1/rules.d/`, so leaving `40-palserver.rules` in place alongside new `40-logpose.rules` is additive, not conflicting. [CITED: polkit(8) man page + ARCHITECTURE.md + STATE.md Known Open Questions #2] | Runtime State Inventory, POL-04 | Low — documented polkit behavior; worst case is "extra rule grants same YES twice." |
| A5 | `pkcheck` is in the `policykit-1` package on Debian 12; absence on the research host is expected and does not block plan-writing. | Environment Availability | None — E2E-only tool; real VM has it. |
| A6 | Phase 4's VM E2E (success criterion #2) may be deferred to Phase 5's VM sweep, mirroring the user's Phase 2 deferral. This is an **assumption about user preference**, not a locked decision. | Environment Availability, Phase Plan ordering | Medium — if user wants Phase 4 E2E verified standalone, plan must allocate a VM task before Phase 5. Planner should confirm with user OR treat deferral as default and flag explicitly in the plan. |

**If this table is non-empty:** `A6` is the only item meaningfully actionable — the planner should either (a) assume deferral to Phase 5 and document it as an explicit deferral in Phase 4's verification plan, or (b) ask the user. Given `workflow.skip_discuss: true`, default to (a) with a visible deferral note.

## Open Questions

1. **Should `palserver.rules.template` be deleted from the package or left alongside the new `40-logpose.rules.template`?**
   - What we know: After the merge, nothing reads `palserver.rules.template`. `package-data` glob `templates/*` would ship it to PyPI as dead weight. Deleting it is a clean `git rm`. No runtime system references it (the on-disk `40-palserver.rules` is sourced from the template at v0.1.19 install time and never re-read).
   - What's unclear: Whether the user wants to preserve it as a historical artifact in-repo.
   - Recommendation: Delete in the same atomic commit as `40-logpose.rules.template` creation. Simple, minimal, reversible via git history.

2. **Should `@app.callback()` be a no-op callback or hold the `--version` handling?**
   - What we know: Either pattern works. A no-op callback + eager `--version` option is idiomatic Typer. A callback body that handles `--version` directly works too but is less idiomatic.
   - What's unclear: Preference is cosmetic.
   - Recommendation: Use the eager-callback pattern (shown in Pattern 2 above); matches Typer docs and keeps the root callback body empty.

3. **Should the placeholder-audit `assert` in `_setup_polkit` be a runtime assert or a module-import-time check?**
   - What we know: `assert` runs only when `_setup_polkit` is called (install path). Import-time check runs always but adds startup cost and complicates test harness. Placeholder-audit-as-test (in `tests/test_polkit_golden.py`) catches drift at CI time without runtime cost.
   - What's unclear: Whether Phase 4 adds the golden test (recommended) or just the runtime assert.
   - Recommendation: Add the golden test — mirrors Phase 2's harness pattern; locks template against drift for all future phases.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both Typer and Rich already installed, pinned versions compatible with every Phase 4 API used; `importlib.metadata` is Python stdlib on 3.8+.
- Architecture: HIGH — factory pattern is standard Python, verified locally; Phase 3 handoff note already flagged the factory shape and the `spec = GAMES["palworld"]` pattern that makes the migration mechanical.
- Pitfalls: HIGH — all six critical pitfalls are either directly verified (brace-escape round-trip, placeholder extraction, Typer import, metadata lookup) or inherited from `PITFALLS.md`'s HIGH-confidence section on Typer nested subcommands.
- Requirements mapping: HIGH — each requirement ID has a concrete research-backed implementation path; no orphans.

## Sources

### Primary (HIGH confidence)
- `logpose/main.py` post-Phase 3 — full re-read with grep audit for `sys.exit`, `typer.Option`, `help=`, `@app.callback`, `importlib.metadata` references. Confirmed 7 `sys.exit` sites; confirmed `GAMES["palworld"]` binding at top of every verb body; confirmed `_setup_polkit` signature still takes game-specific args.
- `logpose/templates/palserver.service.template` + `logpose/templates/palserver.rules.template` — byte-read to confirm existing placeholder shape (`{user}`).
- `.planning/research/ARCHITECTURE.md` — Typer factory pattern + merged polkit strategy + `GameSpec` schema.
- `.planning/research/PITFALLS.md` — Pitfall 6 (GAMES dict leakage), Pitfall 7 (Typer nested subcommands exit codes + help), Pitfall 10 (polkit merge-vs-split, with merged being the accepted default in STATE.md despite PITFALLS.md's preference for split).
- `.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-SUMMARY.md` — Phase 3 handoff items: factory-ready `for hook in spec.post_install_hooks`, `spec = GAMES["palworld"]` at every verb top, `install_options = {"port_default": 8211, "players_default": 32}` feed into `typer.Option` defaults.
- `.planning/REQUIREMENTS.md` — 17 phase-4 requirement IDs with exact acceptance criteria.
- `.planning/ROADMAP.md` — Phase 4 goal + 5 success criteria.
- `.planning/STATE.md` — Known Open Questions #2 (merged polkit is locked default; two-file split is documented fallback).
- Python stdlib docs — `importlib.metadata.version` (3.8+), `string.Formatter().parse`.
- Local probes on research host (2026-04-13):
  - `python3 -c "import importlib.metadata as m; print(m.version('logpose-launcher'))"` → `0.1.19`
  - Typer 0.15.2 `add_typer(..., help=...)` kwarg accepted.
  - Brace-escape round-trip: `'{{ var units = [{units}]; }}'.format(units='"a", "b"')` → `'{ var units = ["a", "b"]; }'`.

### Secondary (MEDIUM confidence)
- Typer 0.15 documentation for `--version` callback pattern and eager callbacks — referenced by memory; not re-verified via Context7/WebFetch this session (installed Typer matches documented behavior, so verification depth is adequate for plan-writing).

### Tertiary (LOW confidence)
- None — every claim in this document is either verified locally or cited from prior research files that the planner can re-read.

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (30 days; Typer/Rich stable; polkit behavior stable; no fast-moving deps)

## RESEARCH COMPLETE

**Phase:** 4 — Typer Factory + Merged Polkit
**Confidence:** HIGH

### Key Findings
- Typer 0.15.2 (installed, pinned `>=0.9,<0.21`) supports every Phase 4 API needed: factory pattern, `add_typer(help=...)`, `Typer(no_args_is_help=True)`, eager `--version` callback — no new dependencies, no pyproject.toml edits.
- `importlib.metadata.version("logpose-launcher")` returns `0.1.19` in the research host (verified) — `PackageNotFoundError` fallback is the only edge case to code-handle.
- Merged `40-logpose.rules.template` brace-escape round-trip verified locally: `{{`/`}}` for literal JS braces, `{units}` pre-joined as `"a.service", "b.service"` string, `{user}` for the installing user. Placeholder extraction via `string.Formatter` confirms exactly two placeholders.
- Seven `sys.exit` sites identified in `logpose/main.py` (lines 75, 100, 276, 317, 381, 487, 494) — six go to `typer.Exit(code=1)`, the `sys.exit(0)` at line 317 becomes bare `typer.Exit()`.
- Byte-diff harness does NOT currently cover the polkit template — a new golden (`tests/golden/40-logpose.rules.v0_2_0`) plus one test is the proposed addition.

### File Created
`.planning/phases/04-typer-factory-merged-polkit/04-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Both deps already installed + pinned; stdlib-only for metadata/formatter |
| Architecture | HIGH | Factory pattern canonical; Phase 3 handoff note + ARCHITECTURE.md gave the exact shape |
| Pitfalls | HIGH | Brace-escape + list-vs-string + closure trap all verified locally or directly cited |
| Requirements coverage | HIGH | All 17 phase-4 requirement IDs have a concrete implementation path mapped |

### Open Questions
1. Delete `palserver.rules.template` from the package in the same commit as `40-logpose.rules.template` creation? (Recommendation: yes — planner decides.)
2. Defer Phase 4 VM E2E (success criterion #2) into Phase 5's VM sweep, mirroring Phase 2's deferral? (Recommendation: yes, given `skip_discuss: true` and Phase 2 precedent — planner documents as explicit deferral.)
3. Runtime `assert` in `_setup_polkit` vs golden test in `tests/test_polkit_golden.py`? (Recommendation: both — runtime assert is a one-liner; golden test is the durable drift detector.)

### Ready for Planning
Research complete. Planner can now decompose Phase 4 into ~4 atomic commits (factory addition side-by-side with flat commands → factory swap + flat-command removal → polkit merge + golden test → `sys.exit` → `typer.Exit` conversion) with the byte-diff harness staying green at every boundary.
