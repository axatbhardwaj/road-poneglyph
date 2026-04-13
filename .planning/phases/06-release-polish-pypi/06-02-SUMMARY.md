---
phase: 06-release-polish-pypi
plan: 02
subsystem: docs
tags: [readme, pypi-long-description, multi-game, migration, PKG-08, POL-04]
requires:
  - Plan 06-01 (version bump + python3-build installed)
  - Phase 4 (logpose palworld ... verbs finalised)
  - Phase 5 (logpose ark ... verbs finalised)
provides:
  - README.md rewritten for multi-game CLI
  - dist/logpose_launcher-0.2.0.tar.gz with new long-description embedded
affects:
  - Plan 06-03 (TestPyPI long-description rendering)
  - Plan 06-04 (production PyPI project page)
tech_stack_added: []
tech_stack_patterns: []
key_files_created: []
key_files_modified:
  - README.md
decisions:
  - Every verb gets a dedicated fenced command block plus a one-line explanation (the verifier's literal-string check does not care about formatting, but consistent examples read better on the PyPI project page).
  - Migration section explicitly spells out that `pip install --upgrade palworld-server-launcher` will NOT pull v0.2.0 — this is the single most likely confusion point for existing users.
  - Firewall section states plainly that logpose does NOT manage ufw/iptables; the user must open ports themselves.
  - ARK map list copied verbatim from the 12-map enum documented in 05-SUMMARY.md.
metrics:
  duration_minutes: ~8
  completed_date: 2026-04-13
  tasks_completed: 2
  tests_passing: 6
---

# Phase 6 Plan 02: Rewrite README for multi-game CLI

One-liner: rewrote `README.md` (28 → 247 lines) to document both Palworld and ARK as first-class sub-apps, added migration guidance from `palworld-server-launcher` v0.1.19 (including POL-04 Polkit cleanup), a firewall port reference table, and sections covering `/etc/sudoers.d/logpose-ark` + opt-in `arkserver.service`.

## Section tree (new README)

```
# logpose
├─ Features
├─ Prerequisites
├─ Installation
├─ Migration from palworld-server-launcher v0.1.19
├─ Quick Start
│  ├─ Palworld
│  └─ ARK: Survival Evolved
├─ Palworld Usage (`logpose palworld <verb>`)
├─ ARK Usage (`logpose ark <verb>`)
├─ Firewall / Port Reference
├─ Permissions & Security Model
├─ Version
├─ Supported OS
└─ License
```

## Line count

| | Before | After |
|-|-------:|------:|
| README.md | 77 | 247 |
| `git diff --stat` | | 199 insertions, 28 deletions |

## Task 1 — Rewrite verification

Automated verifier (from `<verify>` block of the plan) — checks all 9 Palworld verb examples + 11 ARK verb examples + 12 required literal strings:

```
OK
```

Exit code: `0`. No missing items.

| Requirement class | Count | All present? |
|-------------------|------:|:------------:|
| Palworld verb examples (`logpose palworld <verb>`) | 9 | ✅ |
| ARK verb examples (`logpose ark <verb>`) | 11 | ✅ |
| Required literal strings | 12 | ✅ |

Specific literal checks:
- `pip install logpose-launcher` ✅
- `logpose --version` ✅
- `40-palserver.rules` (migration cleanup) ✅
- `40-logpose.rules` (current merged rule) ✅
- `/etc/sudoers.d/logpose-ark` ✅
- `--enable-autostart` ✅
- `arkmanager` ✅
- Ports: 8211, 7777, 7778, 27015, 27020 ✅

Commit: `9f83330` — `docs(06-02): rewrite README for multi-game CLI (Palworld + ARK)`.

## Task 2 — sdist PKG-INFO spot-check

Rebuilt `dist/` after the README edit so the sdist ships the new long-description:

```
rm -rf build/ dist/ *.egg-info/
python3 -m build
```

First 14 lines of `logpose_launcher-0.2.0/PKG-INFO` inside the sdist:

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

`Description-Content-Type: text/markdown` ✅ (setuptools infers it from `readme = "README.md"` in `pyproject.toml`).

Grep check — `logpose ark install` appears **9** times in PKG-INFO (new README is embedded, not the old Palworld-only v0.1.19 text):

```
$ tar -xzf dist/logpose_launcher-0.2.0.tar.gz -O logpose_launcher-0.2.0/PKG-INFO | grep -c 'logpose ark install'
9
```

Byte-diff harness after the README rewrite + rebuild: `6 passed in 0.09s` (README changes cannot affect template rendering, but pinned as an exit gate).

## Success Criteria

| Criterion | Result |
|-----------|--------|
| Automated verifier exits 0 with `OK` | ✅ |
| PKG-INFO contains `logpose ark install` | ✅ (9 occurrences) |
| `git diff --stat README.md` ≥ 100 lines changed | ✅ (199 insertions, 28 deletions) |
| `git status --short` shows only README.md modified from this task | ✅ (Task 2 does not alter tracked files — dist/ + build/ gitignored) |

## Deviations from Plan

None. Plan executed exactly as written.

## Self-Check: PASSED

- FOUND: README.md @ 247 lines with `logpose ark install` examples
- FOUND: dist/logpose_launcher-0.2.0.tar.gz PKG-INFO contains new README
- FOUND commit 9f83330 in `git log --oneline`

## Handoff

- Plan 06-03 (TestPyPI dry-run) will upload `dist/logpose_launcher-0.2.0-py3-none-any.whl` + `dist/logpose_launcher-0.2.0.tar.gz` and visually confirm that https://test.pypi.org/project/logpose-launcher/0.2.0/ renders this README correctly (the "Project description" panel). Human-gated — needs a TestPyPI API token.
- Plan 06-04 (production PyPI) does the same against pypi.org after 06-03 passes. Human-gated — needs a PyPI API token.
- The README as-of commit `9f83330` is the canonical v0.2.0 long description.
