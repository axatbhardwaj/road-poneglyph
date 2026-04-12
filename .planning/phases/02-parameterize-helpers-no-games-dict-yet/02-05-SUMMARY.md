---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 05
subsystem: tests.test_palworld_golden
tags: [testing, regression-harness, real-code-path, python]
requirements: [PAL-09, E2E-01, ARCH-04]
dependency_graph:
  requires:
    - "02-parameterize-helpers-no-games-dict-yet/01 (byte-diff harness + golden fixture)"
    - "02-parameterize-helpers-no-games-dict-yet/03 (pure _render_service_file helper)"
  provides:
    - "Real-code-path oracle for _render_service_file — if Phase 3 GameSpec migration breaks byte-compat, this test fires"
    - "Harness now has 3 tests: template-format (Plan 01), v0.1.19-tag drift (Plan 01), _render_service_file real-path (Plan 05)"
  affects: []
tech_stack:
  added: []
  patterns:
    - "deferred import inside test body (so Plan 01 tests stay green even if logpose.main breaks)"
    - "sys.path insertion for script-mode import resolution"
key_files:
  created:
    - .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-05-SUMMARY.md
  modified:
    - tests/test_palworld_golden.py
decisions:
  - "Prepend repo root to sys.path at module top so `python tests/test_palworld_golden.py` finds the `logpose` package in script mode — pytest already handles this via rootdir, but script mode only adds the script's own directory. This closes the acceptance gap on the Rule 3 blocker."
  - "Deferred import (`from logpose.main import _render_service_file` inside the test body, NOT at module top) preserves Plan 01 invariant that the first two tests can run even with a broken logpose.main."
metrics:
  duration: "~10 min"
  completed: "2026-04-12"
  tasks: 1
  commits: 1
  files_modified: 1
---

# Phase 2 Plan 5: Harness Real Render Path Summary

Extended `tests/test_palworld_golden.py` with a third test that imports `_render_service_file` from `logpose.main`, calls it with the locked FIXTURE, and asserts its UTF-8-encoded output equals `tests/golden/palserver.service.v0_1_19` byte-for-byte — closing Pitfall 4 and making the harness load-bearing for Phase 3's `GameSpec` migration.

## What Was Done

### Task 1: Added `test_render_service_file_byte_identical_to_golden` — commit `e3f962a`

- New test (~30 lines) inserted between `test_golden_matches_v0_1_19_tag` and the `__main__` block.
- Deferred import of `_render_service_file` inside the test function body (not module-top) — preserves Plan 01's invariant that the first two tests run even if `logpose.main` is broken.
- Uses all five locked FIXTURE keys (`user`, `port`, `players`, `working_directory`, `exec_start_path`) with string paths wrapped in `Path(...)`.
- `__main__` block extended with a new `try/except` block that runs the test, exits 1 on `AssertionError` or `ImportError`, and the final success message updated to `OK: palserver.service matches v0.1.19 golden (template + real render path)`.

## Acceptance Results

| Check                                                                                             | Result   |
| ------------------------------------------------------------------------------------------------- | -------- |
| `grep -c '^def test_' tests/test_palworld_golden.py` == 3                                         | 3 — PASS |
| `grep -qF 'def test_render_service_file_byte_identical_to_golden(' ...`                           | PASS     |
| `from logpose.main import _render_service_file` inside test body (deferred)                       | PASS     |
| All 5 FIXTURE keys used: user, port, players, working_directory, exec_start_path                  | PASS     |
| `service_name="palserver"` + `template_name="palserver.service.template"` kwargs present         | PASS     |
| `pytest tests/test_palworld_golden.py -x`                                                         | 3 passed |
| `python tests/test_palworld_golden.py`                                                            | EXIT=0   |
| Negative-path mutation (port=players swap) fires Plan 05 test                                     | PASS     |

## Both Entrypoints Exit Codes

```
$ /home/xzat/personal/palworld-server-launcher/.venv/bin/python -m pytest tests/test_palworld_golden.py -x
collected 3 items
tests/test_palworld_golden.py ...                                        [100%]
============================== 3 passed in 0.05s ===============================
EXIT=0

$ /home/xzat/personal/palworld-server-launcher/.venv/bin/python tests/test_palworld_golden.py
OK: palserver.service matches v0.1.19 golden (template + real render path)
EXIT=0
```

## Negative-Path Mutation (Real-Oracle Proof)

To confirm the new test is not a tautology, `_render_service_file` was temporarily mutated (swapped `port=port` to `port=players` in the `template.format(...)` call). With the mutation in place:

```
$ pytest tests/test_palworld_golden.py -x
1 failed, 2 passed in 0.06s
E   AssertionError: _render_service_file drift vs v0.1.19 golden
    (rendered=381 bytes, golden=383 bytes). Helper body diverged from
    template.format path — inspect logpose/main.py _render_service_file
    and compare placeholder wiring against the template.
E   assert b'[Unit]\nDes...-user.target ' == b'[Unit]\nDes...-user.target '
E     At index 239 diff: b'3' != b'8'
```

The first two Plan 01 tests still passed (confirming deferred import does not bleed state), and the Plan 05 test failed with a clear byte-count + index-diff message. Mutation reverted; all three tests green again; `logpose/main.py` restored byte-identical to pre-mutation HEAD.

## Phase 2 Final Snapshot

| Criterion                                                                     | Status                                               |
| ----------------------------------------------------------------------------- | ---------------------------------------------------- |
| #1 Parse/save byte-equivalent (Plan 02, Plan 03)                              | PASS — `_palworld_parse` + `_palworld_save` in place |
| #2 Helpers accept explicit args — no module-global reads (Plan 03)            | PASS — 7 signatures verified                         |
| #3 Script exits 0 — `pytest ...` AND `python ...` (Plan 01, Plan 05)          | PASS — both entrypoints green with 3 tests           |
| #4 Manual E2E (install → start → edit-settings → stop) unchanged on VM        | USER-VERIFIABLE — not in-scope for static harness    |

## Note for Phase 3 Planner

`test_render_service_file_byte_identical_to_golden` is the regression oracle that must stay green across the `GameSpec` migration. The caller switches from passing individual values to passing `spec.working_directory`/`spec.exec_start_path`/etc., but `_render_service_file`'s body is unchanged — so this test keeps passing. If Phase 3 accidentally mutates `_render_service_file`'s internals (e.g., template lookup logic, placeholder wiring, argument routing), this test fires immediately with a byte-count + index-diff message.

Plan 05 also adds a `sys.path.insert(0, str(ROOT))` guard at module top of `tests/test_palworld_golden.py`. Phase 3 should NOT remove this — it makes the script-mode entrypoint portable across environments that don't install `logpose` as an editable package.

## Deviations from Plan

**1. [Rule 3 — Blocking issue] Added `sys.path.insert(0, str(ROOT))` guard at module top**

- **Found during:** Task 1 verification (`python tests/test_palworld_golden.py`)
- **Issue:** The plan's acceptance required `python tests/test_palworld_golden.py` to exit 0, but in script mode Python only adds the script's own directory (`tests/`) to `sys.path` — not the repo root. So `from logpose.main import _render_service_file` failed with `ModuleNotFoundError: No module named 'logpose'`, making the `__main__` block print `FAIL: cannot import _render_service_file (logpose.main broken)` and exit 1. Pytest already handled this via rootdir configuration in `pyproject.toml`.
- **Fix:** Added a conditional `if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))` immediately after the `ROOT`/`TEMPLATE`/`GOLDEN` path constants. This closes the acceptance gap without polluting sys.path on re-imports.
- **Files modified:** `tests/test_palworld_golden.py` (4 new lines, folded into the main commit)
- **Commit:** `e3f962a`

No other deviations. Plan executed as written.

## Deferred Items

None.

## Known Stubs

None introduced by this plan.

## Self-Check: PASSED

- tests/test_palworld_golden.py — FOUND (3 tests, real-code-path test present)
- .planning/phases/02-parameterize-helpers-no-games-dict-yet/02-05-SUMMARY.md — FOUND (this file)
- Commit `e3f962a` — FOUND (Task 1: real-code-path test)
- `pytest tests/test_palworld_golden.py -x` — 3 passed
- `python tests/test_palworld_golden.py` — EXIT=0
- Negative-path mutation — fired the Plan 05 test and was reverted cleanly
