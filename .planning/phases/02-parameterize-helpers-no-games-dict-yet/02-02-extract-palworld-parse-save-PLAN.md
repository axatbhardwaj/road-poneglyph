---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - logpose/main.py
autonomous: true
requirements: [PAL-03, PAL-04, SET-01]
tags: [refactor, palworld, settings, python]

must_haves:
  truths:
    - "`_palworld_parse(path: Path) -> dict[str, str]` exists in `logpose/main.py` as a NAMED function whose body is byte-equivalent in logic to v0.1.19's `_parse_settings`, differing only in reading `path` instead of `PAL_SETTINGS_PATH`."
    - "`_palworld_save(path: Path, settings: dict[str, str]) -> None` exists in `logpose/main.py` as a NAMED function whose body is byte-equivalent in logic to v0.1.19's `_save_settings`, differing only in reading/writing `path` instead of `PAL_SETTINGS_PATH`."
    - "Both extracted functions carry a comment on their first body line: `# verbatim from v0.1.19 — PAL-03 invariant` (for parse) and `# verbatim from v0.1.19 — PAL-04 invariant` (for save)."
    - "The old `_parse_settings()` / `_save_settings(settings)` wrappers are DELETED (not kept as thin shims) — there is exactly one settings-parse function and one settings-save function in the module, and their names are the new ones."
    - "`edit_settings` command still works: calls `_palworld_parse(PAL_SETTINGS_PATH)` and `_palworld_save(PAL_SETTINGS_PATH, settings)` as the sole call site."
    - "`python -c 'import logpose.main; logpose.main._palworld_parse; logpose.main._palworld_save'` succeeds."
  artifacts:
    - path: "logpose/main.py"
      provides: "Named Palworld settings parse/save functions with explicit path parameter"
      exports: ["_palworld_parse", "_palworld_save"]
      contains: "def _palworld_parse(path: Path) -> dict[str, str]:"
  key_links:
    - from: "logpose/main.py::edit_settings"
      to: "logpose/main.py::_palworld_parse"
      via: "direct call with PAL_SETTINGS_PATH module global as argument"
      pattern: "_palworld_parse\\(PAL_SETTINGS_PATH\\)"
    - from: "logpose/main.py::edit_settings"
      to: "logpose/main.py::_palworld_save"
      via: "direct call with PAL_SETTINGS_PATH module global as argument"
      pattern: "_palworld_save\\(PAL_SETTINGS_PATH, settings\\)"
---

<objective>
Rename `_parse_settings` → `_palworld_parse(path)` and `_save_settings(settings)` → `_palworld_save(path, settings)` in `logpose/main.py`. Function bodies stay verbatim except for replacing the `PAL_SETTINGS_PATH` module-global read/write with the `path` parameter. Update the sole call site (the `edit_settings` command) to pass `PAL_SETTINGS_PATH` explicitly. The old names are DELETED, not kept as shims — minimum-diff means one name per function.

Purpose: Satisfies PAL-03 (`_palworld_parse` preserved verbatim) and PAL-04 (`_palworld_save` preserved verbatim) with `should_quote` still a local nested function. Preps SET-01 (Phase 2 prep) by decoupling settings I/O from the Palworld-specific module global — Phase 3 will swap the caller's argument from `PAL_SETTINGS_PATH` to `GAMES["palworld"].settings_path`, and helper bodies won't change.

Output: `logpose/main.py` post-extraction with verbatim-body discipline and a single call site updated. No other helpers touched — Plan 03 handles them.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md
@logpose/main.py

<interfaces>
<!-- Exact verbatim bodies to lift (from research section "OptionSettings Parser/Saver"). -->
<!-- ANY regex character change, ANY control-flow change, ANY error-message change violates PAL-03/PAL-04. -->

Current `_parse_settings` (logpose/main.py:191-201) — body to preserve:
```python
content = PAL_SETTINGS_PATH.read_text()     # path.read_text() after extract
match = re.search(r"OptionSettings=\((.*)\)", content)
if not match:
    raise ValueError("Could not find OptionSettings in PalWorldSettings.ini")

settings_str = match.group(1)
# This regex handles quoted strings and other values
settings_pairs = re.findall(r'(\w+)=(".*?"|[^,]+)', settings_str)
return {key: value.strip('"') for key, value in settings_pairs}
```

Current `_save_settings` (logpose/main.py:204-226) — body to preserve:
```python
content = PAL_SETTINGS_PATH.read_text()     # path.read_text() after extract

def should_quote(value: str) -> bool:
    if value.lower() in ("true", "false", "none"):
        return False
    try:
        float(value)
        return False
    except ValueError:
        return True

settings_str = ",".join(
    f'{key}="{value}"' if should_quote(value) else f"{key}={value}"
    for key, value in settings.items()
)

new_content = re.sub(
    r"OptionSettings=\(.*?\)", f"OptionSettings=({settings_str})", content
)
PAL_SETTINGS_PATH.write_text(new_content)   # path.write_text(new_content) after extract
console.print("Settings saved successfully.")
```

Current sole call site — `edit_settings` command (logpose/main.py:375-396):
```python
@app.command(name="edit-settings")
def edit_settings() -> None:
    """Edit the PalWorldSettings.ini file."""
    try:
        settings = _parse_settings()
    except (FileNotFoundError, ValueError):
        _create_settings_from_default()
        try:
            settings = _parse_settings()
        except (ValueError, FileNotFoundError) as e:
            rich.print(...); sys.exit(1)

    try:
        _interactive_edit_loop(settings)
        _save_settings(settings)
    except Exception as e:
        ...
```

Note: `_create_settings_from_default()` is a separate helper — it is NOT parameterized in this plan (Plan 03 handles it). This plan only touches parse/save.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Rename _parse_settings → _palworld_parse(path) with verbatim body</name>
  <files>logpose/main.py</files>
  <read_first>
    - logpose/main.py (the entire file — understand imports, module-globals, function order before editing)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Pitfall 3: `_palworld_parse` / `_palworld_save` body drift")
  </read_first>
  <behavior>
    - Calling `_palworld_parse(Path(...))` on a well-formed PalWorldSettings.ini returns a `dict[str, str]` mapping each `OptionSettings=(...)` key to its value with surrounding quotes stripped — identical behavior to pre-rename `_parse_settings()`.
    - Calling `_palworld_parse` on a file missing `OptionSettings=(...)` raises `ValueError("Could not find OptionSettings in PalWorldSettings.ini")` — error message byte-identical to v0.1.19.
    - Calling `_palworld_parse` on a non-existent path raises `FileNotFoundError` (from `path.read_text()`) — same as v0.1.19.
    - The old name `_parse_settings` no longer exists: `grep -q '^def _parse_settings' logpose/main.py` MUST fail after this task.
  </behavior>
  <action>
    In `logpose/main.py`, locate the function defined as `def _parse_settings() -> dict[str, str]:` (around line 191). Replace it with EXACTLY this function, preserving the regex strings CHARACTER-FOR-CHARACTER and the error message string BYTE-FOR-BYTE:

    ```python
    def _palworld_parse(path: Path) -> dict[str, str]:
        """Parses a Palworld PalWorldSettings.ini file."""
        # verbatim from v0.1.19 _parse_settings — PAL-03 invariant
        content = path.read_text()
        match = re.search(r"OptionSettings=\((.*)\)", content)
        if not match:
            raise ValueError("Could not find OptionSettings in PalWorldSettings.ini")

        settings_str = match.group(1)
        # This regex handles quoted strings and other values
        settings_pairs = re.findall(r'(\w+)=(".*?"|[^,]+)', settings_str)
        return {key: value.strip('"') for key, value in settings_pairs}
    ```

    Exact diff discipline:
    - The function name changes from `_parse_settings` to `_palworld_parse`.
    - The signature gains `path: Path`; the return type annotation stays `dict[str, str]`.
    - The docstring changes from `"""Parses the PalWorldSettings.ini file."""` to `"""Parses a Palworld PalWorldSettings.ini file."""` (this minor tweak gets re-aligned naturally when Phase 3 introduces the `_ark_parse` counterpart; if you prefer to keep the v0.1.19 docstring verbatim, that is also acceptable — byte-compat is about code, not docstrings).
    - A new comment line `# verbatim from v0.1.19 _parse_settings — PAL-03 invariant` appears as the first body line (BEFORE the `content = ...` assignment) to flag the function as load-bearing.
    - `PAL_SETTINGS_PATH.read_text()` becomes `path.read_text()` — THE only logical change.
    - The two regex string literals are COPIED CHARACTER-FOR-CHARACTER: `r"OptionSettings=\((.*)\)"` and `r'(\w+)=(".*?"|[^,]+)'`. Do not "simplify", do not swap quote types.
    - The error-message string is COPIED CHARACTER-FOR-CHARACTER: `"Could not find OptionSettings in PalWorldSettings.ini"`. Do not "fix" grammar.
    - The dict comprehension `{key: value.strip('"') for key, value in settings_pairs}` is copied verbatim.
    - `import re` is already at the top of the file — do not re-add.

    DO NOT touch the call site in this task — that is a separate edit in Task 3. After this task, `edit_settings` will still reference `_parse_settings()`, which will raise `NameError` on invocation. That is expected and fine; Task 3 fixes it in the same commit boundary or the one immediately after.

    Verify with a diff review: `git diff logpose/main.py` on the affected hunk should show ONLY: signature change, docstring tweak (if you chose to), added PAL-03 comment, and `PAL_SETTINGS_PATH` → `path` swap. No regex character changes, no whitespace reformatting inside the function body.
  </action>
  <verify>
    <automated>grep -q '^def _palworld_parse(path: Path) -> dict\[str, str\]:' logpose/main.py && ! grep -q '^def _parse_settings' logpose/main.py && python -c 'import ast, pathlib; ast.parse(pathlib.Path("logpose/main.py").read_text())'</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '^def _palworld_parse(path: Path) -> dict\[str, str\]:' logpose/main.py` returns `1`.
    - `grep -c '^def _parse_settings' logpose/main.py` returns `0` (old name deleted).
    - `grep -qF '# verbatim from v0.1.19' logpose/main.py` succeeds near `_palworld_parse`.
    - `grep -qF 'r"OptionSettings=\\((.*)\\)"' logpose/main.py` succeeds (outer capture regex preserved char-for-char).
    - `grep -qF "r'(\\w+)=(\".*?\"|[^,]+)'" logpose/main.py` succeeds (pairs regex preserved char-for-char).
    - `grep -qF 'Could not find OptionSettings in PalWorldSettings.ini' logpose/main.py` succeeds (error string verbatim).
    - `grep -q 'PAL_SETTINGS_PATH.read_text()' logpose/main.py` has AT MOST one match — and it is NOT inside the `_palworld_parse` body (Plan 03 / Task 3 removes it from `_palworld_save` too; this task only ensures `_palworld_parse` no longer reads `PAL_SETTINGS_PATH`).
    - `python -c 'import ast; ast.parse(open("logpose/main.py").read())'` exits 0 (file is syntactically valid).
  </acceptance_criteria>
  <done>
    `_palworld_parse(path)` exists; `_parse_settings` removed; regexes and error string byte-identical to v0.1.19; module parses.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rename _save_settings → _palworld_save(path, settings) with verbatim body</name>
  <files>logpose/main.py</files>
  <read_first>
    - logpose/main.py (to see current `_save_settings` at lines 204-226 and adjacent functions)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Pitfall 3")
  </read_first>
  <behavior>
    - Calling `_palworld_save(path, {"PalKey": "true"})` writes back the file with `OptionSettings=(PalKey=true)` — booleans NOT quoted (because `should_quote` returns False for `"true"`).
    - Calling `_palworld_save(path, {"PalKey": "1.5"})` writes `OptionSettings=(PalKey=1.5)` — numeric float NOT quoted.
    - Calling `_palworld_save(path, {"ServerName": "My Server"})` writes `OptionSettings=(ServerName="My Server")` — non-numeric non-boolean strings quoted with double-quotes.
    - After writing, `console.print("Settings saved successfully.")` is called (side effect preserved).
    - The old name `_save_settings` no longer exists: `grep -q '^def _save_settings' logpose/main.py` MUST fail after this task.
    - `should_quote` stays a LOCAL nested function inside `_palworld_save` — it is NOT hoisted to module scope.
  </behavior>
  <action>
    In `logpose/main.py`, locate the function defined as `def _save_settings(settings: dict[str, str]) -> None:` (around line 204). Replace it with EXACTLY this function:

    ```python
    def _palworld_save(path: Path, settings: dict[str, str]) -> None:
        """Saves settings back to a Palworld PalWorldSettings.ini file."""
        # verbatim from v0.1.19 _save_settings — PAL-04 invariant
        content = path.read_text()

        def should_quote(value: str) -> bool:
            if value.lower() in ("true", "false", "none"):
                return False
            try:
                float(value)
                return False
            except ValueError:
                return True

        settings_str = ",".join(
            f'{key}="{value}"' if should_quote(value) else f"{key}={value}"
            for key, value in settings.items()
        )

        new_content = re.sub(
            r"OptionSettings=\(.*?\)", f"OptionSettings=({settings_str})", content
        )
        path.write_text(new_content)
        console.print("Settings saved successfully.")
    ```

    Exact diff discipline:
    - Function name changes from `_save_settings` to `_palworld_save`.
    - Signature gains `path: Path` as first parameter; `settings: dict[str, str]` is preserved; return annotation stays `None`.
    - First-body comment: `# verbatim from v0.1.19 _save_settings — PAL-04 invariant`.
    - Nested `should_quote` function preserved BYTE-FOR-BYTE — same body, same return values, same control flow. Do not hoist it to module scope. Do not add type guards. Do not refactor the `try/except ValueError` to an `isinstance` check.
    - The ternary `f'{key}="{value}"' if should_quote(value) else f"{key}={value}"` preserved character-for-character. Do not swap quote types in the f-strings.
    - The regex `r"OptionSettings=\(.*?\)"` preserved verbatim — specifically the lazy quantifier `.*?` must stay lazy.
    - `PAL_SETTINGS_PATH.read_text()` → `path.read_text()` and `PAL_SETTINGS_PATH.write_text(new_content)` → `path.write_text(new_content)` — THE only logical changes.
    - `console.print("Settings saved successfully.")` is PRESERVED at the end — do not move it to the caller. This print is part of the v0.1.19 contract for PAL-04.

    Again, DO NOT touch the `edit_settings` call site yet — Task 3 handles both renames' call sites in one atomic edit.
  </action>
  <verify>
    <automated>grep -q '^def _palworld_save(path: Path, settings: dict\[str, str\]) -> None:' logpose/main.py && ! grep -q '^def _save_settings' logpose/main.py && python -c 'import ast, pathlib; ast.parse(pathlib.Path("logpose/main.py").read_text())'</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '^def _palworld_save(path: Path, settings: dict\[str, str\]) -> None:' logpose/main.py` returns `1`.
    - `grep -c '^def _save_settings' logpose/main.py` returns `0`.
    - `grep -c 'def should_quote(value: str) -> bool:' logpose/main.py` returns `1` AND the match is INSIDE `_palworld_save` (nested function — check indentation with `grep -n '    def should_quote' logpose/main.py`).
    - `grep -qF 'console.print("Settings saved successfully.")' logpose/main.py` succeeds (preserved side effect).
    - `grep -qF 'r"OptionSettings=\\(.*?\\)"' logpose/main.py` succeeds (lazy regex preserved).
    - `grep -qF "(\"true\", \"false\", \"none\")" logpose/main.py` succeeds (boolean-like tuple preserved).
    - `grep -c 'PAL_SETTINGS_PATH.read_text\|PAL_SETTINGS_PATH.write_text' logpose/main.py` returns `0` after this task (both old reads/writes are now parameterized away).
    - `python -c 'import ast; ast.parse(open("logpose/main.py").read())'` exits 0.
  </acceptance_criteria>
  <done>
    `_palworld_save(path, settings)` exists; `_save_settings` removed; `should_quote` still nested; console.print preserved; module parses.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update edit_settings call site to pass PAL_SETTINGS_PATH explicitly</name>
  <files>logpose/main.py</files>
  <read_first>
    - logpose/main.py (current `edit_settings` command at lines 375-396)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Call Sites")
  </read_first>
  <action>
    In `logpose/main.py`, locate the `edit_settings` function (decorated `@app.command(name="edit-settings")`, around line 375). Update the FOUR call sites:

    Before:
    ```python
    @app.command(name="edit-settings")
    def edit_settings() -> None:
        """Edit the PalWorldSettings.ini file."""
        try:
            settings = _parse_settings()
        except (FileNotFoundError, ValueError):
            _create_settings_from_default()
            try:
                settings = _parse_settings()
            except (ValueError, FileNotFoundError) as e:
                rich.print(
                    f"An error occurred after creating default settings: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)

        try:
            _interactive_edit_loop(settings)
            _save_settings(settings)
        except Exception as e:
            rich.print(f"An error occurred during settings edit: {e}", file=sys.stderr)
            sys.exit(1)
    ```

    After (only three lines change — `_parse_settings()` → `_palworld_parse(PAL_SETTINGS_PATH)` x2 and `_save_settings(settings)` → `_palworld_save(PAL_SETTINGS_PATH, settings)`):
    ```python
    @app.command(name="edit-settings")
    def edit_settings() -> None:
        """Edit the PalWorldSettings.ini file."""
        try:
            settings = _palworld_parse(PAL_SETTINGS_PATH)
        except (FileNotFoundError, ValueError):
            _create_settings_from_default()
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

    DO NOT touch `_create_settings_from_default()` in this task — Plan 03 parameterizes it. For now, that call stays exactly as written.

    DO NOT touch `sys.exit(1)` → `typer.Exit` — that's Phase 4 (CLI-05). Minimum-diff.

    After editing, grep for leftover references:
    ```bash
    grep -n '_parse_settings\|_save_settings' logpose/main.py   # MUST return NOTHING
    grep -nc '_palworld_parse(PAL_SETTINGS_PATH)' logpose/main.py  # MUST return 2
    grep -nc '_palworld_save(PAL_SETTINGS_PATH, settings)' logpose/main.py  # MUST return 1
    ```

    Smoke-test the module can be imported (does not execute CLI, just parses + resolves names):
    ```bash
    python -c "import logpose.main; assert callable(logpose.main._palworld_parse); assert callable(logpose.main._palworld_save); assert callable(logpose.main.edit_settings)"
    ```

    This smoke-test is the primary regression signal: if the rename left any stale reference, the `import logpose.main` step will either fail at module-load (if the stale name is at module scope) or pass silently (if inside a function body) — so the grep checks above are also required.
  </action>
  <verify>
    <automated>! grep -qE '_parse_settings|_save_settings' logpose/main.py && test "$(grep -c '_palworld_parse(PAL_SETTINGS_PATH)' logpose/main.py)" = "2" && test "$(grep -c '_palworld_save(PAL_SETTINGS_PATH, settings)' logpose/main.py)" = "1" && python -c "import logpose.main; assert callable(logpose.main._palworld_parse) and callable(logpose.main._palworld_save) and callable(logpose.main.edit_settings)" && pytest tests/test_palworld_golden.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -cE '_parse_settings|_save_settings' logpose/main.py` returns `0` (no stale references anywhere).
    - `grep -c '_palworld_parse(PAL_SETTINGS_PATH)' logpose/main.py` returns exactly `2` (two call sites in `edit_settings`: the primary try and the retry-after-create try).
    - `grep -c '_palworld_save(PAL_SETTINGS_PATH, settings)' logpose/main.py` returns exactly `1`.
    - `python -c "import logpose.main"` exits 0.
    - `python -c "import logpose.main; logpose.main._palworld_parse; logpose.main._palworld_save; logpose.main.edit_settings"` exits 0 (all three names resolve).
    - Plan 01's harness still green: `pytest tests/test_palworld_golden.py -x` exits 0 (Plan 02 does not touch the template, so the harness MUST still pass; this is an invariant check).
    - `_create_settings_from_default()` is still called with NO arguments in `edit_settings` (Plan 03 changes that — out of scope here).
  </acceptance_criteria>
  <done>
    edit_settings uses the new names with PAL_SETTINGS_PATH threaded explicitly; no stale references remain; module imports cleanly; Plan 01 harness still green (template unchanged).
  </done>
</task>

</tasks>

<verification>
```bash
# 1. Old names fully deleted
! grep -qE '^def _parse_settings|^def _save_settings' logpose/main.py
! grep -qE '_parse_settings\(|_save_settings\(' logpose/main.py

# 2. New names exist with correct signatures
grep -qE '^def _palworld_parse\(path: Path\) -> dict\[str, str\]:' logpose/main.py
grep -qE '^def _palworld_save\(path: Path, settings: dict\[str, str\]\) -> None:' logpose/main.py

# 3. should_quote stays nested inside _palworld_save
grep -qE '^    def should_quote\(value: str\) -> bool:' logpose/main.py

# 4. PAL-03/PAL-04 verbatim markers present
grep -c '# verbatim from v0.1.19' logpose/main.py  # returns 2

# 5. Regex and error strings byte-identical
grep -qF 'r"OptionSettings=\((.*)\)"' logpose/main.py
grep -qF "r'(\\w+)=(\".*?\"|[^,]+)'" logpose/main.py
grep -qF 'r"OptionSettings=\(.*?\)"' logpose/main.py
grep -qF 'Could not find OptionSettings in PalWorldSettings.ini' logpose/main.py

# 6. Call site updated exactly twice (parse) + once (save)
test "$(grep -c '_palworld_parse(PAL_SETTINGS_PATH)' logpose/main.py)" = "2"
test "$(grep -c '_palworld_save(PAL_SETTINGS_PATH, settings)' logpose/main.py)" = "1"

# 7. Module imports cleanly
python -c "import logpose.main; logpose.main._palworld_parse; logpose.main._palworld_save"

# 8. Plan 01 harness unaffected
pytest tests/test_palworld_golden.py -x
```
</verification>

<success_criteria>
- PAL-03 satisfied: `_palworld_parse(path)` exists with verbatim regex + error-string body.
- PAL-04 satisfied: `_palworld_save(path, settings)` exists with verbatim `should_quote` nested + verbatim regex + preserved `console.print` side effect.
- SET-01 prep: `edit_settings` threads `PAL_SETTINGS_PATH` through the new names; Phase 3's migration becomes a caller-only change when the module global dissolves into `GAMES["palworld"].settings_path`.
- No stale references to old names anywhere in `logpose/main.py`.
- Phase 1 template invariant preserved (harness from Plan 01 still green).
</success_criteria>

<output>
After completion, create `.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-02-SUMMARY.md` documenting:
- Confirmation `_parse_settings` and `_save_settings` deleted (0 grep hits).
- Confirmation `_palworld_parse` and `_palworld_save` signatures match spec exactly.
- Byte-level verification that regex strings and error message are unchanged from v0.1.19 (paste the `git diff` hunk showing ONLY the signature + body changes allowed).
- Plan 01 harness re-run exit code.
</output>
