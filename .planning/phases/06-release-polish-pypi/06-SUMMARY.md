---
phase: 06-release-polish-pypi
status: partial
plans_complete: 2
plans_total: 4
plans_pending_human: [06-03, 06-04]
tags: [pypi, release, v0.2.0, multi-game, human-gated]
completed_date: 2026-04-13
---

# Phase 6: Release Polish + PyPI — Partial Summary (2 of 4 plans complete)

This phase ships `logpose-launcher` v0.2.0 to PyPI. The two **autonomous** plans (06-01 version bump + clean build, 06-02 README rewrite) have been executed in wave 1. The remaining two plans (06-03 TestPyPI dry-run, 06-04 production PyPI upload) are **human-gated** — they require live API tokens and are deliberately NOT executed by Claude.

## Executed autonomous plans

### Plan 06-01 — Bump version → 0.2.0, clean build, verify wheel METADATA

- **Status:** ✅ Complete
- **Commits:** `82baeab` (version bump), `348bb88` (summary)
- **Outputs:**
  - `pyproject.toml` @ `version = "0.2.0"`
  - `dist/logpose_launcher-0.2.0-py3-none-any.whl` (17 360 bytes)
  - `dist/logpose_launcher-0.2.0.tar.gz` (19 658 bytes)
- **E2E-05 satisfied:** wheel METADATA shows `Name: logpose-launcher` + `Version: 0.2.0`.
- **Per-plan details:** see `06-01-SUMMARY.md`.

### Plan 06-02 — Rewrite README for multi-game CLI

- **Status:** ✅ Complete
- **Commits:** `9f83330` (README rewrite), `7bad6e3` (summary)
- **Outputs:**
  - `README.md` rewritten (28 → 247 lines; 199 insertions, 28 deletions)
  - `dist/logpose_launcher-0.2.0.tar.gz` rebuilt to embed the new README as the PyPI long description
- **PKG-08 satisfied:** both games' verb examples, migration note, firewall table, manual Polkit cleanup all present.
- **POL-04 satisfied:** README tells v0.1.19 users to remove `/etc/polkit-1/rules.d/40-palserver.rules` after confirming v0.2.0 works.
- **Per-plan details:** see `06-02-SUMMARY.md`.

## Pending human-gated plans

| Plan | What | Human gate |
|------|------|-----------|
| 06-03 | TestPyPI dry-run upload + rendering check at `https://test.pypi.org/project/logpose-launcher/0.2.0/` | Requires TestPyPI API token |
| 06-04 | Production PyPI upload to `https://pypi.org/project/logpose-launcher/0.2.0/` | Requires production PyPI API token |

Both plans consume the same `dist/logpose_launcher-0.2.0-*` artefacts produced by Plan 06-01 (and re-emitted after the README rewrite in Plan 06-02). No further code changes are expected — 06-03 and 06-04 are `twine upload` invocations plus visual verification.

## Test and invariant status after wave 1

- Byte-diff harness: `6 passed in 0.09s` (4 palworld + 2 ark) — template rendering unaffected by version bump and README rewrite.
- PKG-06 invariant: `dist/`, `build/`, `*.egg-info/` remain gitignored; `git status --short` shows no tracked artefacts.
- v0.1.19 `palworld-server-launcher` PyPI release remains untouched (no PyPI actions taken yet).

## Deviations (wave 1)

- **Plan 06-01:** System `python3` lacked the `build` and `pytest` modules. Installed `python3-build` + `python3-pip` via `apt-get install` (system-level, no repo change). Ran `pytest` via the pre-existing `.venv/` which carries it. No impact on deliverables.
- **Plan 06-02:** No deviations. Plan executed exactly as written.

## Deferred (logged to `deferred-items.md`)

- **DI-1:** `logpose/templates/CLAUDE.md` is packaged inside the wheel because the `package-data` glob is `templates/*` (too wide). 1.1 KB payload, harmless but non-ideal. Fix belongs in a focused packaging-polish plan that can re-run the byte-diff harness after tightening the glob.

## Handoff to wave 2 (human-gated)

1. Operator obtains a TestPyPI API token (scope: project `logpose-launcher` on test.pypi.org).
2. Operator runs Plan 06-03 (`twine upload --repository testpypi dist/*`), then visually checks that the project page at https://test.pypi.org/project/logpose-launcher/0.2.0/ renders the rewritten README correctly (headings, tables, fenced code).
3. On pass, operator obtains a production PyPI API token and runs Plan 06-04 (`twine upload dist/*`).
4. After 06-04, `pip install logpose-launcher` on a clean box should install v0.2.0 and `logpose --version` should print `0.2.0`.

At that point Phase 6 closes and milestone v0.2.0 ships.
