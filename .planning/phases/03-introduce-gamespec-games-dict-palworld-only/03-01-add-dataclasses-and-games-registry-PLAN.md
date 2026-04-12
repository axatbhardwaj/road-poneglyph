---
phase: 03-introduce-gamespec-games-dict-palworld-only
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - logpose/main.py
autonomous: true
requirements: [ARCH-01, ARCH-02, ARCH-03]
tags: [refactor, dataclasses, registry, python, palworld]

must_haves:
  truths:
    - "SettingsAdapter is defined as a frozen dataclass with parse + save callable fields."
    - "GameSpec is defined as a frozen dataclass with all 14 fields in the ARCHITECTURE.md + ROADMAP schema."
    - "GAMES: dict[str, GameSpec] is defined at module scope in logpose/main.py with exactly one entry keyed 'palworld'."
    - "All existing PAL_* module globals remain untouched in this plan — both the new GAMES registry and the old globals coexist reachable in the module."
    - "python -c 'import logpose.main' succeeds — no NameError, no FrozenInstanceError, no mutable-default error."
    - "pytest tests/test_palworld_golden.py -x exits 0 (all 3 tests green) — byte-diff exit gate."
  artifacts:
    - path: "logpose/main.py"
      provides: "SettingsAdapter + GameSpec dataclasses + GAMES registry alongside existing PAL_* globals"
      contains: "@dataclass(frozen=True)\\nclass SettingsAdapter"
    - path: "logpose/main.py"
      provides: "GameSpec dataclass with 14 fields"
      contains: "@dataclass(frozen=True)\\nclass GameSpec"
    - path: "logpose/main.py"
      provides: "Module-scope GAMES registry keyed 'palworld'"
      contains: "GAMES: dict[str, GameSpec]"
  key_links:
    - from: "GameSpec.settings_adapter"
      to: "SettingsAdapter"
      via: "field type annotation + runtime reference at GAMES construction"
      pattern: "settings_adapter=SettingsAdapter\\(parse=_palworld_parse, save=_palworld_save\\)"
    - from: "GAMES['palworld'].post_install_hooks"
      to: "_palworld_sdk_hook (zero-arg closure over _fix_steam_sdk)"
      via: "list element in post_install_hooks"
      pattern: "post_install_hooks=\\[_palworld_sdk_hook\\]"
    - from: "tests/test_palworld_golden.py"
      to: "logpose.main._render_service_file"
      via: "deferred import in Test #3"
      pattern: "from logpose.main import _render_service_file"
---

<objective>
Introduce the `SettingsAdapter` + `GameSpec` frozen dataclasses and a module-scope `GAMES: dict[str, GameSpec]` registry with a single `"palworld"` entry in `logpose/main.py`. All existing `PAL_*` module globals and the current `install()` / `edit_settings()` / `update()` call sites remain UNCHANGED in this plan — the goal is to land the dataclasses and registry additively so the byte-diff harness stays green while subsequent plans switch call sites over.

Purpose: ARCH-01 (GameSpec), ARCH-02 (SettingsAdapter), ARCH-03 (GAMES registry) are closed by the mere existence of correctly-typed, frozen dataclass definitions and a module-scope registry. This plan closes them structurally; plans 03-02 and 03-03 finish ARCH-04 / PAL-05 / PAL-08 by dissolving globals and wiring the hook.

Output: A single commit that adds ~60 lines to `logpose/main.py` (two `@dataclass(frozen=True)` blocks, one `_palworld_sdk_hook` closure, one `GAMES` literal) and leaves every existing line untouched. `pytest tests/test_palworld_golden.py -x` stays green (3/3 tests pass).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/research/ARCHITECTURE.md
@.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-RESEARCH.md
@logpose/main.py
@tests/test_palworld_golden.py
@CLAUDE.md
@logpose/CLAUDE.md

<interfaces>
<!-- Key types the executor needs. Extracted directly from 03-RESEARCH.md and logpose/main.py. -->
<!-- Executor should use these verbatim — no codebase exploration needed. -->

## SettingsAdapter dataclass (ARCH-02)

```python
@dataclass(frozen=True)
class SettingsAdapter:
    """Per-game settings file I/O. Two callables, no state."""
    parse: Callable[[Path], dict[str, str]]
    save: Callable[[Path, dict[str, str]], None]
```

## GameSpec dataclass — 14 fields (ARCH-01)

```python
@dataclass(frozen=True)
class GameSpec:
    """Frozen per-game configuration. Populated once at module scope in GAMES."""
    key: str
    display_name: str
    app_id: int
    server_dir: Path
    binary_rel_path: str
    settings_path: Path
    default_settings_path: Optional[Path]
    settings_section_rename: Optional[tuple[str, str]]
    service_name: str                       # bare name, no ".service" suffix
    service_template_name: str
    settings_adapter: SettingsAdapter
    post_install_hooks: list[Callable[[], None]] = field(default_factory=list)
    apt_packages: list[str] = field(default_factory=list)
    steam_sdk_paths: list[tuple[Path, Path]] = field(default_factory=list)
    install_options: dict[str, object] = field(default_factory=dict)
```

Field count: 15 annotations but `SettingsAdapter` is one field; the ROADMAP "14 fields" counts the GameSpec fields listed in the Phase 3 Success Criterion #1 verbatim:
  key, display_name, app_id, server_dir, binary_rel_path, settings_path,
  default_settings_path, settings_section_rename, service_name,
  service_template_name, settings_adapter, post_install_hooks,
  apt_packages, steam_sdk_paths, install_options
  = 15 names. ROADMAP line 53 enumerates 15 names but calls them "14 fields" — match the enumerated list exactly. Success criterion is satisfied when every name in the ROADMAP list exists as a dataclass field.

## _palworld_sdk_hook closure (PAL-08 prep — wired in Plan 03-03)

```python
_PAL_SERVER_DIR_LOCAL = STEAM_DIR / "steamapps/common/PalServer"
_PAL_STEAM_CLIENT_SO = STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"
_PAL_SDK64_DST = Path.home() / ".steam/sdk64"


def _palworld_sdk_hook() -> None:
    """Palworld post-install hook: copy steamclient.so into sdk64 (PAL-08)."""
    _fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)
```

Note: underscore-prefixed `_PAL_*` names are module-private helper locals used ONLY to construct `GAMES["palworld"]` and the hook. They are NOT the same as the existing `PAL_SERVER_DIR` etc. module globals that `install()` currently reads — those stay in place through this plan and are removed in Plan 03-02.

## GAMES["palworld"] literal (ARCH-03)

```python
GAMES: dict[str, GameSpec] = {
    "palworld": GameSpec(
        key="palworld",
        display_name="Palworld",
        app_id=2394010,
        server_dir=_PAL_SERVER_DIR_LOCAL,
        binary_rel_path="PalServer.sh",
        settings_path=_PAL_SERVER_DIR_LOCAL / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini",
        default_settings_path=_PAL_SERVER_DIR_LOCAL / "DefaultPalWorldSettings.ini",
        settings_section_rename=(
            "[/Script/Pal.PalWorldSettings]",
            "[/Script/Pal.PalGameWorldSettings]",
        ),
        service_name="palserver",
        service_template_name="palserver.service.template",
        settings_adapter=SettingsAdapter(parse=_palworld_parse, save=_palworld_save),
        post_install_hooks=[_palworld_sdk_hook],
        apt_packages=[],
        steam_sdk_paths=[(_PAL_STEAM_CLIENT_SO, _PAL_SDK64_DST)],
        install_options={"port_default": 8211, "players_default": 32},
    ),
}
```

## Existing functions referenced (do NOT modify in this plan)

- `_palworld_parse(path: Path) -> dict[str, str]` — logpose/main.py:200
- `_palworld_save(path: Path, settings: dict[str, str]) -> None` — logpose/main.py:214
- `_fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path) -> None` — logpose/main.py:146
- `STEAM_DIR = Path.home() / ".steam/steam"` — logpose/main.py:19 (stays; game-agnostic)

## Ordering constraint (module source layout)

In `logpose/main.py`, the new code must be inserted in this order:

1. `STEAM_DIR` — already at line 19, unchanged.
2. Existing `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` — already at lines 20–22, unchanged.
3. `from dataclasses import dataclass, field` — add to the imports block at the top of the file (after `from typing import Optional` around line 10).
4. `from typing import Callable` — add to the `from typing import Optional` line (merge: `from typing import Callable, Optional`).
5. NEW: `@dataclass(frozen=True) class SettingsAdapter` — must come before `GameSpec`. Suggested location: immediately after the existing module-global constants block (after line 22, before the first `def _get_os_id():` at line 25). The existing functions (`_palworld_parse`, `_palworld_save`, `_fix_steam_sdk`) are defined LATER in the file, so direct runtime references to them at module top-level would NameError.
6. NEW: `@dataclass(frozen=True) class GameSpec` — immediately after `SettingsAdapter`.
7. NEW: `_PAL_SERVER_DIR_LOCAL`, `_PAL_STEAM_CLIENT_SO`, `_PAL_SDK64_DST`, `_palworld_sdk_hook`, and `GAMES` — MUST be placed AFTER `_palworld_parse`, `_palworld_save`, and `_fix_steam_sdk` are defined (they are referenced in the `GAMES["palworld"]` literal at runtime). Suggested location: between `_interactive_edit_loop` (ends around line 307) and the first `@app.command()` decorator at line 310.

This ordering avoids `NameError` at import time while keeping the dataclass definitions near the top (discoverable) and the GAMES construction adjacent to the code that consumes it (the `@app.command()` block).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add SettingsAdapter + GameSpec dataclass definitions + imports</name>
  <files>logpose/main.py</files>
  <action>
Open `logpose/main.py`. Make three edits:

1. **Update imports.** Locate `from typing import Optional` (around line 10). Replace with:
   ```python
   from typing import Callable, Optional
   ```
   Immediately above it, add:
   ```python
   from dataclasses import dataclass, field
   ```
   (Insert the `dataclasses` import on its own line so existing `# noqa` / formatting conventions are untouched.)

2. **Insert dataclass definitions.** After the existing module-globals block (`DEFAULT_PAL_SETTINGS_PATH = …` at line 22), add a single blank line and then append the two frozen dataclasses verbatim from the `<interfaces>` block above:
   - `SettingsAdapter` — 2 callable fields (`parse`, `save`).
   - `GameSpec` — 15 annotations covering the 14 ROADMAP-named fields (`key`, `display_name`, `app_id`, `server_dir`, `binary_rel_path`, `settings_path`, `default_settings_path`, `settings_section_rename`, `service_name`, `service_template_name`, `settings_adapter`, `post_install_hooks`, `apt_packages`, `steam_sdk_paths`, `install_options`).

Use `field(default_factory=list)` for `post_install_hooks`, `apt_packages`, `steam_sdk_paths`; `field(default_factory=dict)` for `install_options`. All four mutable-default fields MUST use `field(default_factory=...)` — naked `= []` or `= {}` raises `ValueError: mutable default list is not allowed: use default_factory` under `@dataclass(frozen=True)`.

3. **Do NOT modify** any existing function body, any existing `@app.command()`, or any existing `PAL_SERVER_DIR` / `PAL_SETTINGS_PATH` / `DEFAULT_PAL_SETTINGS_PATH` line. Those survive this plan and are dissolved in Plan 03-02.

**WHY** (not `@dataclass` without frozen, not TypedDict, not plain dict): `research/ARCHITECTURE.md` locks frozen dataclass. Frozen enforces ARCH-04 invariant that no code mutates `GAMES` at runtime. `TypedDict` gives no runtime immutability. Plain dict violates type safety per CLAUDE.md + SUMMARY.md.

**WHY Callable import from typing, not collections.abc**: The project supports Python 3.8 (PKG-04); `collections.abc.Callable` as a generic subscription requires 3.9+. `typing.Callable` works across 3.8–3.12. Under `from __future__ import annotations` (already present at line 5), the runtime cost is zero.
  </action>
  <verify>
    <automated>cd /root/personal/palworld-server-launcher && .venv/bin/python -c "from logpose.main import SettingsAdapter, GameSpec; import dataclasses; assert dataclasses.is_dataclass(SettingsAdapter) and dataclasses.is_dataclass(GameSpec); assert SettingsAdapter.__dataclass_params__.frozen and GameSpec.__dataclass_params__.frozen; fields = {f.name for f in dataclasses.fields(GameSpec)}; expected = {'key','display_name','app_id','server_dir','binary_rel_path','settings_path','default_settings_path','settings_section_rename','service_name','service_template_name','settings_adapter','post_install_hooks','apt_packages','steam_sdk_paths','install_options'}; assert fields == expected, f'GameSpec field drift: missing={expected-fields} extra={fields-expected}'; print('OK: SettingsAdapter + GameSpec frozen dataclasses with 15 field names.')"</automated>
  </verify>
  <done>
- `logpose/main.py` imports `Callable` from `typing` and `dataclass, field` from `dataclasses`.
- `SettingsAdapter` is a `@dataclass(frozen=True)` with two `Callable` fields (`parse`, `save`).
- `GameSpec` is a `@dataclass(frozen=True)` with exactly the 15 named annotations listed in the interfaces block.
- `python -c "import logpose.main"` succeeds (no import error).
- All three fields with list defaults use `field(default_factory=list)`; the dict default uses `field(default_factory=dict)`.
- Existing `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`, `STEAM_DIR` and every existing function body are unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add GAMES registry + _palworld_sdk_hook closure (additive — call sites unchanged)</name>
  <files>logpose/main.py</files>
  <action>
Locate the end of `_interactive_edit_loop` (around line 307) — immediately before the first `@app.command()` decorator for `install` (around line 310). Insert the `_PAL_*` module-private helpers + `_palworld_sdk_hook` + `GAMES` dict VERBATIM from the `<interfaces>` block above:

```python
# --- Palworld post-install hook + GAMES registry (Phase 3 Plan 01) ---
# Module-private helpers bound once at import time. These are NOT the same as
# the existing PAL_SERVER_DIR / PAL_SETTINGS_PATH / DEFAULT_PAL_SETTINGS_PATH
# module globals (those dissolve in Plan 03-02). The underscore prefix signals
# "internal to GAMES construction" — nothing outside this block reads them.
_PAL_SERVER_DIR_LOCAL = STEAM_DIR / "steamapps/common/PalServer"
_PAL_STEAM_CLIENT_SO = STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"
_PAL_SDK64_DST = Path.home() / ".steam/sdk64"


def _palworld_sdk_hook() -> None:
    """Palworld post-install hook: copy steamclient.so into sdk64 (PAL-08)."""
    _fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)


GAMES: dict[str, GameSpec] = {
    "palworld": GameSpec(
        key="palworld",
        display_name="Palworld",
        app_id=2394010,
        server_dir=_PAL_SERVER_DIR_LOCAL,
        binary_rel_path="PalServer.sh",
        settings_path=_PAL_SERVER_DIR_LOCAL / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini",
        default_settings_path=_PAL_SERVER_DIR_LOCAL / "DefaultPalWorldSettings.ini",
        settings_section_rename=(
            "[/Script/Pal.PalWorldSettings]",
            "[/Script/Pal.PalGameWorldSettings]",
        ),
        service_name="palserver",
        service_template_name="palserver.service.template",
        settings_adapter=SettingsAdapter(parse=_palworld_parse, save=_palworld_save),
        post_install_hooks=[_palworld_sdk_hook],
        apt_packages=[],
        steam_sdk_paths=[(_PAL_STEAM_CLIENT_SO, _PAL_SDK64_DST)],
        install_options={"port_default": 8211, "players_default": 32},
    ),
}
```

**Critical ordering:** This block MUST come AFTER `_palworld_parse`, `_palworld_save`, and `_fix_steam_sdk` are defined in the file (they are referenced at construction time — not just in annotations). Placing it immediately before the first `@app.command()` satisfies this because all three helpers are defined above line 310 already.

**DO NOT** modify any existing `@app.command()` body. Every existing `install()` / `start()` / `update()` / `edit_settings()` call continues to read the OLD `PAL_SERVER_DIR` / `PAL_SETTINGS_PATH` / `DEFAULT_PAL_SETTINGS_PATH` / `2394010` / `"palserver"` literals. That dissolution happens in Plan 03-02.

**WHY the underscore prefix `_PAL_SERVER_DIR_LOCAL` instead of `PAL_SERVER_DIR`**: The existing module global at line 20 is `PAL_SERVER_DIR` (no underscore). Using the same name here would shadow it and confuse the diff. Underscore-prefix clarifies "helper for GAMES construction; will be inlined in a future plan if desired." Alternative (inline the paths directly into the `GAMES` literal) is acceptable but reduces readability.

**WHY post_install_hooks is a list of zero-arg Callables, not list[Callable[[GameSpec], None]]**: `research/ARCHITECTURE.md` line 78 locks the zero-arg signature. The closure (`_palworld_sdk_hook`) captures the specific paths at module import time. ARK in Phase 5 will define its own zero-arg hook or omit hooks entirely.
  </action>
  <verify>
    <automated>cd /root/personal/palworld-server-launcher && .venv/bin/python -c "from logpose.main import GAMES, GameSpec, SettingsAdapter; assert isinstance(GAMES, dict) and list(GAMES.keys()) == ['palworld']; pal = GAMES['palworld']; assert isinstance(pal, GameSpec); assert pal.key == 'palworld' and pal.app_id == 2394010 and pal.service_name == 'palserver' and pal.service_template_name == 'palserver.service.template'; assert pal.binary_rel_path == 'PalServer.sh' and pal.display_name == 'Palworld'; assert pal.settings_section_rename == ('[/Script/Pal.PalWorldSettings]','[/Script/Pal.PalGameWorldSettings]'); assert isinstance(pal.settings_adapter, SettingsAdapter) and callable(pal.settings_adapter.parse) and callable(pal.settings_adapter.save); assert len(pal.post_install_hooks) == 1 and callable(pal.post_install_hooks[0]); assert pal.apt_packages == [] and len(pal.steam_sdk_paths) == 1 and pal.install_options == {'port_default': 8211, 'players_default': 32}; print('OK: GAMES[palworld] GameSpec fully populated, frozen, single entry.')"</automated>
  </verify>
  <done>
- `GAMES` is a module-scope `dict[str, GameSpec]` with exactly one key (`"palworld"`).
- `GAMES["palworld"]` populates all 15 fields exactly matching the `<interfaces>` block.
- `_palworld_sdk_hook` is a zero-arg callable that internally calls `_fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)`.
- Existing `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` module globals are still present.
- Every existing `@app.command()` body is byte-identical to its pre-plan state.
- Attempting `GAMES["palworld"].key = "other"` raises `FrozenInstanceError` (frozen invariant).
  </done>
</task>

<task type="auto">
  <name>Task 3: Byte-diff exit gate + commit</name>
  <files>logpose/main.py</files>
  <action>
Run the full byte-diff regression harness; it MUST stay green because this plan added code additively without touching any call site or template:

```bash
cd /root/personal/palworld-server-launcher
.venv/bin/python -m pytest tests/test_palworld_golden.py -x
```

Expected: `3 passed in 0.05s`, exit code 0.

Also run the script-mode entrypoint for parity with Phase 2's dual verification:

```bash
cd /root/personal/palworld-server-launcher
.venv/bin/python tests/test_palworld_golden.py
```

Expected: `OK: palserver.service matches v0.1.19 golden (template + real render path)` and exit 0.

[BLOCKING] If EITHER command exits non-zero, STOP and diagnose before committing. The most likely failure modes are:
- `NameError: name 'Callable' is not defined` → missing `from typing import Callable` import.
- `NameError: name 'field' is not defined` → missing `from dataclasses import field` import.
- `NameError: name '_palworld_parse' is not defined` → GAMES block placed before `_palworld_parse` definition; move it below line 238 (after `_palworld_save`).
- `ValueError: mutable default list is not allowed` → a mutable-default field uses `= []` instead of `field(default_factory=list)`.
- `FrozenInstanceError` on import → some code accidentally assigns to a GameSpec field after construction. Unlikely but check.

Byte-diff failure (`test_render_service_file_byte_identical_to_golden` fires) is NOT expected in this plan because `install()` and `_render_service_file` are untouched. If it fires, someone modified a call site accidentally — revert.

Once all checks pass, create the commit. Use a single atomic commit, per research recommendation of 3 commits for the phase:

```bash
cd /root/personal/palworld-server-launcher
git add logpose/main.py
git commit -m "$(cat <<'EOF'
refactor(03-01): add GameSpec + SettingsAdapter dataclasses + GAMES registry

Introduces frozen @dataclass definitions for SettingsAdapter (2 callables) and
GameSpec (15 fields per ROADMAP Phase 3 Success Criterion #1), plus a
module-scope GAMES: dict[str, GameSpec] with a single "palworld" entry.
Closes ARCH-01, ARCH-02, ARCH-03.

No call sites change in this commit — existing PAL_* module globals, install(),
update(), edit_settings() all continue to operate unchanged. The new registry
is reachable but unused; Plan 03-02 dissolves the globals and switches call
sites to read from GAMES["palworld"]. Plan 03-03 wires _fix_steam_sdk via
post_install_hooks.

pytest tests/test_palworld_golden.py -x: 3 passed (byte-diff exit gate green).
EOF
)"
```
  </action>
  <verify>
    <automated>cd /root/personal/palworld-server-launcher && .venv/bin/python -m pytest tests/test_palworld_golden.py -x && .venv/bin/python tests/test_palworld_golden.py && git log -1 --pretty=%s | grep -qE '^refactor\(03-01\)' && echo "OK: harness green + commit landed."</automated>
  </verify>
  <done>
- `pytest tests/test_palworld_golden.py -x` exits 0 with 3 tests passing.
- `python tests/test_palworld_golden.py` exits 0.
- A single commit exists on `main` with subject `refactor(03-01): add GameSpec + SettingsAdapter dataclasses + GAMES registry`.
- `git diff HEAD~1 HEAD -- logpose/main.py` shows only additions (two dataclass blocks + `_PAL_*` helpers + `_palworld_sdk_hook` + `GAMES` literal + two new imports). No deletions, no modifications to existing functions or commands.
  </done>
</task>

</tasks>

<verification>
Overall phase-plan checks (all must pass before committing Task 3):

1. Imports: `from typing import Callable, Optional` and `from dataclasses import dataclass, field` both present at top of `logpose/main.py`.
2. `SettingsAdapter` dataclass exists, is frozen, has exactly 2 fields (`parse`, `save`).
3. `GameSpec` dataclass exists, is frozen, has exactly 15 fields with the names listed in the `<interfaces>` block.
4. `GAMES: dict[str, GameSpec]` is defined at module scope with exactly one key (`"palworld"`).
5. `GAMES["palworld"]` fields reproduce Palworld's v0.1.19 values exactly (app_id 2394010, service_name "palserver", section-rename tuple, etc.).
6. All existing `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` module globals are still present and untouched.
7. `pytest tests/test_palworld_golden.py -x` exits 0 (3 tests passing) — byte-diff exit gate.
8. `python -c "import logpose.main"` exits 0.
9. A single commit landed with subject matching `refactor(03-01): …`.
</verification>

<success_criteria>
Plan complete when:
- [ ] `SettingsAdapter` and `GameSpec` frozen dataclasses defined in `logpose/main.py`.
- [ ] `GameSpec` has all 15 named fields from the ROADMAP Phase 3 enumeration.
- [ ] `GAMES: dict[str, GameSpec]` defined at module scope with one entry keyed `"palworld"`.
- [ ] `_palworld_sdk_hook` zero-arg closure defined and registered in `GAMES["palworld"].post_install_hooks`.
- [ ] Every existing module global, function body, and `@app.command()` is byte-identical to its pre-plan state.
- [ ] `pytest tests/test_palworld_golden.py -x` exits 0 with 3 tests passing.
- [ ] One atomic commit with subject `refactor(03-01): add GameSpec + SettingsAdapter dataclasses + GAMES registry` landed on `main`.
</success_criteria>

<output>
After completion, create `.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-01-SUMMARY.md` per the summary.md template. Record:
- Commit SHA.
- Confirm ARCH-01 / ARCH-02 / ARCH-03 closed by existence.
- Byte-diff harness result (expected: 3 passed).
- Handoff note for Plan 03-02: call sites still read old globals; dissolution comes next.
</output>
