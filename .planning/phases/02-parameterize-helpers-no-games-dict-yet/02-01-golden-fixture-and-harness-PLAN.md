---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/__init__.py
  - tests/golden/palserver.service.v0_1_19
  - tests/test_palworld_golden.py
  - scripts/capture_golden.py
  - .gitattributes
autonomous: true
requirements: [PAL-09, E2E-01]
tags: [testing, regression-harness, golden-file, python]

must_haves:
  truths:
    - "tests/golden/palserver.service.v0_1_19 exists as a 323-byte file containing the v0.1.19 rendered palserver.service for fixture user=foo, port=8211, players=32."
    - "tests/test_palworld_golden.py exists and passes when invoked via `pytest tests/test_palworld_golden.py -x` (exit 0)."
    - "tests/test_palworld_golden.py exists and passes when invoked via `python tests/test_palworld_golden.py` (exit 0)."
    - "Running the harness against a corrupted template (any single-byte drift) produces non-zero exit — the harness is a real oracle, not a tautology."
    - "A `.gitattributes` entry prevents git from normalising line endings on `logpose/templates/*.template` so the trailing-space-no-newline survives checkout on any platform."
  artifacts:
    - path: "tests/golden/palserver.service.v0_1_19"
      provides: "Byte-exact v0.1.19 rendered palserver.service for locked fixture"
      exact_bytes: 323
    - path: "tests/test_palworld_golden.py"
      provides: "Byte-diff regression harness — dual entrypoint (pytest + __main__)"
      exports: ["test_palserver_service_byte_identical_to_v0_1_19", "FIXTURE", "_render_from_template"]
    - path: "scripts/capture_golden.py"
      provides: "One-shot golden-file capture script (idempotent; re-runnable)"
    - path: ".gitattributes"
      provides: "Disables text-mode transforms on template files"
      contains: "logpose/templates/*.template -text"
    - path: "tests/__init__.py"
      provides: "Empty marker so `tests/` is not treated as a namespace package accidentally"
  key_links:
    - from: "tests/test_palworld_golden.py"
      to: "tests/golden/palserver.service.v0_1_19"
      via: "GOLDEN.read_bytes() comparison with rendered output"
      pattern: "GOLDEN\\.read_bytes\\(\\)"
    - from: "tests/test_palworld_golden.py"
      to: "logpose/templates/palserver.service.template"
      via: "TEMPLATE.read_bytes().decode.format(**FIXTURE)"
      pattern: "palserver\\.service\\.template"
---

<objective>
Land the byte-diff regression harness that anchors every subsequent phase: a locked FIXTURE, a committed 323-byte golden file captured from the current (=v0.1.19, verified via diff exit 0) `palserver.service.template`, and a dual-entrypoint pytest module that asserts byte equality between `template.format(**FIXTURE)` and the golden bytes.

Purpose: Every later phase (3-6) inherits this harness as the Palworld regression oracle. If Phase 3's `GameSpec` migration or Phase 4's polkit merge subtly changes the rendered service file, this harness fires. Without this plan landing first, Phase 2's success criterion #3 cannot be verified.

Output:
- `tests/golden/palserver.service.v0_1_19` (323 bytes, committed)
- `tests/test_palworld_golden.py` (harness with `if __name__ == "__main__":` guard)
- `scripts/capture_golden.py` (one-shot capture, idempotent)
- `.gitattributes` (preserves template EOF state)
- `tests/__init__.py` (empty marker)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md
@logpose/templates/palserver.service.template
@pyproject.toml

<interfaces>
<!-- Template format placeholders — extracted from logpose/main.py:160-174 and the template file itself. -->
<!-- The template uses str.format() with exactly these 5 named placeholders: -->

From logpose/templates/palserver.service.template (323 bytes, ends with "multi-user.target " — trailing space, NO final newline):
```
{user}                 # substituted twice: User= and Group= lines
{working_directory}    # WorkingDirectory= line
{exec_start_path}      # ExecStart= line (leading token)
{port}                 # ExecStart= line (-port={port})
{players}              # ExecStart= line (-players={players})
```

Locked FIXTURE per phase success criterion #3 + research section "Fixture Design":
```python
FIXTURE = {
    "user": "foo",
    "port": 8211,
    "players": 32,
    "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
    "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
}
```

Verified byte-equivalence (from research):
```bash
diff <(git show v0.1.19:palworld_server_launcher/templates/palserver.service.template) \
     logpose/templates/palserver.service.template
# exit 0 — the current template IS the v0.1.19 template, byte-for-byte.
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write .gitattributes to preserve template EOF bytes</name>
  <files>.gitattributes</files>
  <read_first>
    - logpose/templates/palserver.service.template (verify file tail is `et ` with no newline via `xxd | tail -1`)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Pitfall 1: Trailing-space / newline drift")
  </read_first>
  <action>
    Create `.gitattributes` at repo root (it does not exist yet — verify with `ls -la .gitattributes`; if it does exist, append the rules instead of overwriting). Write exactly these two lines (each followed by a single `\n`, and file terminated by a final `\n`):

    ```
    logpose/templates/*.template -text
    tests/golden/** -text
    ```

    The `-text` marker tells git: do not apply any text-mode transforms (no LF↔CRLF conversion, no working-tree eol normalisation) to these paths. This prevents the trailing-space-no-newline invariant from being silently broken on checkout across platforms or after a `git config core.autocrlf` change.

    After writing, run `git check-attr -a logpose/templates/palserver.service.template` and confirm the output contains `text: unset`. Also run `git check-attr -a tests/golden/palserver.service.v0_1_19` (the file itself won't exist yet but `check-attr` works on the path pattern) and confirm `text: unset`.
  </action>
  <verify>
    <automated>test -f .gitattributes && grep -qxF 'logpose/templates/*.template -text' .gitattributes && grep -qxF 'tests/golden/** -text' .gitattributes && git check-attr -a logpose/templates/palserver.service.template | grep -q 'text: unset'</automated>
  </verify>
  <acceptance_criteria>
    - `.gitattributes` exists at repo root.
    - `grep -c '\-text' .gitattributes` returns `2` (two rules).
    - `git check-attr -a logpose/templates/palserver.service.template` includes `text: unset`.
    - `git check-attr -a tests/golden/palserver.service.v0_1_19` includes `text: unset`.
    - `xxd logpose/templates/palserver.service.template | tail -1` still ends with `65 74 20` (`et ` — no trailing newline).
  </acceptance_criteria>
  <done>
    .gitattributes exists with both rules; `git check-attr` reports `text: unset` for both patterns; template EOF bytes unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create scripts/capture_golden.py + generate tests/golden/palserver.service.v0_1_19</name>
  <files>scripts/capture_golden.py, tests/__init__.py, tests/golden/palserver.service.v0_1_19</files>
  <read_first>
    - logpose/templates/palserver.service.template (the 323-byte source being rendered)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Golden-File Capture Strategy" and "Fixture Design")
  </read_first>
  <action>
    Step A — create `tests/__init__.py` as an empty file (0 bytes is fine, but make it a single `\n` terminator to keep editors happy). Purpose: prevent pytest rootdir confusion and prevent accidental namespace-package resolution if someone later runs `python -m tests.foo`.

    Step B — create `scripts/` directory if absent, then write `scripts/capture_golden.py` with EXACTLY this content (the `__future__` import is required per PKG-05; the fixture values are locked by phase success criterion #3):

    ```python
    """One-shot capture: render palserver.service from the current template
    against the locked Phase 2 fixture and write bytes to tests/golden/.

    Re-runnable. Idempotent. Exits 1 if the resulting render is not 323 bytes
    (the v0.1.19 size — any drift signals template corruption).
    """

    from __future__ import annotations

    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parent.parent
    TEMPLATE = ROOT / "logpose" / "templates" / "palserver.service.template"
    GOLDEN = ROOT / "tests" / "golden" / "palserver.service.v0_1_19"

    FIXTURE = {
        "user": "foo",
        "port": 8211,
        "players": 32,
        "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
        "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
    }


    def main() -> int:
        template_bytes = TEMPLATE.read_bytes()
        rendered = template_bytes.decode("utf-8").format(**FIXTURE).encode("utf-8")
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_bytes(rendered)
        print(f"wrote {len(rendered)} bytes to {GOLDEN.relative_to(ROOT)}")
        return 0


    if __name__ == "__main__":
        sys.exit(main())
    ```

    Step C — run the capture: `python scripts/capture_golden.py`. It MUST print `wrote 323 bytes to tests/golden/palserver.service.v0_1_19`. If it prints a different byte count, STOP — the template has drifted; do not commit the golden, open an issue.

    Step D — verify the golden bytes visually: `xxd tests/golden/palserver.service.v0_1_19 | tail -1` MUST end with `et 20` (space after "multi-user.target", no newline). If it ends with `et 20 0a`, something normalised the output — investigate.

    Step E — verify `tests/golden/palserver.service.v0_1_19` size is exactly 323 bytes: `wc -c tests/golden/palserver.service.v0_1_19` MUST print `323 tests/golden/palserver.service.v0_1_19`.

    Do NOT add a shebang to `scripts/capture_golden.py`; invoke it explicitly via `python scripts/capture_golden.py`. Do NOT mark it executable. It is a one-shot utility, not a CLI.
  </action>
  <verify>
    <automated>python scripts/capture_golden.py && test "$(wc -c < tests/golden/palserver.service.v0_1_19)" = "323" && xxd tests/golden/palserver.service.v0_1_19 | tail -1 | grep -q 'et 20$'</automated>
  </verify>
  <acceptance_criteria>
    - `scripts/capture_golden.py` exists with `from __future__ import annotations` on line 3 or earlier.
    - `tests/__init__.py` exists (size may be 0 or 1 bytes).
    - `tests/golden/palserver.service.v0_1_19` exists and is EXACTLY 323 bytes (`wc -c` returns `323`).
    - `xxd tests/golden/palserver.service.v0_1_19 | tail -1` ends with `65 74 20` (final bytes are `e`, `t`, space — no newline).
    - Re-running `python scripts/capture_golden.py` a second time leaves the golden file's sha256 unchanged (`sha256sum` output matches run 1).
    - `grep -c '^FIXTURE' scripts/capture_golden.py` returns `1`.
    - `grep -q 'port": 8211' scripts/capture_golden.py` succeeds AND `grep -q 'players": 32' scripts/capture_golden.py` succeeds AND `grep -q 'user": "foo"' scripts/capture_golden.py` succeeds.
  </acceptance_criteria>
  <done>
    Capture script runs cleanly; golden file is 323 bytes with correct EOF bytes; re-running is idempotent.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Write tests/test_palworld_golden.py with dual entrypoint</name>
  <files>tests/test_palworld_golden.py</files>
  <read_first>
    - tests/golden/palserver.service.v0_1_19 (the reference bytes — must exist before this task)
    - scripts/capture_golden.py (the FIXTURE definition must match this file exactly)
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-RESEARCH.md (section "Test Harness Recommendation")
  </read_first>
  <behavior>
    - Test 1 (`test_palserver_service_byte_identical_to_v0_1_19`): rendering the current template with FIXTURE and comparing to the committed golden MUST assert-equal (both are 323 bytes, identical sha256).
    - Test 2 (`test_golden_matches_v0_1_19_tag`): the current template bytes MUST equal `git show v0.1.19:palworld_server_launcher/templates/palserver.service.template` — guarantees the captured golden is faithful to the v0.1.19 tag.
    - Dual entrypoint: `pytest tests/test_palworld_golden.py -x` returns exit 0 AND `python tests/test_palworld_golden.py` returns exit 0.
    - Negative-path sanity: if the template file is temporarily mutated (e.g. an extra space appended), BOTH entrypoints return NON-ZERO exit. This is verified manually below, not automated.
  </behavior>
  <action>
    Create `tests/test_palworld_golden.py` with EXACTLY this content (indentation critical; Python 3.8 compatible; no walrus operators; no PEP-604 unions; `Optional` not needed here):

    ```python
    """Byte-diff regression harness — palserver.service render vs v0.1.19 golden.

    Invocation modes (both MUST exit 0 when the harness is green):
      pytest tests/test_palworld_golden.py -x
      python tests/test_palworld_golden.py

    Drops dependency on logpose.main on purpose in Task 3 — Phase 2 Plan 05 adds
    a second test that exercises the real _render_service_file code path once
    Plan 03 extracts it. Keep this file minimal and side-effect-free.
    """

    from __future__ import annotations

    import subprocess
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parent.parent
    TEMPLATE = ROOT / "logpose" / "templates" / "palserver.service.template"
    GOLDEN = ROOT / "tests" / "golden" / "palserver.service.v0_1_19"

    FIXTURE = {
        "user": "foo",
        "port": 8211,
        "players": 32,
        "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
        "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
    }


    def _render_from_template() -> bytes:
        """Render by str.format on the on-disk template. No logpose import."""
        return TEMPLATE.read_bytes().decode("utf-8").format(**FIXTURE).encode("utf-8")


    def test_palserver_service_byte_identical_to_v0_1_19() -> None:
        rendered = _render_from_template()
        expected = GOLDEN.read_bytes()
        assert rendered == expected, (
            f"palserver.service render drift vs v0.1.19 golden "
            f"(rendered={len(rendered)} bytes, golden={len(expected)} bytes). "
            f"Run: diff <(python scripts/capture_golden.py && cat {GOLDEN}) - "
            f"to inspect, then decide whether template change was intentional."
        )


    def test_golden_matches_v0_1_19_tag() -> None:
        """Paranoia: verify template on disk equals v0.1.19 tag byte-for-byte."""
        try:
            v019_bytes = subprocess.check_output(
                [
                    "git",
                    "show",
                    "v0.1.19:palworld_server_launcher/templates/palserver.service.template",
                ],
                cwd=str(ROOT),
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            import pytest

            pytest.skip(f"git or tag v0.1.19 unavailable: {exc}")
            return  # unreachable under pytest; placates type-checkers under plain python
        current_bytes = TEMPLATE.read_bytes()
        assert v019_bytes == current_bytes, (
            f"palserver.service.template drifted vs v0.1.19 tag "
            f"(current={len(current_bytes)} bytes, v0.1.19={len(v019_bytes)} bytes). "
            f"Golden was captured from current template — if template drifted, golden is invalid."
        )


    if __name__ == "__main__":
        # Script-mode entrypoint (phase success criterion #3: "script exits 0").
        # Runs both tests; the v0.1.19-tag test degrades to a skip-but-pass if git unavailable.
        try:
            test_palserver_service_byte_identical_to_v0_1_19()
        except AssertionError as exc:
            print(f"FAIL: test_palserver_service_byte_identical_to_v0_1_19: {exc}", file=sys.stderr)
            sys.exit(1)

        try:
            # In script mode, a pytest.skip call raises — catch it and treat as pass.
            import pytest as _pytest

            try:
                test_golden_matches_v0_1_19_tag()
            except _pytest.skip.Exception as skip_exc:
                print(f"SKIP: test_golden_matches_v0_1_19_tag: {skip_exc}", file=sys.stderr)
        except ImportError:
            # pytest not importable in script mode — run the raw check and let it skip silently
            try:
                v019_bytes = subprocess.check_output(
                    [
                        "git",
                        "show",
                        "v0.1.19:palworld_server_launcher/templates/palserver.service.template",
                    ],
                    cwd=str(ROOT),
                )
                assert v019_bytes == TEMPLATE.read_bytes(), (
                    "palserver.service.template drifted vs v0.1.19 tag"
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass  # git/tag unavailable — mirror the pytest skip behavior

        print("OK: palserver.service matches v0.1.19 golden")
        sys.exit(0)
    ```

    Notes on why the file is structured this way:
    - No `logpose.main` import here. Plan 05 adds a second test file that imports the real `_render_service_file`. Keeping this harness import-free means it can run on a busted `logpose/main.py` and still verify the template/golden contract — the highest-value regression signal.
    - `test_golden_matches_v0_1_19_tag` uses `pytest.skip` inside the function body so it degrades gracefully if `git` is unavailable (e.g., wheel install without the repo). The `__main__` branch replicates that behavior manually.
    - The f-string error messages are deliberately verbose with byte counts — they are the operator's first diagnostic when the harness fires.
    - No module-level side effects beyond path construction; importing this file does not touch the filesystem.

    After writing, verify both entrypoints:
    ```bash
    pytest tests/test_palworld_golden.py -x    # MUST print 2 passed (or 1 passed 1 skipped) and exit 0
    python tests/test_palworld_golden.py        # MUST print "OK: palserver.service matches v0.1.19 golden" and exit 0
    ```
  </action>
  <verify>
    <automated>pytest tests/test_palworld_golden.py -x && python tests/test_palworld_golden.py</automated>
  </verify>
  <acceptance_criteria>
    - `tests/test_palworld_golden.py` exists and starts with `"""` docstring then `from __future__ import annotations` within the first 20 lines.
    - `grep -c 'def test_' tests/test_palworld_golden.py` returns `2` (two test functions).
    - `grep -qF 'if __name__ == "__main__":' tests/test_palworld_golden.py` succeeds (dual entrypoint).
    - `grep -qF 'FIXTURE = {' tests/test_palworld_golden.py` succeeds AND the FIXTURE values (`"foo"`, `8211`, `32`, `/home/foo/.steam/steam/steamapps/common/PalServer`, `/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh`) all appear verbatim in the file.
    - `pytest tests/test_palworld_golden.py -x` exits 0 (stdout shows `2 passed` or `1 passed, 1 skipped`).
    - `python tests/test_palworld_golden.py` exits 0 and prints `OK: palserver.service matches v0.1.19 golden` on stdout.
    - The file does NOT import from `logpose` anywhere (`grep -q '^from logpose\|^import logpose' tests/test_palworld_golden.py` MUST fail).
    - Negative-path hand-check (document in commit message or SUMMARY, do NOT commit the mutation): temporarily append a byte to `logpose/templates/palserver.service.template`, re-run `pytest tests/test_palworld_golden.py -x` — MUST exit non-zero with a clear diff message. Then revert the template.
  </acceptance_criteria>
  <done>
    Both entrypoints exit 0 on the current tree; harness contains exactly 2 test functions; file is import-free from logpose; negative-path manual check (mutation + revert) confirms the harness is a real oracle.
  </done>
</task>

</tasks>

<verification>
Run these in order from the repo root; all MUST pass before marking Plan 01 done:

```bash
# 1. Static file presence
test -f .gitattributes
test -f tests/__init__.py
test -f tests/golden/palserver.service.v0_1_19
test -f tests/test_palworld_golden.py
test -f scripts/capture_golden.py

# 2. Byte-exact golden
test "$(wc -c < tests/golden/palserver.service.v0_1_19)" = "323"
xxd tests/golden/palserver.service.v0_1_19 | tail -1 | grep -q 'et 20$'

# 3. Gitattributes take effect
git check-attr -a logpose/templates/palserver.service.template | grep -q 'text: unset'

# 4. Harness green, both entrypoints
pytest tests/test_palworld_golden.py -x
python tests/test_palworld_golden.py

# 5. Capture script idempotent
sha256sum tests/golden/palserver.service.v0_1_19 > /tmp/golden.sha
python scripts/capture_golden.py
sha256sum -c /tmp/golden.sha

# 6. No accidental logpose import in harness
! grep -Eq '^(from|import) logpose' tests/test_palworld_golden.py
```
</verification>

<success_criteria>
- Contributes to PAL-09 (byte-diff harness half — ARK half deferred to Phase 5).
- Contributes to E2E-01 (byte-diff test infrastructure).
- Dual-entrypoint harness exits 0 on current tree.
- Golden file is 323 bytes with trailing space, no trailing newline.
- `.gitattributes` prevents platform-dependent normalisation of template and golden bytes.
- Phase 2 success criterion #3 "script exits 0" is demonstrably satisfiable (both `pytest` and `python` modes).
</success_criteria>

<output>
After completion, create `.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-01-SUMMARY.md` documenting:
- Exact byte size of golden file (must be 323)
- Sha256 of golden file for future drift detection
- Confirmation that `pytest` and `python` entrypoints both exit 0
- Negative-path manual verification outcome (template mutation fires harness; reverted cleanly)
</output>
