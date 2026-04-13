---
phase: 06-release-polish-pypi
plan: 01
subsystem: packaging
tags: [pypi, version-bump, wheel, sdist, metadata, E2E-05]
requires:
  - Phase 1 PKG-02 (name = "logpose-launcher" established)
  - Phase 1 PKG-06 (dist/, build/, *.egg-info/ gitignored)
  - Phase 5 (byte-diff harness at 6 tests — 4 palworld + 2 ark)
provides:
  - dist/logpose_launcher-0.2.0-py3-none-any.whl
  - dist/logpose_launcher-0.2.0.tar.gz
  - pyproject.toml @ version = "0.2.0"
affects:
  - Plan 06-03 (TestPyPI dry-run — consumes these artefacts)
  - Plan 06-04 (Production PyPI upload — consumes these artefacts)
tech_stack_added: []
tech_stack_patterns: [setuptools build_meta, python-build PEP 517 frontend]
key_files_created: []
key_files_modified:
  - pyproject.toml
decisions:
  - Version-only delta (no classifier/description touch) to keep v0.1.19→v0.2.0 diff minimal.
  - System python3 (3.13.5) + python3-build from apt used as PEP 517 frontend; .venv used for pytest run.
metrics:
  duration_minutes: ~5
  completed_date: 2026-04-13
  tasks_completed: 2
  tests_passing: 6
---

# Phase 6 Plan 01: Bump version → 0.2.0, clean build, verify wheel METADATA

One-liner: bumped `pyproject.toml` to 0.2.0 and produced a clean `logpose_launcher-0.2.0` wheel + sdist whose METADATA correctly advertises `Name: logpose-launcher` / `Version: 0.2.0` — E2E-05 ✅.

## Task 1 — Version bump

Single-line diff against `pyproject.toml`:

```diff
-version = "0.1.19"
+version = "0.2.0"
```

Verification: `grep -c '^version = "0.2.0"$' pyproject.toml` → `1`.

Commit: `82baeab` — `chore(06-01): bump version to 0.2.0 for logpose-launcher PyPI release`.

## Task 2 — Clean build + wheel metadata

### Environment setup (deviation — see below)

`python3 -m build` was not installed. Installed `python3-build` and `python3-pip` via `apt-get install -y python3-pip python3-build` (Debian 13 trixie, Python 3.13.5 from system). No changes to the repository.

### Build

```
rm -rf build/ dist/ *.egg-info/
python3 -m build
```

Result: `Successfully built logpose_launcher-0.2.0.tar.gz and logpose_launcher-0.2.0-py3-none-any.whl`.

### dist/ listing

```
-rw-r--r-- 1 root root 17360 Apr 13 22:58 logpose_launcher-0.2.0-py3-none-any.whl
-rw-r--r-- 1 root root 19658 Apr 13 22:58 logpose_launcher-0.2.0.tar.gz
```

### Wheel METADATA (first 14 lines)

```
Metadata-Version: 2.4
Name: logpose-launcher
Version: 0.2.0
Summary: A Linux dedicated game server launcher for Palworld and ARK: Survival Evolved — manages steamcmd, systemd, and polkit on Debian/Ubuntu.
Author-email: axatbhardwaj <axatbhardwaj@gmail.com>
License-Expression: MIT
Classifier: Programming Language :: Python :: 3
Classifier: Operating System :: POSIX :: Linux
Requires-Python: >=3.8
Description-Content-Type: text/markdown
License-File: LICENSE
Requires-Dist: typer<0.21,>=0.9
Requires-Dist: rich<14,>=13.0
Dynamic: license-file
```

`Name:` + `Version:` sort:
```
Name: logpose-launcher
Version: 0.2.0
```

E2E-05 ✅.

### Template inventory inside wheel

```
      274  logpose/templates/40-logpose.rules.template
     1107  logpose/templates/CLAUDE.md
      296  logpose/templates/arkserver.service.template
       57  logpose/templates/logpose-ark.sudoers.template
      323  logpose/templates/palserver.service.template
```

All four required runtime templates present:
- `palserver.service.template` ✅
- `arkserver.service.template` ✅
- `40-logpose.rules.template` ✅
- `logpose-ark.sudoers.template` ✅

### Entry point

```
[console_scripts]
logpose = logpose.main:app
```

### Byte-diff harness

```
collected 6 items
tests/test_ark_golden.py ..                                              [ 33%]
tests/test_palworld_golden.py ....                                       [100%]
============================== 6 passed in 0.09s ===============================
```

Invoked via `.venv/bin/python -m pytest tests/ -x` (the project's pre-existing virtualenv carries pytest; system python3 lacks it).

### git status

```
 M uv.lock   (pre-existing, unrelated)
?? .planning/phases/04-typer-factory-merged-polkit/04-*-SUMMARY.md   (pre-existing, unrelated)
```

`dist/`, `build/`, `*.egg-info/` are NOT tracked (PKG-06 invariant holds).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Missing `build` and `pytest` on system python**
- **Found during:** Task 2 setup
- **Issue:** `python3 -m build` exited with `No module named build`. `python3 -m pytest` likewise unavailable. `pip` and `ensurepip` both missing from system python. The repository contains a pre-existing `.venv/` (Python 3.13.5) that carries pytest, logpose, markdown-it, pygmentize, typer — but no `build` and no `pip`.
- **Fix:** Installed `python3-pip` and `python3-build` via `apt-get install -y python3-pip python3-build` (Debian 13 apt, not repo-affecting). Ran `python3 -m build` using the system python3. Ran pytest via `.venv/bin/python -m pytest tests/ -x` as that is where pytest lives.
- **Files modified:** none (system package install only)
- **Commit:** n/a (no repo change)

### Deferred Issues (out of scope)

**1. `logpose/templates/CLAUDE.md` is being shipped inside the wheel.**
- **Detail:** The `[tool.setuptools.package-data] "logpose" = ["templates/*"]` glob in `pyproject.toml` pulls in `logpose/templates/CLAUDE.md` (1.1 KB LLM instructions file), which is not a runtime asset. Wheel stays small (17 KB total) so the impact is negligible, but a future polish plan could tighten the glob to `templates/*.template`.
- **Why deferred:** Out-of-scope per executor scope boundary — this plan's must_haves only require the four runtime templates to be present, and they all are. Introducing a glob change here would risk perturbing the byte-diff harness (reads templates at runtime) without user sign-off.
- **Logged to:** `.planning/phases/06-release-polish-pypi/deferred-items.md` (created by executor)

## Success Criteria

| Criterion | Result |
|-----------|--------|
| `grep -c '^version = "0.2.0"$' pyproject.toml` → 1 | ✅ 1 |
| Both `dist/logpose_launcher-0.2.0*.whl` + `.tar.gz` exist | ✅ both present, no other versions |
| Wheel METADATA `Name: logpose-launcher` + `Version: 0.2.0` | ✅ verified |
| `pytest tests/ -x` → 6 passed | ✅ 6 passed in 0.09s |

## Self-Check: PASSED

- FOUND: pyproject.toml @ version = "0.2.0" (grep confirms)
- FOUND: dist/logpose_launcher-0.2.0-py3-none-any.whl (17360 bytes)
- FOUND: dist/logpose_launcher-0.2.0.tar.gz (19658 bytes)
- FOUND commit 82baeab in `git log --oneline`

## Handoff

- Plan 06-02 (README rewrite) will need to rebuild `dist/` after editing README so the sdist carries the new long-description.
- Plan 06-03 (TestPyPI dry-run) consumes `dist/logpose_launcher-0.2.0-py3-none-any.whl` + `.tar.gz` via `twine upload --repository testpypi dist/*`.
- Plan 06-04 (production PyPI) consumes the same artefacts after Plan 06-03 verifies TestPyPI rendering.
