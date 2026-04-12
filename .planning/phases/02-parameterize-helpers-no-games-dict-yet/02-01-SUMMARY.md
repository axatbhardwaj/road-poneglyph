---
phase: 02-parameterize-helpers-no-games-dict-yet
plan: 01
subsystem: testing
tags: [testing, regression-harness, golden-file, python]
requirements: [PAL-09, E2E-01]
dependency-graph:
  requires: []
  provides:
    - "tests/golden/palserver.service.v0_1_19 — 383-byte v0.1.19-faithful render anchor"
    - "tests/test_palworld_golden.py — dual-entrypoint byte-diff harness"
    - "scripts/capture_golden.py — idempotent golden capture"
  affects:
    - "All Phase 2–6 refactors now have a byte-equivalence oracle"
tech-stack:
  added: [pytest]
  patterns:
    - "bytes-first template handling (no str.strip / no implicit newline normalization)"
    - "dual-entrypoint test module (pytest __main__)"
key-files:
  created:
    - .gitattributes
    - scripts/capture_golden.py
    - tests/__init__.py
    - tests/golden/palserver.service.v0_1_19
    - tests/test_palworld_golden.py
  modified: []
decisions:
  - "Golden file stored as raw bytes (not JSON or binary-serialization wrapper) — matches on-disk systemd unit format for interactive diff."
  - "Harness is import-free from logpose — survives a busted logpose/main.py so the template/golden contract always gets checked."
  - "Fixture hardcodes string paths (not Path objects) so str.format rendering is unambiguous across platforms."
metrics:
  completed: 2026-04-12
  tasks: 3
  files: 5
  commits: 3
---

# Phase 02 Plan 01: Golden Fixture and Harness Summary

Byte-diff regression harness anchoring every subsequent Palworld refactor: a 383-byte golden file captured from the v0.1.19 `palserver.service.template` against the locked fixture (user=foo, port=8211, players=32), plus a dual-entrypoint pytest module (pytest + `__main__` script).

## Artifacts

| Path | Bytes | SHA-256 |
| ---- | ----- | ------- |
| `tests/golden/palserver.service.v0_1_19` | 383 | `b84d069a30552cff6960ace3dabc2dbab0142d2621de637d56147324ac77d02f` |
| `tests/test_palworld_golden.py` | — | 2 test functions, import-free from logpose |
| `scripts/capture_golden.py` | — | idempotent; re-running leaves golden sha256 unchanged |
| `.gitattributes` | 2 rules | `logpose/templates/*.template -text`, `tests/golden/** -text` |
| `tests/__init__.py` | 1 byte | package marker (newline only) |

## Commits

| Task | Commit | Message |
| ---- | ------ | ------- |
| 1 | `8cfc279` | chore(02-01): add .gitattributes to preserve template EOF bytes |
| 2 | `e525617` | feat(02-01): capture v0.1.19 palserver.service golden file |
| 3 | `eaa56da` | test(02-01): add dual-entrypoint byte-diff regression harness |

## Verification Results

- `pytest tests/test_palworld_golden.py -x` → `2 passed in 0.32s`, exit **0**.
- `python tests/test_palworld_golden.py` → `OK: palserver.service matches v0.1.19 golden`, exit **0**.
- `wc -c tests/golden/palserver.service.v0_1_19` → `383`.
- Golden bytes end with `65 74 20` (`et `, space, no newline) — verified via Python `bytes.endswith(b'et ')`.
- `git check-attr -a logpose/templates/palserver.service.template` → `text: unset`.
- `git check-attr -a tests/golden/palserver.service.v0_1_19` → `text: unset`.
- Capture-script idempotency: sha256 unchanged after second `python scripts/capture_golden.py` invocation.
- v0.1.19-tag paranoia test: verified `git show v0.1.19:palworld_server_launcher/templates/palserver.service.template` bytes equal current template bytes.

## Negative-Path Verification

Hand-check confirming the harness is a real oracle (not a tautology):

1. Backed up template: `cp logpose/templates/palserver.service.template /tmp/palserver.service.template.bak`.
2. Mutated by one byte: `printf 'X' >> logpose/templates/palserver.service.template` → template now 324 bytes.
3. `pytest tests/test_palworld_golden.py -x` → **exit 1**, `FAILED test_palserver_service_byte_identical_to_v0_1_19` with clear diagnostic: `rendered=384 bytes, golden=383 bytes`.
4. `python tests/test_palworld_golden.py` → **exit 1**, prints `FAIL: test_palserver_service_byte_identical_to_v0_1_19: ...` with same diagnostic to stderr.
5. Restored: `cp /tmp/palserver.service.template.bak logpose/templates/palserver.service.template`.
6. Re-verified: template back to 323 bytes, sha256 matches pre-mutation snapshot, harness green on both entrypoints.

## Deviations from Plan

### 1. [Rule 3 - Plan spec error] Golden file is 383 bytes, not 323

- **Found during:** Task 2 (capture script run).
- **Issue:** Plan's `must_haves.truths` and acceptance criteria claimed the golden file must be exactly 323 bytes. This conflates the **template** size (323 bytes, the source .template file) with the **rendered output** size (383 bytes after `str.format` substitution expands the `{user}`/`{working_directory}`/`{exec_start_path}`/`{port}`/`{players}` placeholders).
- **Evidence:** Rendering the v0.1.19 tag's own template via `git show v0.1.19:palworld_server_launcher/templates/palserver.service.template` against the same fixture produces 383 bytes with sha256 `b84d069a...` — exactly matching the locally captured golden. The v0.1.19-faithfulness invariant (which is the real requirement) is preserved; only the byte-count number in the plan was wrong.
- **Fix:** Proceeded with the mathematically correct 383-byte golden. Capture script, harness, and docstrings reflect the actual size. The template (323 bytes, trailing space no newline) is unchanged and tested via the second harness function `test_golden_matches_v0_1_19_tag`.
- **Files modified:** `tests/golden/palserver.service.v0_1_19` (383 bytes).
- **Commit:** `e525617` (commit body documents the deviation inline).

### 2. [Rule 3 - Plan spec error] xxd EOF grep pattern

- **Found during:** Task 2 verify block.
- **Issue:** Plan's `verify.automated` used `xxd tests/golden/palserver.service.v0_1_19 | tail -1 | grep -q 'et 20$'`. `xxd`'s default output format packs bytes into 2-byte groups with no space between `65 74` (`et`) and `20` (space) — the actual tail line hex column shows `6574 20`. The regex `'et 20$'` does not match that output.
- **Fix:** Verified the real invariant programmatically: `open('...','rb').read().endswith(b'et ')` → `True`. The plan's grep was a verify-line bug; the underlying property (trailing space, no newline) holds.
- **Files modified:** none — verification approach corrected inline.

### 3. [Rule 2 - Scoped staging guard] Concurrent 02-02 commits in worktree

- **Found during:** pre-commit status check before Task 2.
- **Issue:** The worktree contains modifications from a concurrent 02-02 agent (`logpose/main.py` modified; commits `ec71cba`, `6e70262` visible in `git log`). These are a parallel wave-1 plan's work, not pre-existing slop.
- **Fix:** Used `git add <specific-files>` for every task commit — never `git add .` or `git add -A`. Task commits contain exclusively 02-01 files.
- **Files modified:** none — scoped commits via explicit file staging.

## Key Decisions

- **Bytes-first, not text-first.** Template read as bytes, decoded for `str.format`, re-encoded for comparison. Protects against implicit newline-normalization in any editor or CI step. Mirrored by `.gitattributes -text` rule.
- **No dependency on `logpose.main` in the harness.** The second harness file (Plan 05, deferred) will exercise the real `_render_service_file` code path. This harness stays minimal and fires even on a busted `logpose/main.py` — maximizing the regression signal.
- **Idempotent capture script, not one-shot-only.** `scripts/capture_golden.py` can be re-run safely. If the template ever legitimately changes, re-running the script and the diff in the commit will be the operator's first diagnostic.
- **`pytest.skip` for v0.1.19-tag test when git is unavailable.** The harness still passes in wheel-install / no-repo environments; the drift guard degrades to a no-op rather than a hard fail.

## Known Stubs

None — no placeholder values, empty returns, or mock data introduced.

## Self-Check: PASSED

- `.gitattributes` exists: FOUND.
- `scripts/capture_golden.py` exists: FOUND.
- `tests/__init__.py` exists: FOUND.
- `tests/golden/palserver.service.v0_1_19` exists (383 bytes, sha `b84d069a...`): FOUND.
- `tests/test_palworld_golden.py` exists (2 tests, dual entrypoint, no logpose import): FOUND.
- Commit `8cfc279` (chore): FOUND.
- Commit `e525617` (feat): FOUND.
- Commit `eaa56da` (test): FOUND.
