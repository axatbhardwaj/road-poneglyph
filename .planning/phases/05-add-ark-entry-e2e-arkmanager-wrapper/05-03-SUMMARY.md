---
phase: 05-add-ark-entry-e2e-arkmanager-wrapper
plan: 03
subsystem: ark-byte-diff-harness
tags: [tests, golden, byte-diff, ark]
requires: [05-02]
provides: [ark-byte-diff-tests, arkserver-golden, sudoers-golden]
affects: [tests/]
tech-stack:
  added: []
  patterns: [byte-diff-harness, dual-invocation-script-and-pytest]
key-files:
  created:
    - tests/test_ark_golden.py
    - tests/golden/arkserver.service.v0_2_0
    - tests/golden/logpose-ark.sudoers.v0_2_0
decisions:
  - "Mirror Palworld harness structure: ROOT constant at top, dual pytest + script-mode invocation, descriptive failure messages with re-capture hints"
  - "Self-contained — no import of logpose.main (templates are tested in isolation of module code)"
  - "Sudoers golden captured with user='foo' (matches Palworld fixture user)"
metrics:
  tasks_completed: 2
  tasks_total: 2
  commits: 2
  completed: "2026-04-13"
---

# Phase 5 Plan 3: ARK Byte-Diff Harness Summary

Locks the shape of the two ARK templates with a $0.01 static byte-diff test — any future drift in `arkserver.service.template` or `logpose-ark.sudoers.template` fails the harness immediately instead of surfacing only during VM E2E.

## Commits

| Hash | Subject |
|------|---------|
| 2ccecba | test(05-03): capture v0.2.0 goldens for arkserver.service + sudoers templates |
| 65772a6 | test(05-03): add tests/test_ark_golden.py byte-diff harness |

## What Was Built

- `tests/golden/arkserver.service.v0_2_0` (296 bytes) — static template bytes.
- `tests/golden/logpose-ark.sudoers.v0_2_0` (54 bytes) — rendered with `user='foo'`.
- `tests/test_ark_golden.py` (2 tests):
  - `test_arkserver_service_template_static` — reads template + golden, byte-compares.
  - `test_logpose_ark_sudoers_template_renders_correctly` — renders template with `user='foo'`, byte-compares.
- Dual invocation:
  - `pytest tests/test_ark_golden.py -x` → 2 passed.
  - `python tests/test_ark_golden.py` → exits 0 with "OK" message.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `pytest tests/test_ark_golden.py -x` → 2 passed ✅
- `python tests/test_ark_golden.py` → OK, exit 0 ✅
- `pytest tests/ -x` → 6 passed (4 palworld + 2 ark) ✅
- Goldens contain expected patterns (`User=steam`, `foo ALL=(steam) NOPASSWD:`) ✅

## Self-Check: PASSED

- FOUND: tests/test_ark_golden.py
- FOUND: tests/golden/arkserver.service.v0_2_0
- FOUND: tests/golden/logpose-ark.sudoers.v0_2_0
- FOUND commits: 2ccecba, 65772a6
- Full test suite 6/6 green.
