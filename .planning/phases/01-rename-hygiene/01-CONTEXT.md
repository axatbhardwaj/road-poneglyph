# Phase 1: Rename + Hygiene - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss) — REQUIREMENTS.md + research/SUMMARY.md are the spec

<domain>
## Phase Boundary

Repo carries the `logpose` identity cleanly — package path, distribution name, pinned deps, and tree hygiene all align before any behavioral change. No refactoring, no game logic changes — pure mechanical rename + dependency hygiene.

Covers requirements: PKG-01 (package dir rename), PKG-02 (pyproject name/entry), PKG-03 (pinned deps), PKG-04 (Python 3.8 floor preserved), PKG-05 (`from __future__ import annotations`), PKG-06 (egg-info scrubbed). Also continuous invariants: ARCH-05 (no `core/`), ARCH-06 (helper signatures unchanged), PAL-01/02/06 (Palworld service/template/launch-args byte-identical).

</domain>

<decisions>
## Implementation Decisions

### Distribution & Entry Point
- **Distribution name**: `logpose-launcher` (`logpose` is taken on PyPI per research verification 2026-04-12)
- **CLI script**: `logpose = "logpose.main:app"` (CLI name + import name both `logpose`)
- **Package directory**: `palworld_server_launcher/` → `logpose/` via `git mv` (preserves history)

### Dependency Pinning
- `typer>=0.9,<0.21` — Typer 0.21 dropped Python 3.8 support on 2025-12-25
- `rich>=13.0,<14` — floor matches Typer compatibility band
- `requires-python = ">=3.8"` kept as-is

### Python 3.8 Compat
- Every module in `logpose/` gets `from __future__ import annotations` as first statement (after the module docstring if present) — PEP-585 generics (`dict[str, str]`) work at import time on 3.8

### Hygiene
- `git rm -r --cached palworld_server_launcher.egg-info/` — stale egg-info corrupts the new wheel build
- Add `.gitignore` entries: `*.egg-info/`, `build/`, `dist/`, `__pycache__/`, `*.pyc`

### Claude's Discretion
- Commit granularity: one commit per logical change (rename, pyproject, gitignore, egg-info scrub, future-annotations)
- Whether to also scrub existing `dist/` directory from working tree (it's untracked; leave alone)
- Whether to also update the `description` field in pyproject.toml (yes — it says "Palworld dedicated server"; should mention multi-game)

</decisions>

<code_context>
## Existing Code Insights

- Single-file Python package: `palworld_server_launcher/__init__.py` (likely empty marker) + `palworld_server_launcher/main.py` (~400 lines, Typer app)
- `palworld_server_launcher/templates/` contains `palserver.service.template` and `palserver.rules.template`
- `palworld_server_launcher.egg-info/` is currently tracked in git (visible in git status as modified)
- `pyproject.toml` uses setuptools with `packages = ["palworld_server_launcher"]` and `package-data = { "palworld_server_launcher" = ["templates/*"] }`
- Current `main.py` uses PEP-585 generics in signatures (`dict[str, str]`) — works on 3.8 only because Typer lazy-introspects annotations

</code_context>

<specifics>
## Specific Ideas

- Use `git mv` (not `mv` + `git add`) for the directory rename so history is preserved
- After rename, pyproject.toml `[tool.setuptools]` section needs `packages = ["logpose"]` AND `[tool.setuptools.package-data]` needs `"logpose" = ["templates/*"]` — both keys change
- `from __future__ import annotations` goes ABOVE any other import (first import statement) — convention is to place it immediately after the module docstring
- egg-info scrub: `git rm -r --cached palworld_server_launcher.egg-info` then commit; physical directory can stay on disk (`rm -rf` separately if user cares)

</specifics>

<deferred>
## Deferred Ideas

- Actually publishing to PyPI — deferred to Phase 6
- README rewrite — partial update in Phase 4 (CLI examples), final in Phase 6
- Removing `docs/` or `.pdf` from git tracking — out of scope for this phase
- Updating `palworld_server_launcher.egg-info/PKG-INFO` regeneration — irrelevant once we move to `logpose-launcher`

</deferred>

---

*Phase: 01-rename-hygiene*
*Context gathered: 2026-04-12 (auto-generated, skip_discuss mode)*
