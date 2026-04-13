---
phase: 04-typer-factory-merged-polkit
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - logpose/main.py
  - logpose/templates/40-logpose.rules.template
  - logpose/templates/CLAUDE.md
  - tests/test_palworld_golden.py
  - tests/golden/40-logpose.rules.v0_2_0
  - README.md
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 6 (5 source + 1 doc table)
**Status:** issues_found

## Summary

Phase 4 performs three coordinated refactors: (1) introduces a `_build_game_app` factory that closes over a `GameSpec` to produce per-game Typer sub-apps, (2) flips the CLI surface from flat verbs to `logpose <game> <verb>` via `add_typer`, (3) merges the per-game polkit rule into a single `40-logpose.rules` driven by `GAMES.values()`, and (4) finishes a `sys.exit -> typer.Exit` conversion across the module. A byte-diff golden test (`40-logpose.rules.v0_2_0`) was added and the existing palserver golden is preserved.

The factory design is clean — `spec` is captured as a closure variable, every inner verb references `spec.*`, and the v0.1.19 palserver golden still renders byte-identically (verified by inspection and by the existing `_render_service_file` test). No critical bugs, security regressions, or architectural red flags were found. Six issues below are either pre-existing smells now surfaced by the refactor or forward-looking risks for the ARK slot-in coming in Phase 5.

## Warnings

### WR-01: `assert` used for runtime template-drift check disappears under `python -O`

**File:** `logpose/main.py:222-225`
**Issue:** `_setup_polkit` audits the template's placeholder set with a bare `assert`:

```python
placeholders = {f[1] for f in Formatter().parse(template) if f[1]}
assert placeholders == {"units", "user"}, (
    f"40-logpose.rules.template placeholder drift: {placeholders}"
)
```

When the module is run under `python -O` (or a `PYTHONOPTIMIZE=1` environment), the `assert` is stripped at compile time and the audit becomes a no-op. A template that accidentally adds a `{foo}` placeholder would then reach `template.format(units=..., user=...)` and raise `KeyError: 'foo'` at install time — the exact "fails fast if the template drifts" guarantee the comment promises silently disappears in optimized mode.

This is a real concern on pipx/PyPI installs where users may set `PYTHONOPTIMIZE` via environment.

**Fix:** Replace the `assert` with an explicit raise so the check is always active:

```python
placeholders = {f[1] for f in Formatter().parse(template) if f[1]}
if placeholders != {"units", "user"}:
    raise RuntimeError(
        f"40-logpose.rules.template placeholder drift: {placeholders}"
    )
```

---

### WR-02: Shell-injection surface widened by templated `echo '...' | sudo tee`

**File:** `logpose/main.py:210, 227`
**Issue:** Both `_write_service_file` and `_setup_polkit` splat rendered template content into a shell one-liner:

```python
_run_command(f"echo '{content}' | sudo tee {service_file}")
_run_command(f"echo '{policy_content}' | sudo tee {policy_file}")
```

`_run_command` runs with `shell=True`. Today's input is safe because the v0.1.19 systemd template and the new polkit template contain no single-quote characters, and the substituted values (`user=Path.home().name`, `port`/`players` as ints, `service_name` from `GameSpec`) are not user-controlled. However, this pattern now feeds content that is assembled from `GAMES.values()` — any future game whose `service_name` contains a single quote, or a future template that adds a `'` in a comment or string literal, would produce a subtle shell-parse break (at best a failed install; at worst — though unlikely given the sudo-tee target — a command injection).

Phase 4 expanded the blast radius from one template to two, and Phase 5 will add a third unit (`arkserver.service`) to the polkit rendering. Harden now, while the templates are few.

**Fix:** Pipe via stdin instead of interpolating into the command string:

```python
def _write_via_sudo_tee(path: Path, content: str) -> None:
    console.print(f"Writing {path} via sudo tee...")
    proc = subprocess.run(
        ["sudo", "tee", str(path)],
        input=content,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        rich.print(f"sudo tee failed: {proc.stderr}", file=sys.stderr)
        raise typer.Exit(code=1)
```

Then call `_write_via_sudo_tee(service_file, content)` and `_write_via_sudo_tee(policy_file, policy_content)`. This removes the `shell=True` path entirely for these two writes.

## Info

### IN-01: `_setup_polkit` forward-references the module-level `GAMES` dict

**File:** `logpose/main.py:214-228`
**Issue:** `_setup_polkit` reads `GAMES.values()` (line 219) but is defined at line 214, ahead of `GAMES`'s assignment at line 356. Python resolves the name at call time so this works, but it introduces a hidden ordering coupling: the function is no longer a pure helper — it depends on module-global state that is constructed later in the file. Under testing or future refactors that call `_setup_polkit` during `GAMES` construction (e.g. a per-spec validation pass) this would raise `NameError`.

**Fix:** Make the dependency explicit by taking the spec list as a parameter:

```python
def _setup_polkit(user: str, specs: Iterable[GameSpec]) -> None:
    ...
    units = ", ".join(f'"{spec.service_name}.service"' for spec in specs)
```

Then the factory's `install` verb passes `GAMES.values()` at call site. This also makes the helper unit-testable without constructing the real GAMES dict.

---

### IN-02: `console.print(..., file=sys.stderr)` is silently wrong (pre-existing, now co-located with `typer.Exit` change)

**File:** `logpose/main.py:278-285`
**Issue:** `rich.console.Console.print` has no `file=` parameter (its signature is `(*objects, sep, end, style, ...)`). Passing `file=sys.stderr` folds `sys.stderr` into the `*objects` tuple and prints it as a literal — the error text goes to stdout, and the word `<_io.TextIOWrapper ...>` appears in the output. Phase 4 touched this block by replacing the adjacent `sys.exit(1)` with `raise typer.Exit(code=1)`, so the reviewer should be aware.

Surrounding `_create_settings_from_default` is the only place in the module that uses `console.print` for stderr — every other error path uses `rich.print(..., file=sys.stderr)`, which does accept `file`.

**Fix:** Change both calls to `rich.print`:

```python
rich.print(
    f"Default configuration file not found at {default_path}",
    file=sys.stderr,
)
rich.print(
    "Cannot create a new settings file. Please run `install` first or run the server once.",
    file=sys.stderr,
)
```

---

### IN-03: Factory silently accepts port/players defaults of 0 for games that omit `install_options`

**File:** `logpose/main.py:392-393`
**Issue:**

```python
port_default = int(spec.install_options.get("port_default", 0))
players_default = int(spec.install_options.get("players_default", 0))
```

If a future `GameSpec` forgets to set `port_default`/`players_default` (easy to miss — `install_options` is a free-form `dict[str, object]` with no schema), the CLI will advertise `--port 0 --players 0` as defaults and attempt to render a systemd unit with `-port=0 -players=0`. The server will either fail to bind or start in a broken state.

Palworld sets both, so nothing breaks today. But the factory exists specifically to host a second game in Phase 5 — this is the exact moment to turn the silent fallback into a loud one.

**Fix:** Either (a) make these keys required on `GameSpec` (promote them to named fields), or (b) raise when missing:

```python
try:
    port_default = int(spec.install_options["port_default"])
    players_default = int(spec.install_options["players_default"])
except KeyError as e:
    raise RuntimeError(
        f"GameSpec for {spec.key!r} missing required install_options key: {e}"
    ) from e
```

---

### IN-04: `_version_cb` uses `typer.echo` while the rest of the module uses `console.print`/`rich.print`

**File:** `logpose/main.py:508-517`
**Issue:** Minor stylistic inconsistency — every other user-facing output path in the module routes through `rich`/`Console`, which gives colored/styled output and respects NO_COLOR. `typer.echo(f"logpose {v}")` is plain `click.echo` and bypasses the Console. Not a bug; just drifts from the module's convention.

Also: the parameter is typed `bool` with default `None`. Typer accepts this idiom, but `Optional[bool]` would be more honest and would avoid a mypy-strict false positive if the project ever tightens type checking.

**Fix:**

```python
def _version_cb(value: Optional[bool]) -> None:
    if value:
        import importlib.metadata

        try:
            v = importlib.metadata.version("logpose-launcher")
        except importlib.metadata.PackageNotFoundError:
            v = "unknown"
        console.print(f"logpose {v}")
        raise typer.Exit()
```

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
