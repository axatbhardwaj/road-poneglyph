---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 02
subsystem: logpose-settings-io
tags: [refactor, palworld, settings, python]
dependency_graph:
  requires: [PAL-03-invariant-body, PAL-04-invariant-body]
  provides:
    - "_palworld_parse(path: Path) -> dict[str, str]"
    - "_palworld_save(path: Path, settings: dict[str, str]) -> None"
  affects: [logpose.main.edit_settings]
tech_stack:
  added: []
  patterns: [verbatim-body-discipline, explicit-path-parameter]
key_files:
  created: []
  modified:
    - logpose/main.py
decisions:
  - "Normalized PAL-03/PAL-04 verbatim markers to '# verbatim from v0.1.19 — PAL-NN invariant' (drop historical function name) so grep '_parse_settings|_save_settings' returns 0 matches, matching must_haves.truths and orchestrator critical_invariants."
metrics:
  duration_minutes: ~8
  completed_date: 2026-04-12
requirements: [PAL-03, PAL-04, SET-01]
---

# Phase 02 Plan 02: Extract Palworld Parse/Save Summary

Rename `_parse_settings` → `_palworld_parse(path)` and `_save_settings(settings)` → `_palworld_save(path, settings)` with verbatim bodies; `edit_settings` threads `PAL_SETTINGS_PATH` explicitly through the single call site.

## Outcome

- `_palworld_parse(path: Path) -> dict[str, str]` defined (logpose/main.py:191).
- `_palworld_save(path: Path, settings: dict[str, str]) -> None` defined (logpose/main.py:205).
- Old `_parse_settings` / `_save_settings` wrappers DELETED (no shims).
- `edit_settings` calls `_palworld_parse(PAL_SETTINGS_PATH)` twice (primary + retry-after-create) and `_palworld_save(PAL_SETTINGS_PATH, settings)` once.
- Nested `should_quote` preserved (not hoisted); `console.print("Settings saved successfully.")` preserved as side effect inside the saver.
- Regex strings (outer greedy `r"OptionSettings=\((.*)\)"`, pairs `r'(\w+)=(".*?"|[^,]+)'`, lazy `r"OptionSettings=\(.*?\)"`) and error message `"Could not find OptionSettings in PalWorldSettings.ini"` copied byte-for-byte from v0.1.19.

## Verification

All checks from `<verification>` block passed:

```
1. Old names fully deleted             OK (def + call hits = 0)
2. New signatures correct              OK
3. should_quote nested                 OK (line 210 with 4-space indent)
4. Verbatim markers x2                 OK (PAL-03, PAL-04)
5. Regex + error strings byte-identical OK
6. Call site counts                    OK (parse=2, save=1)
7. Module imports cleanly              OK (logpose.main via .venv)
8. Plan 01 harness                     OK (2 passed in 0.01s)
```

### Byte-level diff (only allowed changes)

```diff
-def _parse_settings() -> dict[str, str]:
-    """Parses the PalWorldSettings.ini file."""
-    content = PAL_SETTINGS_PATH.read_text()
+def _palworld_parse(path: Path) -> dict[str, str]:
+    """Parses a Palworld PalWorldSettings.ini file."""
+    # verbatim from v0.1.19 — PAL-03 invariant
+    content = path.read_text()
```

```diff
-def _save_settings(settings: dict[str, str]) -> None:
-    """Saves the settings back to PalWorldSettings.ini."""
-    content = PAL_SETTINGS_PATH.read_text()
+def _palworld_save(path: Path, settings: dict[str, str]) -> None:
+    """Saves settings back to a Palworld PalWorldSettings.ini file."""
+    # verbatim from v0.1.19 — PAL-04 invariant
+    content = path.read_text()
 ...
-    PAL_SETTINGS_PATH.write_text(new_content)
+    path.write_text(new_content)
```

```diff
-        settings = _parse_settings()
+        settings = _palworld_parse(PAL_SETTINGS_PATH)   # x2
 ...
-        _save_settings(settings)
+        _palworld_save(PAL_SETTINGS_PATH, settings)
```

Changes confined to: signature (+docstring polish), first-body invariant comment, module-global read/write → `path` parameter, and 3 call-site name swaps in `edit_settings`. No regex chars, no error-string chars, no control-flow edits.

## Commits

| Task | Name                                                            | Commit  |
| ---- | --------------------------------------------------------------- | ------- |
| 1    | Rename _parse_settings → _palworld_parse(path)                  | ec71cba |
| 2    | Rename _save_settings → _palworld_save(path, settings)          | 6e70262 |
| 3    | Update edit_settings call sites + normalize invariant markers   | c317951 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking / spec conflict] Invariant-marker wording collided with Task 3 grep check**

- **Found during:** Task 3 verification (`grep -cE '_parse_settings|_save_settings'` returned 2 instead of 0)
- **Issue:** Task 1/2 action text prescribed `# verbatim from v0.1.19 _parse_settings — PAL-03 invariant` (and similarly for PAL-04) as the first-body comment. That wording embeds the historical function names, which causes the plan's own Task 3 verification regex (`_parse_settings|_save_settings`) to match. The plan frontmatter `must_haves.truths` and the orchestrator's `<critical_invariants>` both specify the shorter form `# verbatim from v0.1.19 — PAL-03 invariant` (no historical name). The orchestrator spec wins.
- **Fix:** Normalized both comments in Task 3 to drop the historical function names. Behavioral invariant (PAL-03/PAL-04) unchanged — comments are documentation, not code.
- **Files modified:** logpose/main.py (lines 193, 207)
- **Commit:** c317951 (bundled with call-site rewrite — single atomic transition to the final state)

### Environmental Notes

- `python3` at `/bin/python3` is Python 3.14 without `typer`/`rich`/`pytest`. Used project `.venv/bin/python` (Python 3.12.10) which has the install and for which pytest was added on-demand for the Plan 01 harness rerun. This is a pre-existing worktree hygiene issue and out of scope for this plan.

## Plan 01 Harness Re-run

```
tests/test_palworld_golden.py ..                  [100%]
============================== 2 passed in 0.01s ==============================
```

Phase 1 template invariant preserved (plan touches only parse/save bodies and one call site; templates untouched, golden files untouched).

## Success Criteria

- [x] PAL-03: `_palworld_parse(path)` with verbatim regex + error-string body.
- [x] PAL-04: `_palworld_save(path, settings)` with verbatim `should_quote` nested + verbatim regex + preserved `console.print` side effect.
- [x] SET-01 prep: `edit_settings` threads `PAL_SETTINGS_PATH` explicitly — Phase 3 swaps the caller's arg to `GAMES["palworld"].settings_path` with no helper-body changes.
- [x] No stale references to old names anywhere in `logpose/main.py`.
- [x] Phase 1 template invariant preserved (harness green).

## Self-Check: PASSED

- FOUND: logpose/main.py (modified)
- FOUND: commit ec71cba (Task 1)
- FOUND: commit 6e70262 (Task 2)
- FOUND: commit c317951 (Task 3)
- FOUND: .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-02-SUMMARY.md (this file)
