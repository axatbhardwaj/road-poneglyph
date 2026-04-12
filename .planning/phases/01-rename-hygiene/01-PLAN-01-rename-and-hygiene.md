# Plan 01.01: Rename package and land hygiene

**Phase:** 1 — Rename + Hygiene
**Plan:** 01 of 01
**Created:** 2026-04-12
**Estimated size:** Small (5 atomic commits, pure mechanical)

## Goal

Rename `palworld_server_launcher/` → `logpose/`, update `pyproject.toml` for the new distribution name `logpose-launcher` with pinned deps, add `from __future__ import annotations` to every module, scrub tracked `*.egg-info/`, and update `.gitignore`. No behavioral changes — Palworld install/start/stop paths must still work end-to-end (though this phase doesn't verify that; Phase 2 does).

## Requirements covered

- **PKG-01** — package dir rename via `git mv`
- **PKG-02** — pyproject.toml `name`, `description`, `[project.scripts]`, `[tool.setuptools].packages`, `[tool.setuptools.package-data]`
- **PKG-03** — pinned deps (`typer>=0.9,<0.21`, `rich>=13.0,<14`)
- **PKG-04** — `requires-python = ">=3.8"` preserved
- **PKG-05** — `from __future__ import annotations` on every module
- **PKG-06** — `git rm -r --cached palworld_server_launcher.egg-info/` + `.gitignore` entries

## Atomic steps (one commit each)

### Step 1: Remove tracked egg-info from git + update .gitignore

Before the rename — clean slate for the new package.

```bash
git rm -r --cached palworld_server_launcher.egg-info/
```

Create or update `.gitignore` to include:
```
__pycache__/
*.pyc
*.pyo
*.egg-info/
build/
dist/
.pytest_cache/
.venv/
venv/
```

Commit message: `chore: scrub stale egg-info and tighten .gitignore`

### Step 2: Rename package directory with git mv

```bash
git mv palworld_server_launcher logpose
```

This preserves rename detection in git log — `git log --follow logpose/main.py` will show the pre-rename history.

Commit message: `refactor: rename package palworld_server_launcher → logpose`

### Step 3: Update pyproject.toml for logpose-launcher

Edit `pyproject.toml`:
- `[project]` section:
  - `name = "logpose-launcher"` (was `"palworld-server-launcher"`)
  - `description = "A Linux dedicated game server launcher for Palworld and ARK: Survival Evolved, managing steamcmd + systemd + polkit."` (was Palworld-only)
  - Leave `requires-python = ">=3.8"`, `authors`, `license`, `readme`, `classifiers` intact
- `dependencies`:
  - `"typer>=0.9,<0.21"` (was `"typer"`)
  - `"rich>=13.0,<14"` (was `"rich"`)
- `[project.scripts]`:
  - `logpose = "logpose.main:app"` (was `palworld-server-launcher = "palworld_server_launcher.main:app"`)
- `[tool.setuptools]`:
  - `packages = ["logpose"]` (was `["palworld_server_launcher"]`)
- `[tool.setuptools.package-data]`:
  - `"logpose" = ["templates/*"]` (was `"palworld_server_launcher" = ["templates/*"]`)

Commit message: `chore: rename distribution to logpose-launcher and pin deps for py3.8`

### Step 4: Add `from __future__ import annotations` to every module

Target files (after the rename in Step 2):
- `logpose/__init__.py`
- `logpose/main.py`

For each file, ensure the first non-docstring non-comment line is:
```python
from __future__ import annotations
```

If the file already has a docstring, the future-import goes immediately after it.

Commit message: `fix: enable PEP-585 annotations on python 3.8 via __future__`

### Step 5: (optional) Verify by building sdist locally

```bash
python -m build --sdist 2>&1 | tail
ls dist/
```

Expected: `dist/logpose_launcher-0.1.19.tar.gz` (or similar — version bump happens in Phase 6). The build succeeding with the new name is proof of Step 3's correctness. Verification only — do NOT commit `dist/`. If `build` isn't installed, skip; README will cover release.

No commit for Step 5 — it's verification, not a change.

## Success criteria (exit gates)

1. `logpose/` directory exists; `palworld_server_launcher/` no longer exists in tree
2. `git log --follow logpose/main.py` shows pre-rename history (rename detection works)
3. `pyproject.toml` contains `name = "logpose-launcher"`, pinned typer + rich, `packages = ["logpose"]`
4. `git ls-files logpose/ | xargs head -3` shows `from __future__ import annotations` on `logpose/__init__.py` and `logpose/main.py`
5. `git ls-files palworld_server_launcher.egg-info 2>&1 | wc -l` returns `0` (egg-info untracked)
6. `.gitignore` contains `*.egg-info/`, `build/`, `dist/`, `__pycache__/`
7. `python -c "import logpose.main"` (from a venv after `pip install -e .`) succeeds on Python 3.8

## Out of scope (this plan)

- Any change to `logpose/main.py` beyond the future-annotations line — DO NOT refactor, DO NOT introduce GAMES dict, DO NOT touch templates
- Any change to the templates directory contents
- README rewrite — Phase 4/6
- PyPI publish — Phase 6
- Version bump — Phase 6

## Risks

- **Template path break**: If `_get_template()` hardcodes the old package name in string, Palworld install will fail post-rename. Mitigation: the existing code uses `Path(__file__).parent / "templates"` which is path-relative — immune to the rename. Verified against current main.py line 39.
- **Stale egg-info on disk**: `git rm --cached` leaves the directory on disk (untracked). Harmless, but `python -m build` will regenerate fresh. Optional cleanup: `rm -rf palworld_server_launcher.egg-info/` after Step 1.
