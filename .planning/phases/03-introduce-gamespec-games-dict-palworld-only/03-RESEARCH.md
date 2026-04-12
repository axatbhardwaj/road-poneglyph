# Phase 3: Introduce GameSpec + GAMES dict (Palworld only) - Research

**Researched:** 2026-04-13
**Domain:** Python stdlib dataclasses + module-scope registry refactor (minimum-diff; zero-behavior-change for Palworld)
**Confidence:** HIGH

## Summary

Phase 3 is a **pure structural refactor** of `logpose/main.py` that dissolves four Palworld-specific module-level constants (`STEAM_DIR`, `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH`) and five scattered Palworld literals (app_id `2394010`, service name `palserver`, template filenames, sdk64 path, section-rename tuple) into a single frozen `GameSpec` dataclass held inside `GAMES: dict[str, GameSpec]`. Phase 2 already completed the hard half of this work: every helper already accepts parameters instead of reading module globals, `_palworld_parse`/`_palworld_save` are named, and the byte-diff harness (3 tests in `tests/test_palworld_golden.py`) is the regression oracle that fires the moment the refactor breaks Palworld's rendered systemd unit.

The **14-field `GameSpec` schema** is already fully specified in `.planning/research/ARCHITECTURE.md` — Phase 3 just materializes it in code. There is no external library to research, no API surface to discover, no version to pin: this is stdlib `dataclasses` + `typing.Callable` + the existing `Path`/`re`/`rich`/`typer` surface. The only novel tool usage is `dataclasses.dataclass(frozen=True)` + `field(default_factory=list)` — both Python 3.7+ stdlib, well below the project's 3.8 floor.

**Primary recommendation:** Implement in three atomic commits — (1) define dataclasses + `GAMES["palworld"]` registry with all 14 fields populated, (2) dissolve all `PAL_*` module globals and replace every call-site read with `GAMES["palworld"].<field>` access (keeping helper signatures unchanged since Phase 2 already parameterized them), (3) wire `_fix_steam_sdk` as a `post_install_hook` entry rather than a direct call in `install()`. Between each commit, run `pytest tests/test_palworld_golden.py -x` — all 3 tests must stay green. If the third test (`test_render_service_file_byte_identical_to_golden`) breaks, the refactor has drifted the systemd rendering and must be reverted before commit.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting (`workflow.skip_discuss: true` in `.planning/config.json`). Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Claude's Discretion
All implementation choices — shape of `GameSpec`, ordering of fields, specific `install_options` shape for Palworld, exact mechanism for invoking `post_install_hooks`, organization of the `GAMES` dict block within `logpose/main.py`, commit granularity within the phase.

### Deferred Ideas (OUT OF SCOPE)
None — discuss phase skipped. No items explicitly deferred from a discussion.

**Implicit out-of-scope (from ROADMAP + STATE):**
- ARK entry in `GAMES` dict — deferred to Phase 5.
- Typer factory pattern `_build_game_app(spec)` — deferred to Phase 4.
- Merged polkit rule `40-logpose.rules` — deferred to Phase 4.
- Any behavioral change to Palworld install/start/stop/edit flows — invariants per PAL-01, PAL-02, PAL-06, PAL-09 that span Phases 1–5.
- `sys.exit(1)` → `typer.Exit(code=1)` migration — deferred to Phase 4 per Plan 02-04 summary.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **ARCH-01** | `GameSpec` frozen dataclass with 14 fields | Schema already locked in `research/ARCHITECTURE.md` lines 65–78 (12 fields) — Phase 3 adds `apt_packages`, `steam_sdk_paths`, `install_options` for the full 14-field count per ROADMAP Phase 3 Success Criterion #1. |
| **ARCH-02** | `SettingsAdapter` frozen dataclass with `parse` + `save` callables | Schema locked in `research/ARCHITECTURE.md` lines 60–63. `_palworld_parse` / `_palworld_save` already exist from Plan 02-02 (logpose/main.py:200, 214). |
| **ARCH-03** | `GAMES: dict[str, GameSpec]` at module scope in `logpose/main.py`, single entry `"palworld"` | Phase 3 exit criterion #2. Registry defined adjacent to where module globals currently live (`logpose/main.py:19–22`). |
| **ARCH-04** | Every game-aware helper reads from `GAMES["palworld"]`; no `PAL_*` module globals remain | Phase 2 Plan 03 already parameterized the helper bodies (7 signatures verified zero module-global reads). Phase 3 moves the module-global *reads* from the Typer commands into `GAMES["palworld"]` field accesses. |
| **PAL-05** | Palworld section rename `[/Script/Pal.PalWorldSettings]` → `[/Script/Pal.PalGameWorldSettings]` via `GameSpec.settings_section_rename` | Tuple currently passed inline at `logpose/main.py:410–413`. Phase 3 hoists it into `GAMES["palworld"].settings_section_rename`. |
| **PAL-08** | `_fix_steam_sdk` wired as Palworld-only `post_install_hook` | Currently called directly in `install()` at `logpose/main.py:325–328`. Phase 3 moves it into `GAMES["palworld"].post_install_hooks` as a zero-arg callable (closure over `GAMES["palworld"].steam_sdk_paths`). |
| ARCH-05 (invariant) | No `BaseGame` class, no `core/` split — everything in `logpose/main.py` | Research confirms: dataclasses are a struct, not a class hierarchy. User's constraint is satisfied by frozen `GameSpec` + module-level function callables. |
| ARCH-06 (invariant) | `_run_command`, `_install_steamcmd`, `_repair_package_manager` signatures unchanged | Phase 3 touches NONE of these — they remain game-agnostic helpers. |
| PAL-01 / PAL-02 / PAL-06 (continuous invariants) | Service filename `palserver.service`, template byte-identical, launch args unchanged | Enforced by the 3-test byte-diff harness. Phase 3 must leave `logpose/templates/palserver.service.template` (323 bytes, sha `b84d069a…`) untouched. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Root `./CLAUDE.md` is a file-tree navigator, not a behavior rulebook — no directive constraints. However, two subdirectory CLAUDE.md files establish module structure:

| Source | Constraint | Phase 3 Compliance |
|--------|-----------|-------------------|
| `logpose/CLAUDE.md` | `main.py` is the single implementation file ("CLI commands, systemd/polkit setup, steamcmd") | ✓ Phase 3 keeps everything in `main.py` — no new modules, no `games/` split. |
| `logpose/templates/CLAUDE.md` | Only two template files expected (`palserver.service.template`, `palserver.rules.template`) | ✓ Phase 3 adds nothing to `templates/`. ARK templates come in Phase 5; merged polkit rule in Phase 4. |

**Cross-referenced constraints from SUMMARY.md + STATE.md (locked project decisions):**
- No `BaseGame` class hierarchy (ARCH-05).
- Keep `_repair_package_manager` load-bearing and untouched.
- Minimum-diff principle — "2 games don't justify abstraction."
- `from __future__ import annotations` required on every module (already present in `main.py` line 5).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` (stdlib) | Python 3.7+ | Frozen `GameSpec` + `SettingsAdapter` structs | Stdlib; zero runtime cost; typo-safe field access; autocomplete; exactly what `research/ARCHITECTURE.md` calls for. [VERIFIED: present in every supported Python ≥3.8] |
| `typing.Callable` (stdlib) | Python 3.8 compatible via `from __future__ import annotations` | Type hints for `SettingsAdapter.parse` / `.save` and `post_install_hooks` | No runtime cost under `from __future__ import annotations`; matches existing style in `logpose/main.py`. [VERIFIED: logpose/main.py:5 imports `from __future__ import annotations`] |
| `pathlib.Path` (stdlib) | built-in | Field type for `server_dir`, `settings_path`, `default_settings_path` | Already used throughout `logpose/main.py`; frozen-dataclass-safe (Path is immutable). [VERIFIED] |
| `re` (stdlib) | built-in | `_palworld_parse` regex (unchanged from Phase 2) | Already imported (`logpose/main.py:11`). Phase 3 touches no regex. [VERIFIED] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typer` | `>=0.9,<0.21` (pinned in `pyproject.toml`) | Existing CLI framework | Phase 3 does NOT touch Typer — factory pattern is Phase 4. Commands keep their current shape; only their helper calls switch from `PAL_*` globals to `GAMES["palworld"].<field>`. |
| `rich` | `>=13.0,<14` (pinned) | Existing console output | Unchanged. |
| `pytest` | installed in `.venv` | Byte-diff harness runner | Phase 3 runs `pytest tests/test_palworld_golden.py -x` after every commit; must stay green. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Frozen `@dataclass(frozen=True)` | `typing.NamedTuple` | NamedTuple requires positional ordering or `._replace()`; dataclass is idiomatic for named-field structs. `ARCHITECTURE.md` locked dataclass. |
| Frozen dataclass | Plain `dict` | No type safety, no autocomplete, typo-prone (`spec["app_idi"]` silently None). User's constraint rejected `BaseGame` — not dataclasses. |
| `GAMES = {...}` dict | `GAMES: Final[dict[str, GameSpec]]` annotation | `Final` is Python 3.8+ via `typing`; adds nothing behavioral; the dataclass frozenness is what enforces immutability per-entry. Skip — minimum-diff. |
| `post_install_hooks: list[Callable[[], None]]` (zero-arg closures) | `list[Callable[[GameSpec], None]]` (takes spec) | Zero-arg is simpler; caller builds the closure at `GAMES` definition time (closes over `spec.steam_sdk_paths`). `research/ARCHITECTURE.md` line 78 uses zero-arg signature. Stick with zero-arg. |

**No installation needed — all dependencies already pinned in `pyproject.toml` by Phase 1.**

**Version verification:** Not applicable — Phase 3 adds no runtime dependencies. `pyproject.toml` deps (`typer>=0.9,<0.21`, `rich>=13.0,<14`) verified in place per Phase 1 summary.

## Architecture Patterns

### Target Module Structure (logpose/main.py after Phase 3)
```
logpose/main.py  (single file — ARCH-05 invariant)
├── from __future__ import annotations          # existing
├── stdlib imports + third-party                # existing
├── app = typer.Typer()                         # existing
├── console = Console()                         # existing
├── STEAM_DIR = Path.home() / ".steam/steam"    # KEEP — used inside GAMES["palworld"] construction
├── @dataclass(frozen=True) class SettingsAdapter   # NEW
├── @dataclass(frozen=True) class GameSpec          # NEW
├── def _palworld_parse(...)                    # existing — becomes GAMES["palworld"].settings_adapter.parse
├── def _palworld_save(...)                     # existing — becomes GAMES["palworld"].settings_adapter.save
├── def _fix_steam_sdk(...)                     # existing — referenced from GAMES["palworld"].post_install_hooks via lambda
├── def _palworld_sdk_hook()                    # NEW — thin zero-arg closure binding _fix_steam_sdk paths
├── GAMES: dict[str, GameSpec] = { "palworld": GameSpec(...) }   # NEW
├── def _get_os_id() / _get_template / _run_command / _repair_package_manager / _install_steamcmd / ...  # existing unchanged
├── def _run_steamcmd_update / _install_palworld / _render_service_file / _write_service_file / _setup_polkit / _create_settings_from_default / _display_settings / _interactive_edit_loop  # existing signatures unchanged from Phase 2
└── @app.command() install / start / stop / restart / status / enable / disable / update / edit_settings   # bodies adjusted to read from GAMES["palworld"]
```

**Ordering constraint:** `SettingsAdapter` must be defined before `GameSpec` (since `GameSpec` has a `settings_adapter: SettingsAdapter` field). `GameSpec` must be defined before `GAMES` (obviously). `_palworld_parse`, `_palworld_save`, `_fix_steam_sdk` must be defined before `GAMES` (referenced inside). `STEAM_DIR` must remain at module top (referenced inside `GAMES["palworld"]` construction for `server_dir` and `steam_sdk_paths`).

### Pattern 1: Frozen Dataclass with Default-Factory List
**What:** Use `@dataclass(frozen=True)` + `field(default_factory=list)` for mutable-default-safe field initialization.
**When to use:** Any dataclass field whose default is a list (or any mutable container).
**Example:**
```python
# Source: Python stdlib dataclasses docs — https://docs.python.org/3/library/dataclasses.html#mutable-default-values
from dataclasses import dataclass, field
from typing import Callable, Optional
from pathlib import Path

@dataclass(frozen=True)
class SettingsAdapter:
    parse: Callable[[Path], dict[str, str]]
    save: Callable[[Path, dict[str, str]], None]

@dataclass(frozen=True)
class GameSpec:
    key: str
    display_name: str
    app_id: int
    server_dir: Path
    binary_rel_path: str
    settings_path: Path
    default_settings_path: Optional[Path]
    settings_section_rename: Optional[tuple[str, str]]
    service_name: str
    service_template_name: str
    settings_adapter: SettingsAdapter
    post_install_hooks: list[Callable[[], None]] = field(default_factory=list)
    apt_packages: list[str] = field(default_factory=list)
    steam_sdk_paths: list[tuple[Path, Path]] = field(default_factory=list)
    install_options: dict[str, object] = field(default_factory=dict)
```
[CITED: research/ARCHITECTURE.md lines 56–78, with 14-field expansion per ROADMAP Phase 3 Success Criterion #1]
[VERIFIED: `field(default_factory=list)` pattern — this is the Python-canonical way; naked `= []` raises `ValueError: mutable default list` under `frozen=True`.]

**Note on `install_options`:** Phase 3 is Palworld-only; populate with `{"port_default": 8211, "players_default": 32}` or leave empty — the CLI `install` command still has these as `typer.Option` defaults at the decorator level. The field exists per the ROADMAP spec but its runtime consumer is Phase 4 (factory pattern reads per-game install flags).

### Pattern 2: Zero-Arg Hook Closure over Spec Fields
**What:** Build `post_install_hooks` list with zero-arg lambdas that close over the `spec` being constructed.
**When to use:** When a hook needs per-spec data but the calling convention is "invoke all hooks with zero args."
**Example:**
```python
# Canonical pattern — close over paths at GAMES construction time
_PAL_STEAM_CLIENT_SO = STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"
_PAL_SDK64_DST = Path.home() / ".steam/sdk64"

def _palworld_sdk_hook() -> None:
    """Palworld post-install hook: copy steamclient.so to sdk64."""
    _fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)

# ... later in GAMES construction:
"palworld": GameSpec(
    ...,
    post_install_hooks=[_palworld_sdk_hook],
    steam_sdk_paths=[(_PAL_STEAM_CLIENT_SO, _PAL_SDK64_DST)],  # data twin — Phase 5 ARK iterates over this for sdk32+sdk64
    ...,
)
```
**Rationale:** Keeps `_fix_steam_sdk` signature unchanged (Phase 2 parameterized it with two Path args). The hook is a thin wrapper that binds Palworld's specific sdk paths. [CITED: research/ARCHITECTURE.md line 78; Phase 2 Plan 03 Summary — `_fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path)` signature].

**Alternative considered:** Make `_fix_steam_sdk` iterate over `spec.steam_sdk_paths` and put `_fix_steam_sdk` itself in `post_install_hooks`. Rejected because `_fix_steam_sdk`'s signature takes two args, not a list — changing it would violate minimum-diff and risk the byte-diff harness. The closure pattern is the one-line cost that preserves Phase 2's invariants.

### Pattern 3: Install Command Reads Single `spec` Variable
**What:** Top of `install()` binds `spec = GAMES["palworld"]` once; every subsequent call uses `spec.<field>` instead of module globals.
**Example:**
```python
@app.command()
def install(port: int = typer.Option(8211, help="..."),
            players: int = typer.Option(32, help="..."),
            start: bool = typer.Option(False, "--start")) -> None:
    if Path.home() == Path("/root"):
        rich.print("This script should not be run as root. Exiting.", file=sys.stderr)
        sys.exit(1)

    spec = GAMES["palworld"]

    _install_steamcmd()
    _run_steamcmd_update(spec.server_dir, spec.app_id)
    for hook in spec.post_install_hooks:
        hook()
    service_content = _render_service_file(
        service_name=spec.service_name,
        template_name=spec.service_template_name,
        user=Path.home().name,
        working_directory=spec.server_dir,
        exec_start_path=spec.server_dir / spec.binary_rel_path,
        port=port,
        players=players,
    )
    _write_service_file(Path(f"/etc/systemd/system/{spec.service_name}.service"), service_content)
    _setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)  # template strings stay literal — Phase 4 merges
    ...
```
**Warning:** `_install_palworld` (the thin wrapper at `logpose/main.py:140–143`) can be **deleted** in Phase 3 — its single caller (`install()`) now calls `_run_steamcmd_update(spec.server_dir, spec.app_id)` directly. This mirrors the inline-it-after-parameterization pattern Plan 02-04 set up. Alternatively, keep it as `_install_palworld(spec)` → `_run_steamcmd_update(spec.server_dir, spec.app_id)` for semantic clarity. **Recommendation:** delete the wrapper — one fewer name to grep for Palworld-ness.

### Anti-Patterns to Avoid

- **Don't mutate `GAMES` at runtime.** The dict is module-scope and frozen at definition time. Any code that assigns `GAMES["palworld"] = …` or `GAMES["palworld"].some_field = …` is a bug; `frozen=True` on `GameSpec` will raise `FrozenInstanceError` on the latter.

- **Don't put the section-rename tuple literal at `edit_settings` call site.** Currently `logpose/main.py:410–413` passes `("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]")` inline. Phase 3 hoists this into `GAMES["palworld"].settings_section_rename`; the call site becomes `spec.settings_section_rename`.

- **Don't pre-compute `Path.home()` at module import time.** The tests run under different `$HOME` values (pytest may or may not preserve user home); `STEAM_DIR = Path.home() / ".steam/steam"` is already evaluated at import per the current code, which is fine for the install-time / edit-time flow. **Do NOT** put `Path.home().name` inside `GameSpec` — user identity is per-invocation, not per-game. The `user=Path.home().name` argument to `_render_service_file` and `_setup_polkit` stays at the command level.

- **Don't add module globals to bypass the registry.** The whole point of Phase 3 is "no `PAL_*` module-level constants remain" (Phase 3 Success Criterion #2). Any helper or command that reads `PAL_SERVER_DIR` after Phase 3 is a refactor regression. `STEAM_DIR` is the ONE exception that stays — it's not Palworld-specific (both games use `~/.steam/steam`).

- **Don't change `_palworld_parse` or `_palworld_save` bodies.** They're invariant per PAL-03/PAL-04 (Phase 2 locked). Phase 3 only wraps them in `SettingsAdapter(parse=_palworld_parse, save=_palworld_save)` and changes call sites from direct name to `spec.settings_adapter.parse(spec.settings_path)`.

- **Don't delete `_install_palworld` silently without checking callers.** Per Phase 2 Plan 04 Summary, `_install_palworld` is called twice: once from `install()` and once from inside `update()`. Audit both before removing. Actually, per `logpose/main.py:397`, `update()` calls `_run_steamcmd_update` directly — so `_install_palworld` has only ONE caller (`install()` via `logpose/main.py:324`). Safe to delete.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frozen per-game config struct | Custom `class GameSpec: def __init__(self, ...):` with manual `__hash__`/`__eq__` | `@dataclass(frozen=True)` | stdlib handles `__init__`, `__repr__`, `__eq__`, `__hash__`, immutability — for free. |
| Mutable-default safety | `def __init__(self, hooks=None): self.hooks = hooks or []` | `field(default_factory=list)` | One-liner; explicit; standard. |
| Callable-type annotations | Runtime `callable()` checks inside helper bodies | `Callable[[Path], dict[str, str]]` from `typing` | Under `from __future__ import annotations`, types are strings at runtime — no overhead, full IDE support. |
| Registry lookup | Global module state `_active_game = "palworld"; spec = _lookup()` | Pass `spec: GameSpec` as arg OR `GAMES[key]` at call site | Thread-safety, testability, "no hidden state" per minimum-diff ethos. |
| "Is this field required?" validation | Custom `__post_init__` checks | Type system + `Optional[...]` annotations on truly-optional fields | `default_settings_path: Optional[Path]` says it's allowed to be None; `app_id: int` says it's required. No runtime bloat needed for a 2-game project. |

**Key insight:** Phase 3 is stdlib-only. Any proposal to "use `attrs` for better dataclass ergonomics" or "use `pydantic` for validation" is out of scope — they're new runtime dependencies violating the minimum-diff principle and the `typer + rich` dependency budget locked in Phase 1.

## Runtime State Inventory

> This is a refactor phase — module-global dissolution into a registry. Check for runtime state that embeds the old module-global names.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | None — logpose has no database, no persistent app state. PalWorldSettings.ini on disk uses `[/Script/Pal.PalGameWorldSettings]` section header; this is preserved exactly by the section-rename tuple moving into `GameSpec.settings_section_rename`. | None — section-rename semantics are byte-identical pre/post Phase 3. |
| **Live service config** | `/etc/systemd/system/palserver.service` — rendered once at install time, contains fully-resolved paths from the fixture (user, working_directory, exec_start_path, port, players). Filename unchanged. | None — service file rendering is byte-equivalent per PAL-02 invariant + byte-diff harness. |
| **OS-registered state** | `/etc/polkit-1/rules.d/40-palserver.rules` from v0.1.19 installs. Filename still `40-palserver.rules` in Phase 3 (merged rename is Phase 4). systemd unit `palserver.service` registered via `systemctl enable`. | None — Phase 3 keeps `40-palserver.rules` as the polkit rule filename; the merge to `40-logpose.rules` is Phase 4 per ROADMAP. |
| **Secrets/env vars** | None — logpose reads no env vars other than `HOME` (via `Path.home()`). No secrets stored. | None. |
| **Build artifacts / installed packages** | `palworld_server_launcher.egg-info/` removed from git per Phase 1 (PKG-06). `logpose.egg-info/` may exist locally as build byproduct (gitignored). | None — Phase 3 does not touch `pyproject.toml` or wheel metadata. If the maintainer re-installs in editable mode, a fresh `logpose.egg-info/` appears locally and is gitignored. |

**The canonical question:** *After every file in the repo is updated, what runtime systems still have the old `PAL_*` string cached, stored, or registered?*
- **Answer:** Nothing meaningful. The only string tokens `palserver` / `palworld` that survive Phase 3 are the legitimate systemd unit name (`palserver.service` — PAL-01 invariant), the settings-section headers (on-disk INI state — controlled behavior), and the Palworld display name / key inside `GAMES["palworld"]`. All `PAL_*` module-level **Python constants** are dissolved.

## Common Pitfalls

### Pitfall 1: `TypeError: mutable default <class 'list'> is not allowed` on `GameSpec` definition
**What goes wrong:** Python raises at class definition time if `@dataclass(frozen=True)` sees a raw `[]` or `{}` default.
**Why it happens:** The dataclass machinery refuses mutable defaults to prevent shared-state bugs across instances.
**How to avoid:** Use `field(default_factory=list)` / `field(default_factory=dict)` for every default-empty-collection field (`post_install_hooks`, `apt_packages`, `steam_sdk_paths`, `install_options`).
**Warning signs:** Import error before any test runs. Pytest would fail at collection time with a clear stack trace pointing to the dataclass definition line.

### Pitfall 2: Forward-reference ordering bug — `GameSpec` references `SettingsAdapter` before definition
**What goes wrong:** `NameError: name 'SettingsAdapter' is not defined` at `class GameSpec:` body evaluation.
**Why it happens:** Even with `from __future__ import annotations`, runtime usage of a type (not just annotation) requires the name to exist. The `settings_adapter: SettingsAdapter` field is annotation-only — fine. But if code later does `isinstance(x, SettingsAdapter)`, the class must already be imported/defined.
**How to avoid:** Define `SettingsAdapter` BEFORE `GameSpec` in the source file. `from __future__ import annotations` (already present at `logpose/main.py:5`) defers annotation evaluation to string form — so annotations are safe, but ordering still matters for runtime class references.
**Warning signs:** `NameError` at import. Quick to catch: `python -c "import logpose.main"` exits non-zero.

### Pitfall 3: `frozen=True` + `post_install_hooks` mutation
**What goes wrong:** Someone later writes `GAMES["palworld"].post_install_hooks.append(_another_hook)` — which SUCCEEDS silently (the list is mutable even though the dataclass is frozen; frozen only prevents rebinding the attribute, not mutating its contents).
**Why it happens:** Frozen dataclasses freeze the *reference*, not the pointed-to object.
**How to avoid:** Convention: `GAMES` is constructed once at module scope and never mutated. Code review must flag any `.append` / `.extend` on `GameSpec` list fields. Defensive alternative (Phase 4/5 if needed): use `tuple` instead of `list` for truly-immutable lists — but `list[Callable]` is what `research/ARCHITECTURE.md` locked. Stick with `list` + convention.
**Warning signs:** `post_install_hooks` has different length between two imports. Put a count-check in the byte-diff harness if paranoid — but this is a low-probability bug with 2 games and one developer.

### Pitfall 4: Accidentally breaking byte-diff harness via `service_name` threading
**What goes wrong:** `_render_service_file` currently takes `service_name="palserver"` as a kwarg (unused in the body — Phase 2 Plan 03 decision, held for Phase 3 symmetry). If Phase 3 reads `spec.service_name` and passes it, but the value is subtly different (e.g., `"palserver.service"` with the suffix vs `"palserver"` without), the byte-diff harness STILL passes (because the parameter is unused in the body) — but the service file PATH (`/etc/systemd/system/{spec.service_name}.service`) is wrong and install silently writes to the wrong file.
**Why it happens:** The decision to accept `service_name` for "Phase 3 symmetry" in Plan 02-03 means the template does NOT validate it. Testing at the template level catches nothing.
**How to avoid:** Convention — `spec.service_name = "palserver"` (no suffix). Every call site that needs the full filename constructs `f"{spec.service_name}.service"`. Audit all 9 existing systemctl invocations (`logpose/main.py:345, 360, 366, 372, 378, 384, 390, 397`) and replace hardcoded `"palserver"` with `spec.service_name`. Run `grep -nE 'palserver' logpose/main.py` after the refactor — hits should be zero outside `GAMES["palworld"]` construction.
**Warning signs:** `systemctl start palserver` works but systemd reports "unit not found" for a randomly-different service name. The byte-diff harness will NOT catch this. Manual `logpose palworld install --help` + dry run is the safety net.

### Pitfall 5: `edit_settings` call site regression on section-rename
**What goes wrong:** Moving the section-rename tuple from the inline `_create_settings_from_default` call to `GAMES["palworld"].settings_section_rename` — but forgetting to pass `spec.settings_section_rename` at the call site, leaving a stale `None` that disables Palworld's section rename. Silent: the rename only happens when the settings file is being CREATED from default — most users never hit this path on a fresh install because PalServer creates the file on first launch.
**Why it happens:** The rename codepath is rarely exercised (Plan 02-03 note: "Moved section-rename literals OUT of `_create_settings_from_default` body into caller"). Visual review of the happy path shows no obvious break.
**How to avoid:** Grep after refactor: `grep -nE 'PalGameWorldSettings' logpose/main.py` — must hit exactly ONE location (`GAMES["palworld"].settings_section_rename` tuple). If it hits zero, the rename was dropped. If it hits two or more, there's a stale literal somewhere. Also manually trace: `edit_settings` → `_create_settings_from_default(spec.default_settings_path, spec.settings_path, spec.settings_section_rename)`.
**Warning signs:** Running `logpose edit-settings` on a fresh Palworld install where no INI exists yet — the default template has `[/Script/Pal.PalWorldSettings]` but PalServer would write `[/Script/Pal.PalGameWorldSettings]` — the regex parser won't find `OptionSettings` in the wrong section and raises `ValueError`.

### Pitfall 6: Bypassing the byte-diff harness during Phase 3 commits
**What goes wrong:** Committing "structural-only" changes without running the harness, discovering at the end-of-phase verification that commit 2 of 3 broke `test_render_service_file_byte_identical_to_golden`, and having to bisect.
**Why it happens:** Phase 3 feels like pure syntax shuffling; the temptation to skip tests is real.
**How to avoid:** After every single commit that touches `logpose/main.py`, run `pytest tests/test_palworld_golden.py -x`. All 3 tests must pass. This takes ~50ms; the insurance is worth it.
**Warning signs:** Test #3 (`test_render_service_file_byte_identical_to_golden`) fails. Plan 02-05 Summary labeled this the "Phase 3 regression oracle" — if it fires, STOP and diagnose before continuing.

## Code Examples

### Example 1: Complete `GameSpec` / `SettingsAdapter` definition

```python
# Source: ARCHITECTURE.md lines 56–78 (schema locked); ROADMAP Phase 3 Success Criterion #1 (14 fields)
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class SettingsAdapter:
    """Per-game settings file I/O. Two callables, no state."""
    parse: Callable[[Path], dict[str, str]]
    save: Callable[[Path, dict[str, str]], None]


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
    service_name: str                       # no ".service" suffix
    service_template_name: str
    settings_adapter: SettingsAdapter
    post_install_hooks: list[Callable[[], None]] = field(default_factory=list)
    apt_packages: list[str] = field(default_factory=list)
    steam_sdk_paths: list[tuple[Path, Path]] = field(default_factory=list)
    install_options: dict[str, object] = field(default_factory=dict)
```

### Example 2: Complete `GAMES["palworld"]` entry

```python
# Source: Dissolving all PAL_* globals from logpose/main.py:19-22 into a single registry entry.
# All paths + literals reproduce v0.1.19 behavior byte-for-byte (PAL-01/02/06 invariants).

STEAM_DIR = Path.home() / ".steam/steam"  # Kept — game-agnostic.

_PAL_SERVER_DIR = STEAM_DIR / "steamapps/common/PalServer"
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
        server_dir=_PAL_SERVER_DIR,
        binary_rel_path="PalServer.sh",
        settings_path=_PAL_SERVER_DIR / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini",
        default_settings_path=_PAL_SERVER_DIR / "DefaultPalWorldSettings.ini",
        settings_section_rename=(
            "[/Script/Pal.PalWorldSettings]",
            "[/Script/Pal.PalGameWorldSettings]",
        ),
        service_name="palserver",
        service_template_name="palserver.service.template",
        settings_adapter=SettingsAdapter(parse=_palworld_parse, save=_palworld_save),
        post_install_hooks=[_palworld_sdk_hook],
        apt_packages=[],                                    # Palworld uses only the apt deps that _install_steamcmd already installs
        steam_sdk_paths=[(_PAL_STEAM_CLIENT_SO, _PAL_SDK64_DST)],
        install_options={"port_default": 8211, "players_default": 32},
    ),
}
```

**Note on the module-private prefix `_PAL_*`:** These are *internal to the `GAMES` construction block* — NOT module-level Palworld globals in the ARCH-04 sense. They're helper locals in the same way `_palworld_sdk_hook` is a helper function. Phase 3 Success Criterion #3 says "no `PAL_*` module-level **constants** remain"; function-local and closure-captured bindings are fine. If the reviewer is strict, inline them into the `GAMES` literal (tradeoff: readability vs purity). **Recommendation:** Keep `_PAL_*` prefixed with underscore and use them only inside `_palworld_sdk_hook` + the `GAMES` construction; this is idiomatic and grep-friendly.

### Example 3: Refactored `install()` command body

```python
@app.command()
def install(
    port: int = typer.Option(8211, help="Port to run the server on."),
    players: int = typer.Option(32, help="Maximum number of players."),
    start: bool = typer.Option(False, "--start", help="Start the server immediately after installation."),
) -> None:
    """Install the Palworld dedicated server and create a systemd service."""
    if Path.home() == Path("/root"):
        rich.print("This script should not be run as root. Exiting.", file=sys.stderr)
        sys.exit(1)

    spec = GAMES["palworld"]

    _install_steamcmd()
    _run_steamcmd_update(spec.server_dir, spec.app_id)
    for hook in spec.post_install_hooks:
        hook()
    service_content = _render_service_file(
        service_name=spec.service_name,
        template_name=spec.service_template_name,
        user=Path.home().name,
        working_directory=spec.server_dir,
        exec_start_path=spec.server_dir / spec.binary_rel_path,
        port=port,
        players=players,
    )
    _write_service_file(Path(f"/etc/systemd/system/{spec.service_name}.service"), service_content)
    _setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)

    console.print("Installation complete!")

    if start:
        console.print("Starting the server...")
        _run_command(f"systemctl start {spec.service_name}")
        console.print("Server started successfully!")
    else:
        console.print(
            "You can now start the server with: palworld-server-launcher start"
        )

    console.print(
        "To enable the server to start on boot, run: palworld-server-launcher enable"
    )
```

**Byte-diff preservation check:** Every argument to `_render_service_file` must produce identical bytes to Phase 2's call site.
- `service_name="palserver"` — matches (Plan 02-04 summary).
- `template_name="palserver.service.template"` — matches.
- `user=Path.home().name` — matches.
- `working_directory=_PAL_SERVER_DIR` (was `PAL_SERVER_DIR`) — same Path value.
- `exec_start_path=_PAL_SERVER_DIR / "PalServer.sh"` (was `PAL_SERVER_DIR / "PalServer.sh"`) — same Path value.
- `port`, `players` — unchanged.

Post-Phase-3 golden render stays byte-identical. Test #3 in the harness stays green.

### Example 4: Refactored `edit_settings` and `update`

```python
@app.command()
def update() -> None:
    """Update the Palworld dedicated server."""
    spec = GAMES["palworld"]
    console.print("Updating Palworld dedicated server...")
    _run_steamcmd_update(spec.server_dir, spec.app_id)
    console.print("Update complete! Restart the server for the changes to take effect.")


@app.command(name="edit-settings")
def edit_settings() -> None:
    """Edit the PalWorldSettings.ini file."""
    spec = GAMES["palworld"]
    try:
        settings = spec.settings_adapter.parse(spec.settings_path)
    except (FileNotFoundError, ValueError):
        _create_settings_from_default(
            spec.default_settings_path,
            spec.settings_path,
            spec.settings_section_rename,
        )
        try:
            settings = spec.settings_adapter.parse(spec.settings_path)
        except (ValueError, FileNotFoundError) as e:
            rich.print(
                f"An error occurred after creating default settings: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        _interactive_edit_loop(settings)
        spec.settings_adapter.save(spec.settings_path, settings)
    except Exception as e:
        rich.print(f"An error occurred during settings edit: {e}", file=sys.stderr)
        sys.exit(1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Module-level `PAL_*` constants | Frozen `GameSpec` inside `GAMES` dict | This phase | Required for ARCH-04 to close, PAL-05 / PAL-08 to land, and Phase 4's Typer factory to have anything to iterate over. |
| `_install_palworld` thin wrapper | Direct `_run_steamcmd_update(spec.server_dir, spec.app_id)` | This phase (recommended) | One fewer Palworld-named function in the module. |
| Section-rename tuple passed inline | Read from `spec.settings_section_rename` | This phase (PAL-05) | Aligns with ARCH-04 "no hardcoded palworld values in helper bodies or call sites." |
| `_fix_steam_sdk` called directly in `install()` | Called via `post_install_hooks` iteration | This phase (PAL-08) | Palworld-only behavior is declarative; ARK's `GAMES["ark"].post_install_hooks` will simply omit it (SUMMARY.md correction #3 + Pitfalls #2–#4 all agree). |

**Deprecated/outdated (in the context of this codebase):**
- Module-global `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` — removed this phase.
- `_install_palworld` function name — removed this phase (wrapper inlined).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 3 uses `list[Callable[[], None]]` for `post_install_hooks` (zero-arg closures) rather than `Callable[[GameSpec], None]` | Pattern 2 | Low — `research/ARCHITECTURE.md` line 78 explicitly locks zero-arg. If planner or later phase needs spec-taking hooks, refactor to `Callable[[GameSpec], None]` is mechanical. |
| A2 | `install_options: dict[str, object]` is the right field shape for Palworld's `{"port_default": 8211, "players_default": 32}` | Example 2 | Low — ROADMAP Phase 3 names the field but doesn't specify internal shape. Phase 4 is the consumer (factory reads per-game install flags). If Phase 4 needs a different shape, Phase 3 field contents are easy to change; the field itself is what Phase 3 locks. |
| A3 | `_install_palworld` thin wrapper should be deleted (inlined into `install()`) | Example 3 | Minimal — if reviewer prefers keeping it for semantic grouping, leave it; call sites just become `_install_palworld(spec)`. Cosmetic choice. |
| A4 | `service_name` field holds the bare name ("palserver") without ".service" suffix, and call sites that need the filename use `f"{spec.service_name}.service"` | Pitfall 4 | Medium — reverse convention (`service_name="palserver.service"`) also valid but requires stripping for `systemctl <verb> palserver` calls. Either works; consistency within the phase is what matters. Pick one, document in `GameSpec` docstring. |
| A5 | `STEAM_DIR` module global is kept (not moved into `GAMES`), since it's game-agnostic | Example 2 | Low — both games use the same `~/.steam/steam` directory. Keeping `STEAM_DIR` at module scope is cleaner than duplicating it across every `GameSpec`. Phase 5 ARK entry will also reference `STEAM_DIR`. |
| A6 | `_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)` call site keeps its literal strings in Phase 3 | Example 3 | Low — merged polkit rule (`40-logpose.rules`) is Phase 4 per ROADMAP. Phase 3 leaves polkit entirely alone. |
| A7 | `apt_packages=[]` is correct for Palworld (no extra apt deps beyond what `_install_steamcmd` already pulls) | Example 2 | Low — `research/PITFALLS.md:22` explicitly locks this: "Palworld's entry has an empty list." ARK will have the apt extras. |
| A8 | `steam_sdk_paths` field stores `list[tuple[Path, Path]]` of `(src, dst)` pairs — semantically the same data as what `post_install_hooks` operates on, but kept as data for Phase 5 ARK symmetry | Example 2 | Low — Phase 5's ARK entry will use multiple `(src, dst)` pairs (sdk32 + sdk64 + Engine ThirdParty per PITFALLS.md #2). Phase 3 lists Palworld's single pair for schema-completeness; no code currently consumes the field. |

**If this table feels heavy:** it's because Phase 3 is mostly a translation of locked decisions (`research/ARCHITECTURE.md`, ROADMAP) into Python source. Every assumption above is low-risk because the upstream research locked the shape; the risk is in transcription, not in unknown design.

## Open Questions

1. **Should `install_options` be populated for Palworld in Phase 3, or left as `{}`?**
   - What we know: ROADMAP Phase 3 Success Criterion #1 names the field. Phase 4 is the consumer (factory reads per-game install flags to build `typer.Option` defaults).
   - What's unclear: Whether Phase 4's factory reads `install_options` or keeps Typer decorators as source-of-truth for defaults.
   - Recommendation: Populate `{"port_default": 8211, "players_default": 32}` for documentation value; Phase 4 can ignore it if the factory uses decorator defaults directly. Zero behavioral cost either way.

2. **Keep or remove `_install_palworld`?**
   - What we know: Called exactly once (from `install()` per `logpose/main.py:324`). Phase 2 Plan 04 intentionally left it as a thin wrapper.
   - What's unclear: Whether keeping it as `_install_palworld(spec)` aids reading vs inlining to `_run_steamcmd_update(spec.server_dir, spec.app_id)`.
   - Recommendation: Delete it. One fewer Palworld-named symbol. Planner can choose the other way if preferred — Phase 3 byte-diff harness doesn't care either way.

3. **Should Phase 3 delete `STEAM_DIR` module global and inline `Path.home() / ".steam/steam"` into `GAMES["palworld"]` field construction?**
   - What we know: `STEAM_DIR` is referenced in two places — `GAMES["palworld"].server_dir` construction and `_palworld_sdk_hook` steamclient.so path.
   - What's unclear: Phase 3 Success Criterion #2 says "no `PAL_*` module-level constants remain" — `STEAM_DIR` is not `PAL_*`, but it IS a module-level constant serving Palworld.
   - Recommendation: Keep `STEAM_DIR`. It's game-agnostic (Phase 5 ARK also uses `~/.steam/steam`). Phase 3 criterion targets `PAL_*`-prefixed names specifically, and the research documents it as shared infrastructure.

## Environment Availability

> Phase 3 is a pure code refactor — no new external dependencies introduced, no new tools invoked, no network calls, no filesystem operations at import time beyond what Phase 2 already does.

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.8+ | All logpose code | ✓ | `.venv` has 3.12.10 per Plan 02-02 summary | — |
| `dataclasses` (stdlib) | `GameSpec`, `SettingsAdapter` | ✓ | stdlib | — |
| `typing.Callable` | SettingsAdapter callable type hints | ✓ | stdlib | — |
| `typer>=0.9,<0.21` | @app.command decorators | ✓ | pinned in `pyproject.toml` per Phase 1 | — |
| `rich>=13.0,<14` | Console output | ✓ | pinned in `pyproject.toml` per Phase 1 | — |
| `pytest` | Byte-diff harness runner | ✓ | installed in `.venv` per Plan 02-02 note | `python tests/test_palworld_golden.py` (script-mode entrypoint per Plan 02-05) |
| git with tag `v0.1.19` accessible | Paranoia test `test_golden_matches_v0_1_19_tag` | ✓ (verified in Plan 02-01) | repo-local | `pytest.skip` degrades to no-op |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

> `workflow.nyquist_validation` is **false** in `.planning/config.json`. Per instructions, this section is SKIPPED.

## Security Domain

> No `security_enforcement` key in `.planning/config.json` (absent). Phase 3 is a pure Python refactor with zero network surface, zero new input validation, zero auth paths, zero crypto. The existing sudo-via-polkit architecture is Phase 4's concern. Phase 3 introduces no new attack surface.

**Quick ASVS check:**
- V5 Input Validation: **N/A** — no new user input paths introduced this phase.
- V6 Cryptography: **N/A** — no crypto code.
- V4 Access Control: **N/A** — polkit rule file path `40-palserver.rules` unchanged, permissions unchanged.

## Sources

### Primary (HIGH confidence)
- **`.planning/research/ARCHITECTURE.md`** (lines 55–91) — Canonical `GameSpec` / `SettingsAdapter` schema, locked per Phase 0 research.
- **`.planning/research/SUMMARY.md`** (lines 15–19) — Architecture decisions locked: frozen dataclass + GAMES registry + SettingsAdapter + Typer factory (Phase 4) + flat templates.
- **`.planning/research/PITFALLS.md`** (lines 156–180) — Pitfall 6 "GAMES dict values leak between Palworld and ARK code paths" + mitigations (module-global dissolution is named as the fix).
- **`.planning/REQUIREMENTS.md`** — ARCH-01..04, PAL-05, PAL-08 specifications.
- **`.planning/ROADMAP.md`** lines 48–58 — Phase 3 goal + 14-field success criterion.
- **`.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-03-SUMMARY.md`** — Phase 2 handoff: 7 helper signatures verified zero module-global reads; Phase 3 is the "dissolve module globals" step.
- **`.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-04-SUMMARY.md`** — Phase 2 call-site wiring: Typer commands currently read `PAL_SERVER_DIR`, `2394010`, section-rename tuple directly. These are the exact reads Phase 3 moves into `GAMES["palworld"]`.
- **`.planning/phases/02-parameterize-helpers-no-games-dict-yet/02-05-SUMMARY.md`** — "Note for Phase 3 Planner" — `test_render_service_file_byte_identical_to_golden` is THE regression oracle; must stay green.
- **`logpose/main.py`** (current) — Source truth for what Phase 3 edits.
- **`tests/test_palworld_golden.py`** — 3 tests, must all stay green after every Phase 3 commit.

### Secondary (MEDIUM confidence)
- **Python stdlib `dataclasses` docs** — `frozen=True` + `field(default_factory=...)` semantics. [CITED: https://docs.python.org/3/library/dataclasses.html]

### Tertiary (LOW confidence)
- None — this phase has no LOW-confidence findings. All decisions trace to locked research or to direct source inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — stdlib only, no new dependencies, existing imports cover everything.
- Architecture: **HIGH** — schema locked in research/ARCHITECTURE.md; Phase 3 is transcription.
- Pitfalls: **HIGH** — enumerated from Phase 2 summaries + `research/PITFALLS.md:156–180` + direct code inspection.
- Byte-diff safety: **HIGH** — 3-test harness from Phase 2 is the exit gate, already proven to fire on mutation (Plan 02-01 Summary: negative-path mutation verified).

**Research date:** 2026-04-13
**Valid until:** 30 days (stable stdlib surface; no fast-moving external dependencies in scope).

## RESEARCH COMPLETE

**Phase:** 3 - Introduce GameSpec + GAMES dict (Palworld only)
**Confidence:** HIGH

### Key Findings
- **Zero new runtime dependencies.** Phase 3 is stdlib-only (`dataclasses`, `typing.Callable`, `pathlib.Path`). No pip install, no version bumps.
- **Schema is locked — transcription task.** 14-field `GameSpec` + 2-callable `SettingsAdapter` verbatim from `research/ARCHITECTURE.md`. Phase 3 adds `apt_packages`, `steam_sdk_paths`, `install_options` to the 12-field ARCHITECTURE baseline to hit ROADMAP's 14-field criterion.
- **Phase 2 did the hard work.** All 7 helpers already accept parameters; `_palworld_parse`/`_palworld_save` are named; byte-diff harness green with 3 tests. Phase 3 dissolves 4 module globals + 1 inline tuple + moves `_fix_steam_sdk` into a hook list.
- **Byte-diff harness is the exit gate.** `pytest tests/test_palworld_golden.py -x` must stay green after every commit. Test #3 (`test_render_service_file_byte_identical_to_golden`) is the Phase 3 regression oracle — fires immediately if the refactor drifts the systemd render path.
- **`STEAM_DIR` stays at module scope.** It's game-agnostic; Phase 5 ARK will share it. Only `PAL_*`-prefixed constants dissolve into `GAMES["palworld"]`.
- **Three atomic commits recommended:** (1) add `SettingsAdapter` + `GameSpec` + `GAMES["palworld"]` alongside existing globals, keep both reachable; (2) switch every call site and remove the `PAL_*` globals + `_install_palworld` wrapper; (3) wire `_fix_steam_sdk` into `post_install_hooks` with `_palworld_sdk_hook` closure, remove direct call from `install()`.

### File Created
`.planning/phases/03-introduce-gamespec-games-dict-palworld-only/03-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Stdlib only; every import already present in `logpose/main.py`. |
| Architecture | HIGH | Schema locked in `research/ARCHITECTURE.md`; 14-field expansion traces to ROADMAP line 53. |
| Pitfalls | HIGH | Six pitfalls enumerated from Phase 2 summaries + direct code inspection + `research/PITFALLS.md:156–180`. |
| Byte-Diff Safety | HIGH | 3-test harness (Plan 02-01, 02-05) proven to fire on mutation; Phase 3 regression oracle already in place. |

### Open Questions
Three planner-level decisions (all low-risk):
1. Populate `install_options` in Phase 3 or leave `{}` for Phase 4 to fill? (Recommendation: populate for documentation.)
2. Delete `_install_palworld` wrapper or keep as `_install_palworld(spec)`? (Recommendation: delete.)
3. `service_name` field holds `"palserver"` or `"palserver.service"`? (Recommendation: bare name; call sites append suffix where needed.)

### Ready for Planning
Research complete. Planner can now create PLAN.md files. Recommended commit granularity: 3 atomic commits, byte-diff harness green after each.
