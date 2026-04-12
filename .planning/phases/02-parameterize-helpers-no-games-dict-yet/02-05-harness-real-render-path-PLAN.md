---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 05
type: execute
wave: 3
depends_on:
  - "02-parameterize-helpers-no-games-dict-yet/01"
  - "02-parameterize-helpers-no-games-dict-yet/03"
files_modified:
  - tests/test_palworld_golden.py
autonomous: true
requirements: [PAL-09, E2E-01, ARCH-04]
tags: [testing, regression-harness, real-code-path, python]

must_haves:
  truths:
    - "tests/test_palworld_golden.py now imports `_render_service_file` from `logpose.main` AND asserts its UTF-8-encoded output equals `tests/golden/palserver.service.v0_1_19` byte-for-byte."
    - "The new assertion uses the LOCKED FIXTURE (user=foo, port=8211, players=32, working_directory=/home/foo/.steam/steam/steamapps/common/PalServer, exec_start_path=/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh) — no ad-hoc values."
    - "Both entrypoints still exit 0: `pytest tests/test_palworld_golden.py -x` and `python tests/test_palworld_golden.py`."
    - "The harness now has THREE tests: the original template-format test (Plan 01), the v0.1.19-tag drift test (Plan 01), and the new `_render_service_file` real-code-path test (Plan 05)."
    - "If `_render_service_file` is ever refactored incorrectly (e.g., wrong `str.format` kwargs, wrong template lookup), the new test fires — proving Pitfall 4 is closed."
  artifacts:
    - path: "tests/test_palworld_golden.py"
      provides: "Byte-diff harness with dual entrypoint AND real-code-path coverage via _render_service_file"
      exports: ["test_palserver_service_byte_identical_to_v0_1_19", "test_golden_matches_v0_1_19_tag", "test_render_service_file_byte_identical_to_golden"]
  key_links:
    - from: "tests/test_palworld_golden.py::test_render_service_file_byte_identical_to_golden"
      to: "logpose.main::_render_service_file"
      via: "import + call with FIXTURE + assertEqual on UTF-8 encoded output vs golden bytes"
      pattern: "from logpose.main import _render_service_file"
---

<objective>
Close the Pitfall 4 gap ("harness silently passes because it's running the helper unused code path") by adding a third test that imports the REAL `_render_service_file` function from `logpose.main` and asserts its output equals `tests/golden/palserver.service.v0_1_19`. This is the oracle for every Phase 3/4/5 refactor — if a future change to `_render_service_file` breaks the render, this test fires.

Purpose: Completes PAL-09 for Phase 2 (Palworld half of the byte-diff harness — ARK half lands in Phase 5). Elevates E2E-01 from "template-format matches" to "real helper call matches". Makes the harness load-bearing for Phase 3's `GameSpec` migration: the caller switches from passing individual values to passing `spec.working_directory` etc., but `_render_service_file`'s body is unchanged, so this test keeps passing. If Phase 3 accidentally mutates `_render_service_file`, the test fails immediately.

Output: `tests/test_palworld_golden.py` extended by ~30 lines with one new test function + one small update to the `__main__` block.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md
@.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-01-golden-fixture-and-harness-PLAN.md
@.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-03-parameterize-helpers-PLAN.md
@tests/test_palworld_golden.py
@logpose/main.py

<interfaces>
<!-- _render_service_file signature (from Plan 03): -->

```python
def _render_service_file(
    service_name: str,
    template_name: str,
    user: str,
    working_directory: Path,
    exec_start_path: Path,
    port: int,
    players: int,
) -> str
```

Returns the rendered string (NOT bytes). To compare with the bytes-format golden file, the test encodes as UTF-8.

<!-- FIXTURE values (must be character-identical to Plan 01's FIXTURE): -->

```python
FIXTURE = {
    "user": "foo",
    "port": 8211,
    "players": 32,
    "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
    "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
}
```

Note: `_render_service_file` expects `working_directory` and `exec_start_path` as `Path` objects (the signature annotates them that way); the existing `FIXTURE` dict stores them as strings. The test wraps them via `Path(...)` when calling the helper. `str(Path("/foo/bar")) == "/foo/bar"` on POSIX, so the rendered template bytes are identical.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add test_render_service_file_byte_identical_to_golden to harness</name>
  <files>tests/test_palworld_golden.py</files>
  <read_first>
    - tests/test_palworld_golden.py (the entire current file — the new test must compose cleanly with the existing two tests and the `__main__` entrypoint)
    - logpose/main.py (confirm `_render_service_file` exists with the Plan 03 signature — `grep '^def _render_service_file' logpose/main.py` MUST succeed)
  </read_first>
  <behavior>
    - `test_render_service_file_byte_identical_to_golden` imports `_render_service_file` from `logpose.main`, calls it with the locked FIXTURE (string paths wrapped in `Path(...)`, service_name="palserver", template_name="palserver.service.template"), and asserts the UTF-8 encoded return value equals `GOLDEN.read_bytes()` — the 323-byte file committed in Plan 01.
    - The test FAILS (non-zero exit) if `_render_service_file`'s output drifts from the golden by even one byte.
    - Running `pytest tests/test_palworld_golden.py -x` exits 0 after this change (all three tests pass).
    - Running `python tests/test_palworld_golden.py` exits 0 after this change (script-mode covers all three tests, with the v0.1.19-tag test degrading to skip if git is unavailable).
  </behavior>
  <action>
    In `tests/test_palworld_golden.py`, make two edits.

    Edit 1 — add the new test function. Insert it AFTER `test_golden_matches_v0_1_19_tag` and BEFORE the `if __name__ == "__main__":` block:

    ```python
    def test_render_service_file_byte_identical_to_golden() -> None:
        """Real code path: _render_service_file must produce byte-identical output to the golden.

        This is the Pitfall 4 defender — if the harness only tests template.format() directly,
        a broken _render_service_file helper would sneak past unnoticed. This test imports the
        real helper, calls it with the fixture, and enforces byte-equality against the golden.
        """
        from logpose.main import _render_service_file

        rendered_str = _render_service_file(
            service_name="palserver",
            template_name="palserver.service.template",
            user=FIXTURE["user"],
            working_directory=Path(FIXTURE["working_directory"]),
            exec_start_path=Path(FIXTURE["exec_start_path"]),
            port=FIXTURE["port"],
            players=FIXTURE["players"],
        )
        rendered_bytes = rendered_str.encode("utf-8")
        expected = GOLDEN.read_bytes()
        assert rendered_bytes == expected, (
            f"_render_service_file drift vs v0.1.19 golden "
            f"(rendered={len(rendered_bytes)} bytes, golden={len(expected)} bytes). "
            f"Helper body diverged from template.format path — inspect logpose/main.py "
            f"_render_service_file and compare placeholder wiring against the template."
        )
    ```

    Note on Path vs str: `FIXTURE["working_directory"]` is a string. The helper expects `Path`. `Path("/home/foo/.steam/steam/steamapps/common/PalServer")`'s `__str__` on POSIX is `"/home/foo/.steam/steam/steamapps/common/PalServer"` — identical to the string form. So when `_render_service_file` runs `template.format(..., working_directory=<Path>)`, `str.format` calls `str(<Path>)` which returns the POSIX path string. The resulting bytes equal the golden.

    Note on import placement: Put `from logpose.main import _render_service_file` INSIDE the test function (deferred import), not at module top. Rationale: the Plan 01 tests are deliberately import-free from `logpose` so they can run on a busted `logpose/main.py` and still verify the template/golden contract. If this Plan 05 import fails (syntax error in `logpose/main.py`), ONLY this third test fails; the first two tests still run. Maximum regression signal under partial breakage.

    Edit 2 — extend the `__main__` block to run the new test in script mode. Current (Plan 01) `__main__` structure is:

    ```python
    if __name__ == "__main__":
        try:
            test_palserver_service_byte_identical_to_v0_1_19()
        except AssertionError as exc:
            print(f"FAIL: test_palserver_service_byte_identical_to_v0_1_19: {exc}", file=sys.stderr)
            sys.exit(1)

        try:
            import pytest as _pytest
            try:
                test_golden_matches_v0_1_19_tag()
            except _pytest.skip.Exception as skip_exc:
                print(f"SKIP: test_golden_matches_v0_1_19_tag: {skip_exc}", file=sys.stderr)
        except ImportError:
            # pytest not importable in script mode — run the raw check and let it skip silently
            try:
                v019_bytes = subprocess.check_output(...)
                assert v019_bytes == TEMPLATE.read_bytes(), ...
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        print("OK: palserver.service matches v0.1.19 golden")
        sys.exit(0)
    ```

    Insert a new `try/except` block AFTER the v0.1.19-tag block and BEFORE the final `print("OK: ...")`:

    ```python
        try:
            test_render_service_file_byte_identical_to_golden()
        except AssertionError as exc:
            print(f"FAIL: test_render_service_file_byte_identical_to_golden: {exc}", file=sys.stderr)
            sys.exit(1)
        except ImportError as exc:
            print(f"FAIL: cannot import _render_service_file (logpose.main broken): {exc}", file=sys.stderr)
            sys.exit(1)
    ```

    Also update the final success message from `"OK: palserver.service matches v0.1.19 golden"` to `"OK: palserver.service matches v0.1.19 golden (template + real render path)"` — small clarification; acceptable either way, but recommended.

    After editing, run BOTH entrypoints:
    ```bash
    pytest tests/test_palworld_golden.py -x     # MUST exit 0; "3 passed" or "2 passed, 1 skipped"
    python tests/test_palworld_golden.py         # MUST exit 0; stdout "OK: ..."
    ```

    Then run a negative-path sanity check (do NOT commit the mutation):
    ```bash
    # Temporarily break _render_service_file: comment out the template.format line
    # OR change `port=port` to `port=players` in the format call, etc.
    # Re-run: pytest tests/test_palworld_golden.py -x   → MUST exit non-zero with the Plan 05 test's failure message
    # Revert the mutation.
    ```
    This confirms the test is a real oracle, not a tautology.
  </action>
  <verify>
    <automated>test "$(grep -c '^def test_' tests/test_palworld_golden.py)" = "3" && grep -qF 'from logpose.main import _render_service_file' tests/test_palworld_golden.py && grep -qF 'test_render_service_file_byte_identical_to_golden' tests/test_palworld_golden.py && pytest tests/test_palworld_golden.py -x && python tests/test_palworld_golden.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '^def test_' tests/test_palworld_golden.py` returns `3`.
    - `grep -qF 'def test_render_service_file_byte_identical_to_golden(' tests/test_palworld_golden.py` succeeds.
    - `grep -qF 'from logpose.main import _render_service_file' tests/test_palworld_golden.py` succeeds AND the import is INSIDE the test function body (deferred), NOT at module top. Verify with: `awk '/^def test_render_service_file/,/^def |^if __name__/' tests/test_palworld_golden.py | grep -q 'from logpose.main import _render_service_file'`.
    - The new test uses all FIVE FIXTURE keys: check `grep -qF 'FIXTURE["user"]' tests/test_palworld_golden.py` AND `grep -qF 'FIXTURE["port"]' tests/test_palworld_golden.py` AND `grep -qF 'FIXTURE["players"]' tests/test_palworld_golden.py` AND `grep -qF 'FIXTURE["working_directory"]' tests/test_palworld_golden.py` AND `grep -qF 'FIXTURE["exec_start_path"]' tests/test_palworld_golden.py` ALL succeed.
    - `service_name="palserver"` appears in the call to `_render_service_file`: `grep -qF 'service_name="palserver"' tests/test_palworld_golden.py` succeeds.
    - `template_name="palserver.service.template"` appears: `grep -qF 'template_name="palserver.service.template"' tests/test_palworld_golden.py` succeeds.
    - `__main__` block includes an invocation of the new test: `grep -qF 'test_render_service_file_byte_identical_to_golden()' tests/test_palworld_golden.py` succeeds (should match at least twice: once in the `def` and once in the `__main__` call).
    - `pytest tests/test_palworld_golden.py -x` exits 0 with "3 passed" or "2 passed, 1 skipped" (the v0.1.19-tag test may skip if git unavailable; Plan 05 test MUST pass, not skip).
    - `python tests/test_palworld_golden.py` exits 0.
    - Negative-path manual check: hand-mutate `_render_service_file` (e.g., swap `port=port` to `port=players` in the `.format()` call) → re-run `pytest tests/test_palworld_golden.py -x` → MUST exit non-zero with a clear message from the Plan 05 test. Revert the mutation. Record the outcome in the SUMMARY.
  </acceptance_criteria>
  <done>
    Harness now has three tests with the third one exercising the real `_render_service_file` code path; both entrypoints green; negative-path mutation confirms the test is a real oracle.
  </done>
</task>

</tasks>

<verification>
```bash
# 1. Test count and presence
test "$(grep -c '^def test_' tests/test_palworld_golden.py)" = "3"
grep -qF 'def test_render_service_file_byte_identical_to_golden(' tests/test_palworld_golden.py

# 2. Deferred import (inside the new test function body)
awk '/^def test_render_service_file/,/^def |^if __name__/' tests/test_palworld_golden.py \
  | grep -q 'from logpose.main import _render_service_file'

# 3. Fixture keys all used
for k in user port players working_directory exec_start_path; do
  grep -qF "FIXTURE[\"$k\"]" tests/test_palworld_golden.py
done

# 4. Both entrypoints green
pytest tests/test_palworld_golden.py -x
python tests/test_palworld_golden.py

# 5. Module still imports cleanly
python -c "import logpose.main"

# 6. Full phase-level verification — all Phase 2 invariants hold
python -c "
from pathlib import Path
import logpose.main as m
# _render_service_file produces byte-exact golden
out = m._render_service_file(
    'palserver', 'palserver.service.template', 'foo',
    Path('/home/foo/.steam/steam/steamapps/common/PalServer'),
    Path('/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh'),
    8211, 32,
)
golden = Path('tests/golden/palserver.service.v0_1_19').read_bytes()
assert out.encode('utf-8') == golden
# Parse/save functions still byte-compat (symbol-level check)
assert callable(m._palworld_parse)
assert callable(m._palworld_save)
# Module-scope constants preserved for Phase 3 migration
assert hasattr(m, 'PAL_SERVER_DIR')
assert hasattr(m, 'PAL_SETTINGS_PATH')
assert hasattr(m, 'DEFAULT_PAL_SETTINGS_PATH')
print('OK: Phase 2 invariants satisfied')
"
```
</verification>

<success_criteria>
- PAL-09 (Palworld half): Byte-diff harness covers the real helper code path, not just a template-format shortcut.
- E2E-01 (complete for Phase 2): Rendered Palworld service file matches v0.1.19 golden via both the direct template-format path AND the `_render_service_file` real-code path.
- ARCH-04 (Phase 2 partial, verified): The new test exercises the parameterized `_render_service_file` signature — confirming that the parameter threading in Plan 03 produces the same bytes as v0.1.19's module-global-based rendering.
- Phase 2 success criterion #3 ("script exits 0") fully satisfied via both `pytest` and `python` entrypoints.
- Phase 2 success criterion #1 (parse/save byte-equivalent) verified via Plan 02 + Plan 03 + this plan's harness.
- Phase 2 success criterion #2 (helpers accept explicit args) verified via Plan 03.
- Phase 2 success criterion #4 (manual E2E: install → start → edit-settings → stop unchanged) is user-verifiable on a VM; harness provides static confidence but does not replace manual E2E.
</success_criteria>

<output>
After completion, create `.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-05-SUMMARY.md` documenting:
- Test count: 3 (or 2 + 1 skipped if git unavailable).
- Both entrypoints exit codes.
- Negative-path mutation outcome (proves the test is a real oracle).
- Final Phase 2 snapshot: all four success criteria checked off.
- Note for Phase 3 planner: the `_render_service_file` real-path test is the regression oracle that must stay green across the `GameSpec` migration. If it fires in Phase 3, the migration broke byte-compat.
</output>
