# Phase 2: Parameterize Helpers (no GAMES dict yet) — Research

**Researched:** 2026-04-12
**Domain:** Python refactor discipline + byte-diff regression harness
**Confidence:** HIGH (grounded entirely in local codebase + v0.1.19 git tag — no external dependencies)

## Summary

Phase 2 is a two-part mechanical refactor with one load-bearing novelty: the byte-diff regression harness that will anchor every subsequent phase. The refactor itself is low-risk — extract two module globals (`PAL_SETTINGS_PATH`, `PAL_SERVER_DIR`) out of helper bodies into explicit parameters, wrap the existing `_parse_settings` / `_save_settings` as `_palworld_parse(path)` / `_palworld_save(path, values)` with byte-identical bodies, and thread `port`/`players`/`user`/`exec_start_path`/`working_directory` through `_create_service_file` as they already are. The v0.1.19 `palserver.service.template` and `palserver.rules.template` are verified byte-identical to the current tree (diff exit 0 for both) — the golden oracle already exists on disk. The byte-diff harness is a ~60-line pytest module that renders the service template against the locked fixture (`user=foo, port=8211, players=32`) and asserts equality with a golden bytes blob captured once from the live template.

**Primary recommendation:** Extract `_palworld_parse(path)` and `_palworld_save(path, values)` as thin wrappers with verbatim bodies; add explicit parameters (no dataclass bag yet) threaded into `_create_service_file`, `_fix_steam_sdk`, `_install_palworld`, `_run_steamcmd_update`, `edit_settings`, `_create_settings_from_default`; write byte-diff tests under `tests/test_palworld_golden.py` using pytest (available globally; no config/fixtures required), committed alongside a captured golden blob `tests/golden/palserver.service.v0_1_19`. The harness must be invokable as `pytest tests/test_palworld_golden.py -x` AND as a standalone `python tests/test_palworld_golden.py` (phase success criterion #3 says "script exits 0" — implement the module with a `__main__` guard so both entry points work).

## User Constraints (from CONTEXT.md)

### Locked Decisions
None. CONTEXT.md was auto-generated with `workflow.skip_discuss=true`. Every implementation choice is at Claude's discretion, constrained only by the ROADMAP success criteria and codebase conventions (Python 3.8 floor, `from __future__ import annotations`, `logpose/` package, minimum-diff).

### Claude's Discretion
All implementation choices — parameterization signature pattern (positional args vs dataclass param bag vs keyword-only), test harness location, golden-file format, fixture storage. Recommendations below.

### Deferred Ideas (OUT OF SCOPE)
Explicitly out of scope for Phase 2:
- `GameSpec` dataclass definition → Phase 3
- `GAMES` registry → Phase 3
- `SettingsAdapter` dataclass → Phase 3
- `settings_section_rename` declarative expression → Phase 3
- `_fix_steam_sdk` generalization to sdk32 paths → Phase 5
- `arkserver.service.template` → Phase 5
- `_ark_parse` / `_ark_save` → Phase 5
- Typer factory / game-first CLI → Phase 4
- Merged polkit template → Phase 4

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARCH-04 (partial) | Helpers take game-specific values as args, not module globals | Section "Current Helper Signatures" enumerates each helper's current globals; "Parameterization Pattern" recommends the minimum-diff signature change |
| PAL-03 | `_palworld_parse(path) -> dict[str, str]` preserved verbatim | Section "OptionSettings Parser/Saver" shows exact regex lines to extract unchanged |
| PAL-04 | `_palworld_save(path, values)` with `should_quote` preserved verbatim | Section "OptionSettings Parser/Saver" shows exact saver body to lift |
| PAL-09 (harness half) | Byte-diff regression harness lands here; ARK half in Phase 5 | Sections "Golden-File Capture Strategy" + "Test Harness Recommendation" |
| SET-01 prep | `edit-settings` still works via new `_palworld_parse`/`_palworld_save` | Section "Call Sites" shows the single call site in `edit_settings()` command |
| E2E-01 | Byte-diff test — rendered Palworld service file matches v0.1.19 | Section "Fixture Design" locks the exact placeholder set and values |
| ARCH-05 (invariant) | No `BaseGame`, no `core/` split — flat `logpose/main.py` | Preserved: Phase 2 adds functions to existing module, no new modules |
| ARCH-06 (invariant) | `_run_command`, `_install_steamcmd`, `_repair_package_manager` untouched | Preserved: these helpers are game-agnostic and out of scope |
| PAL-01 (invariant) | `palserver.service` filename unchanged | Preserved: template filename stays `palserver.service.template`, rendered filename stays `palserver.service` |
| PAL-02 (invariant) | `palserver.service.template` byte-identical to v0.1.19 | Verified: `diff` exit 0 against `v0.1.19:palworld_server_launcher/templates/palserver.service.template` |
| PAL-06 (invariant) | Palworld launch args identical | Preserved: template `ExecStart=` line not modified |

## Project Constraints (from CLAUDE.md)

Extracted from `./CLAUDE.md` and `logpose/CLAUDE.md` and `logpose/templates/CLAUDE.md`:

- **Load-bearing helper:** `_repair_package_manager()` stays untouched per user's global CLAUDE.md ("GCP VMs and fresh Debian have broken dpkg state"). Phase 2 does not modify it.
- **Python 3.8 floor:** PEP-585 generics (`dict[str, str]`) require `from __future__ import annotations` on every module. Already present in `logpose/main.py` and `logpose/__init__.py` from Phase 1.
- **Minimum diff:** Touch only what's necessary. Three similar lines > premature abstraction. → Implies a plain parameter-list refactor, NOT a dataclass param bag yet (that's Phase 3's `GameSpec`).
- **No bundle commits:** One logical change per commit; one file per commit when possible → Phase 2 should split into atomic commits (extract `_palworld_parse`; extract `_palworld_save`; parameterize `_create_service_file`; parameterize install helpers; add harness + golden; update call sites).
- **Never commit `.planning/` to a repo** — already enforced; Phase 2's harness goes under `tests/`, NOT `.planning/`.
- **`gsd-fast` / `gsd-quick` routing:** Phase 2 is being executed via the full phase workflow (correct tier per user routing preferences memory entry).
- **Verification mandate:** Never mark done without proving it works — the byte-diff harness IS the proof mechanism for this phase and every subsequent one.

## Current-State Findings

### Current Helper Signatures (as of HEAD, post-Phase 1)

Source file: `/home/xzat/personal/palworld-server-launcher/logpose/main.py`

| Helper | Line | Current signature | Module globals read directly | Touched by Phase 2? |
|--------|------|-------------------|-------------------------------|---------------------|
| `_get_os_id()` | 25 | `() -> str` | None | No — game-agnostic |
| `_get_template(name)` | 39 | `(name: str) -> str` | None (uses `__file__`) | No — game-agnostic |
| `_run_command(command, check)` | 51 | `(command: str, check: bool = True) -> None` | None | No — ARCH-06 invariant |
| `_repair_package_manager()` | 76 | `() -> None` | None | No — load-bearing |
| `_install_steamcmd()` | 91 | `() -> None` | None | No — game-agnostic |
| `_run_steamcmd_update()` | 129 | `() -> None` | `PAL_SERVER_DIR`, hardcoded app_id `2394010` | **YES** — accept `server_dir: Path, app_id: int` |
| `_install_palworld()` | 137 | `() -> None` | None (calls `_run_steamcmd_update`) | **YES** — thin wrapper; signature parameterizes through |
| `_fix_steam_sdk()` | 143 | `() -> None` | `STEAM_DIR` | **YES** — accept `steam_sdk_dst: Path` (Palworld stays `~/.steam/sdk64`) |
| `_create_service_file(port, players)` | 160 | `(port: int, players: int) -> None` | `STEAM_DIR` (derives `pal_server_dir`) | **YES** — accept `service_name: str, template_name: str, working_directory: Path, exec_start_path: Path` |
| `_setup_polkit()` | 179 | `() -> None` | None (hardcodes `40-palserver.rules`, `palserver.rules.template`, `palserver.service` in template body) | **Partial** — accept `rules_filename: str, template_name: str`; rule body stays hardcoded to `palserver.service` until Phase 3 |
| `_parse_settings()` | 191 | `() -> dict[str, str]` | `PAL_SETTINGS_PATH` | **YES** — rename to `_palworld_parse(path: Path) -> dict[str, str]` (PAL-03) |
| `_save_settings(settings)` | 204 | `(settings: dict[str, str]) -> None` | `PAL_SETTINGS_PATH` | **YES** — rename to `_palworld_save(path: Path, settings: dict[str, str]) -> None` (PAL-04) |
| `_create_settings_from_default()` | 229 | `() -> None` | `DEFAULT_PAL_SETTINGS_PATH`, `PAL_SETTINGS_PATH`, hardcoded section-rename strings | **YES** — accept `default_path: Path, dst_path: Path, section_rename: Optional[tuple[str, str]]`; body preserves the `PalWorldSettings` → `PalGameWorldSettings` swap unchanged |
| `_display_settings(settings)` | 255 | `(settings: dict[str, str]) -> None` | None (just Rich table with hardcoded title "Palworld Server Settings") | **OPTIONAL** — minor parameterization (`title: str = "Palworld Server Settings"` keyword-only) is low-churn and preps Phase 3; acceptable to defer |
| `_interactive_edit_loop(settings)` | 269 | `(settings: dict[str, str]) -> None` | None | No — game-agnostic |

**Module-level constants that are the "game-specific module globals" being dissolved:**

```python
# Lines 19-22 of logpose/main.py
STEAM_DIR = Path.home() / ".steam/steam"
PAL_SERVER_DIR = STEAM_DIR / "steamapps/common/PalServer"
PAL_SETTINGS_PATH = PAL_SERVER_DIR / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini"
DEFAULT_PAL_SETTINGS_PATH = PAL_SERVER_DIR / "DefaultPalWorldSettings.ini"
```

**Phase 2 disposition:** The `PAL_*` constants MUST remain at module scope in Phase 2 — the Typer command bodies (`install`, `edit_settings`) need a source to read from. What changes is that **helper bodies stop reading them directly**; the command functions pass them in explicitly. Phase 3 is where these globals dissolve into `GAMES["palworld"]`. This is the "(partial)" in ARCH-04 for Phase 2.

`STEAM_DIR` is genuinely game-agnostic (shared root for all Steam installs) and can stay module-level indefinitely.

### Service File Rendering Mechanism

Source: `logpose/main.py:160-176` (`_create_service_file`).

Rendering is plain `str.format()` on the template read via `_get_template("palserver.service.template")`. The current placeholder set:

```
{user}                 # Path.home().name
{port}                 # CLI flag, default 8211
{players}              # CLI flag, default 32
{exec_start_path}      # str(pal_server_dir / "PalServer.sh")
{working_directory}    # str(pal_server_dir)
```

`pal_server_dir` is re-derived inside the helper as `STEAM_DIR / "steamapps/common/PalServer"`. **This is the duplication Phase 2 must remove** — the helper recomputes what `PAL_SERVER_DIR` already defines at module scope.

Written to disk via `_run_command(f"echo '{service_content}' | sudo tee {service_file}")` at `/etc/systemd/system/palserver.service`. The harness does NOT need to exercise the `sudo tee` path — it only needs to verify the **rendered string** is byte-equivalent to the v0.1.19 rendered string for the locked fixture.

### OptionSettings Parser/Saver (PAL-03 / PAL-04 body capture)

Source: `logpose/main.py:191-226`. These bodies must be lifted **verbatim** into the renamed functions.

**`_parse_settings()` body → `_palworld_parse(path)`:**
```python
def _palworld_parse(path: Path) -> dict[str, str]:
    """Parses a Palworld PalWorldSettings.ini file."""
    content = path.read_text()
    match = re.search(r"OptionSettings=\((.*)\)", content)
    if not match:
        raise ValueError("Could not find OptionSettings in PalWorldSettings.ini")

    settings_str = match.group(1)
    # This regex handles quoted strings and other values
    settings_pairs = re.findall(r'(\w+)=(".*?"|[^,]+)', settings_str)
    return {key: value.strip('"') for key, value in settings_pairs}
```

**`_save_settings(settings)` body → `_palworld_save(path, settings)`:**
```python
def _palworld_save(path: Path, settings: dict[str, str]) -> None:
    """Saves settings back to a Palworld PalWorldSettings.ini file."""
    content = path.read_text()

    def should_quote(value: str) -> bool:
        if value.lower() in ("true", "false", "none"):
            return False
        try:
            float(value)
            return False
        except ValueError:
            return True

    settings_str = ",".join(
        f'{key}="{value}"' if should_quote(value) else f"{key}={value}"
        for key, value in settings.items()
    )

    new_content = re.sub(
        r"OptionSettings=\(.*?\)", f"OptionSettings=({settings_str})", content
    )
    path.write_text(new_content)
    console.print("Settings saved successfully.")
```

**Byte-level requirements for PAL-03/PAL-04:**
- Regex strings copied character-for-character. `r"OptionSettings=\((.*)\)"` and `r'(\w+)=(".*?"|[^,]+)'` and `r"OptionSettings=\(.*?\)"` — do not "improve" any of them.
- `should_quote` inner function stays as a local nested function (not module-level) — this is how v0.1.19 ships.
- `console.print("Settings saved successfully.")` side effect preserved inside `_palworld_save`. Do not move the print to the caller (changes where output appears; also affects any ad-hoc smoke tests).
- The error message string `"Could not find OptionSettings in PalWorldSettings.ini"` stays verbatim (some users may grep for it; minimum diff).

### Call Sites

Exactly one command uses the parser/saver pair — `edit_settings` at `logpose/main.py:376-396`. One-for-one replacement:

**Before:**
```python
settings = _parse_settings()
...
_save_settings(settings)
```

**After:**
```python
settings = _palworld_parse(PAL_SETTINGS_PATH)
...
_palworld_save(PAL_SETTINGS_PATH, settings)
```

`_create_settings_from_default()` is called from `edit_settings` when `_parse_settings()` raises. Becomes:

```python
_create_settings_from_default(
    default_path=DEFAULT_PAL_SETTINGS_PATH,
    dst_path=PAL_SETTINGS_PATH,
    section_rename=("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]"),
)
```

`install()` command (line 296) calls `_install_steamcmd()`, `_install_palworld()`, `_fix_steam_sdk()`, `_create_service_file(port, players)`, `_setup_polkit()`. Each call site will be touched to pass explicit paths / service names / template names.

### v0.1.19 Golden Source — Availability Verified

**Tag present:** `git tag -l | grep v0.1.19` → `v0.1.19` (commit `3fbc260`, dated 2025-06-29).

**Byte-level verification performed during this research session:**

```bash
diff <(git show v0.1.19:palworld_server_launcher/templates/palserver.service.template) \
     logpose/templates/palserver.service.template
# exit 0 — byte-identical

diff <(git show v0.1.19:palworld_server_launcher/templates/palserver.rules.template) \
     logpose/templates/palserver.rules.template
# exit 0 — byte-identical
```

**Critical byte-level observation** — both templates end with a trailing space and NO final newline:

```
# palserver.service.template — file ends with "multi-user.target " (space, no \n)
# hex dump tail: 65 74 20         = "et " at offset 0x142; file size 323 bytes

# palserver.rules.template — file ends with "}});" + space, no \n
# hex dump tail: 7d 7d 29 3b 20   = "}});" then space; file size 248 bytes
```

**This trailing-space-no-newline fact is load-bearing.** The byte-diff harness MUST treat the template as `bytes`, not `str` with implicit newline normalization. Any editor that auto-adds a trailing newline (vim default `endofline`, some VS Code configs) will break the harness. **Recommend adding a `.gitattributes` rule or pre-commit check** to preserve these templates' end-of-file state, but that's Phase 2-adjacent polish — the harness's mere existence is the guardrail.

**Golden-file capture is simple because of the diff exit 0 above:** the rendered output of the CURRENT template with the locked fixture IS the v0.1.19 golden output. No need to check out v0.1.19, install a separate environment, or parse v0.1.19's `_create_service_file` — the template didn't change. Phase 1 preserved byte-equivalence (per `01-SUMMARY.md:38`).

### Test Infrastructure Baseline

- `tests/` directory does NOT exist yet (Glob confirmed).
- No `pytest.ini`, `pyproject.toml [tool.pytest.ini_options]`, `setup.cfg`, `tox.ini`, or `conftest.py` anywhere in the tree.
- No test dependency in `pyproject.toml`. Adding a `[project.optional-dependencies] test = ["pytest>=7"]` would be the clean move if tests get formal dependency tracking; NOT required for Phase 2 (pytest already available on the execution box — `pytest 9.0.3` confirmed via `which pytest`).
- `.gitignore` includes `.pytest_cache/` (added in Phase 1 commit `7257387`) — green-lit for test caching.

**Important caveat:** REQUIREMENTS.md lists TEST-01 (pytest harness) as deferred to v0.3+. Phase 2's harness is NOT that TEST-01 — it's a single-purpose regression oracle for Palworld service rendering, not a general testing framework. Keep it minimal (one test file, one golden file, zero fixtures beyond what PAL-09 demands). Do not let it grow into TEST-01 scope in this phase.

## Recommended Approach

### Parameterization Pattern

**Recommendation: explicit positional (or keyword) parameters, NOT a dataclass param bag.**

Rationale:
- Phase 3 will introduce `GameSpec` and `SettingsAdapter` dataclasses. Defining a Phase-2-only `PalworldPaths` dataclass now creates churn: Phase 3 would delete it and re-wire everything to `GameSpec`. Minimum-diff: skip the intermediate abstraction.
- The helpers take 1–4 parameters each after parameterization — well within "three similar lines > premature abstraction" territory from CLAUDE.md.
- Each helper's signature becomes self-documenting (`_create_service_file(service_name, template_name, user, port, players, exec_start_path, working_directory)`) — loud and grep-able, which matches the "no hidden module-global reads" discipline from PITFALLS.md Pitfall 6.

**Concrete recommended signatures:**

```python
def _run_steamcmd_update(server_dir: Path, app_id: int, binary_rel_path: str) -> None: ...
def _install_palworld(server_dir: Path, app_id: int, binary_rel_path: str) -> None: ...
def _fix_steam_sdk(steam_sdk_dst: Path, src_relpath: str = "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so") -> None: ...
def _create_service_file(
    service_name: str,
    template_name: str,
    user: str,
    working_directory: Path,
    exec_start_path: Path,
    port: int,
    players: int,
) -> None: ...
def _setup_polkit(rules_filename: str, template_name: str, user: str) -> None: ...
def _palworld_parse(path: Path) -> dict[str, str]: ...
def _palworld_save(path: Path, settings: dict[str, str]) -> None: ...
def _create_settings_from_default(
    default_path: Path,
    dst_path: Path,
    section_rename: Optional[tuple[str, str]] = None,
) -> None: ...
```

**Why this shape survives Phase 3 cleanly:** Phase 3's `GameSpec` will have exactly these fields (verified against ARCHITECTURE.md's canonical schema — `server_dir`, `binary_rel_path`, `settings_path`, `settings_section_rename`, `service_name`, `service_template_name`, `steam_sdk_paths`). The Phase 3 migration becomes a **call-site-only** change: helper bodies stay the same; callers switch from passing individual values to passing `spec.server_dir`, `spec.service_name`, etc. Zero helper-body churn across the Phase 2 → Phase 3 boundary.

**Why NOT keyword-only (`*, service_name: str, ...`):** Typer introspects function signatures for its command decorators, but these are internal helpers, not Typer commands — so keyword-only would be fine. However, positional-with-reasonable-order is equally safe and matches the existing `_create_service_file(port, players)` convention already in v0.1.19. Either works; pick consistency over churn.

### Fixture Design

The success criterion locks three values: `user=foo`, `port=8211`, `players=32`. These map to **three** of the five template placeholders. The other two (`working_directory`, `exec_start_path`) must also be locked to produce a deterministic render.

**Complete fixture (recommended):**

```python
FIXTURE = {
    "user": "foo",
    "port": 8211,
    "players": 32,
    "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
    "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
}
```

**Why these specific path strings:** They're what `_create_service_file` would compute for a user `foo` with `Path.home() == Path("/home/foo")` today — so `STEAM_DIR = /home/foo/.steam/steam` and `pal_server_dir = STEAM_DIR / "steamapps/common/PalServer"`. The harness can compute these by constructing paths under a fake home, or (simpler) just hardcode the strings in the fixture since they're stable inputs.

**Do not format the template with `Path` objects directly** — `str.format()` calls `str(path)` which on POSIX is fine (renders as `/home/foo/...`) but is a latent portability concern if the repo is ever cloned on Windows for reference. Explicitly cast to `str` in the fixture OR rely on POSIX `str(Path(...))` being identical to the string form (current v0.1.19 behavior). Either way, the fixture dict should contain `str` values for paths, not `Path` objects — keeps the golden-file comparison obvious.

**Golden capture sequence:**

1. In the test file, build the fixture dict above.
2. Read `logpose/templates/palserver.service.template` as bytes.
3. Render: `rendered = template_bytes.decode("utf-8").format(**FIXTURE).encode("utf-8")`.
4. Save once as `tests/golden/palserver.service.v0_1_19` via a one-shot `python tests/test_palworld_golden.py --capture` flag (or a separate `scripts/capture_golden.py`).
5. Commit that golden file.
6. Thereafter, the test reads the golden bytes and asserts equality after rendering through `_create_service_file`'s refactored output-building path.

### Golden-File Capture Strategy

**Two options considered.**

**Option A (recommended): "template didn't change, so current render IS golden."**

Because `diff` of the current template vs v0.1.19's shows zero bytes of difference (verified above), the golden file can be generated today from the current template without a time-travel checkout. This is the minimum-diff path. Capture script runs once during Phase 2 planning/implementation:

```python
# scripts/capture_golden.py (one-shot)
from pathlib import Path
tpl = (Path(__file__).parent.parent / "logpose/templates/palserver.service.template").read_bytes()
rendered = tpl.decode("utf-8").format(
    user="foo", port=8211, players=32,
    working_directory="/home/foo/.steam/steam/steamapps/common/PalServer",
    exec_start_path="/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
).encode("utf-8")
(Path(__file__).parent.parent / "tests/golden/palserver.service.v0_1_19").parent.mkdir(parents=True, exist_ok=True)
(Path(__file__).parent.parent / "tests/golden/palserver.service.v0_1_19").write_bytes(rendered)
print(f"wrote {len(rendered)} bytes")
```

**Option B: "time-travel checkout of v0.1.19."**

Use `git show v0.1.19:palworld_server_launcher/templates/palserver.service.template` to fetch the historical template, feed it through an ad-hoc `format()` that matches v0.1.19's `_create_service_file` body exactly, capture the output. More paranoid, but unnecessary given the byte-diff-zero evidence. Document as a fallback if anyone doubts Option A's premise; not the primary path.

**Storage format:** Plain raw bytes file under `tests/golden/`. Not JSON-encoded, not base64 — raw bytes so `diff tests/golden/palserver.service.v0_1_19 <actual>` works interactively during debugging. (Explicitly: do not use Python's `pickle` or any binary-serialization wrapper — raw bytes match the on-disk systemd unit format directly.)

**Do NOT store the golden as a Python string literal inside the test file** — escaping the trailing-space-no-newline is error-prone and any auto-formatter (black) will normalize it. A separate bytes file is robust.

### Test Harness Recommendation

**Framework:** pytest. Already available globally (`pytest 9.0.3`). No `conftest.py` needed. No plugins required.

**Location:** `tests/test_palworld_golden.py` at repo root. Rationale: stdlib test discovery (`pytest tests/`) finds it by default. Alternative `logpose/tests/` would make it importable as a submodule but violates the "no new modules in package" minimum-diff target and would get picked up by `packages = ["logpose"]` if not carefully excluded.

**Dual-entrypoint shape (satisfies phase criterion #3 "script exits 0"):**

```python
# tests/test_palworld_golden.py
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "logpose/templates/palserver.service.template"
GOLDEN = ROOT / "tests/golden/palserver.service.v0_1_19"

FIXTURE = {
    "user": "foo",
    "port": 8211,
    "players": 32,
    "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
    "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
}

def _render() -> bytes:
    return TEMPLATE.read_bytes().decode("utf-8").format(**FIXTURE).encode("utf-8")

def test_palserver_service_byte_identical_to_v0_1_19() -> None:
    rendered = _render()
    expected = GOLDEN.read_bytes()
    assert rendered == expected, (
        f"palserver.service rendering drift vs v0.1.19 "
        f"({len(rendered)} rendered bytes vs {len(expected)} golden bytes). "
        f"Run `diff <(python -c '...') {GOLDEN}` to inspect."
    )

if __name__ == "__main__":
    try:
        test_palserver_service_byte_identical_to_v0_1_19()
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    print("OK: palserver.service matches v0.1.19 golden")
```

**Invocation modes (both must exit 0):**

```bash
pytest tests/test_palworld_golden.py -x        # Phase 2 CI-style
python tests/test_palworld_golden.py           # Phase 2 script-style (success criterion #3)
```

**Bonus test to add in the same file** — validates that the golden capture itself is correct by re-reading the v0.1.19 tag's template (paranoia; one-time cost):

```python
def test_golden_matches_v0_1_19_tag() -> None:
    """Sanity: our golden was captured from a template that matches v0.1.19 byte-for-byte."""
    import subprocess
    v019_template = subprocess.check_output(
        ["git", "show", "v0.1.19:palworld_server_launcher/templates/palserver.service.template"],
    )
    current_template = TEMPLATE.read_bytes()
    assert v019_template == current_template, "Template drifted vs v0.1.19 tag — golden invalid"
```

**The phase-3-through-phase-5 contract:** Every subsequent phase's verify step invokes `pytest tests/test_palworld_golden.py -x` and refuses merge on non-zero exit. This harness is THE Palworld oracle for the rest of v0.2.0.

## Runtime State Inventory

Phase 2 is a code-only refactor plus new test files. No rename-at-runtime, no data migration, no OS-registered state changes. Categories:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 2 does not touch `PalWorldSettings.ini` structure, `DefaultPalWorldSettings.ini`, or any saved state files | None |
| Live service config | None — `palserver.service` unit name unchanged (PAL-01), systemd reload only happens when `_create_service_file` is called by `install`, which is not exercised by the harness | None |
| OS-registered state | None — polkit rule filename `40-palserver.rules` unchanged in Phase 2 (merges to `40-logpose.rules` in Phase 4); no systemd timer/target/slice changes | None |
| Secrets/env vars | None — no env vars, no secrets referenced in Phase 2 scope | None |
| Build artifacts | `palworld_server_launcher.egg-info/` directory may still exist on disk as untracked (per Phase 1 SUMMARY line 32); Phase 2 does not need to touch it; `logpose.egg-info` may regenerate if anyone runs `pip install -e .` — both covered by Phase 1's `.gitignore` update | None (safe to `rm -rf palworld_server_launcher.egg-info/` but not required) |

**Canonical question:** *After every file in the repo is updated for Phase 2, what runtime systems still have the old string cached, stored, or registered?* → Nothing — Phase 2 introduces `_palworld_parse` and `_palworld_save` as **new** names alongside the existing (to-be-removed) `_parse_settings` / `_save_settings`. There is no systemd-registered service name change, no polkit rule rename, no stored-data key rename, no package reinstall needed. This phase's surface area is entirely in the source tree and the new `tests/` directory.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime + test execution | ✓ | 3.14.4 (system), but code must work on 3.8+ floor per PKG-04 | — |
| pytest | Harness execution | ✓ | 9.0.3 at `/bin/pytest` | Script-mode fallback (`python tests/test_palworld_golden.py`) always available |
| git | Golden-source verification in optional `test_golden_matches_v0_1_19_tag` | ✓ | (project is in a git repo) | Skip optional test via `pytest.importorskip` pattern or `pytest.skip` if `git` missing |
| typer, rich | Importing `logpose.main` from tests (if needed) | ✓ | Pinned `typer>=0.9,<0.21`, `rich>=13.0,<14` per `pyproject.toml` | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

**Note on Python version:** The execution machine has Python 3.14.4, but PKG-04 locks the floor at 3.8. The harness uses only stdlib + pytest, no features beyond 3.8. Runtime verification on a 3.8 interpreter is acknowledged as deferred per Phase 1 SUMMARY item 7 — Phase 2's harness will NOT gate on 3.8 specifically; it gates on "pytest passes on whatever interpreter is invoking it." If Phase 6 adds CI, CI matrix can exercise 3.8 explicitly.

## Common Pitfalls

### Pitfall 1: Trailing-space / newline drift in the template
**What goes wrong:** Editor auto-adds a trailing newline to `palserver.service.template`; next render differs from golden by 1 byte; harness fires; operator spends 20 minutes wondering why a "cosmetic" change broke everything.
**Why it happens:** Both templates end with a literal space and no final newline (`20` byte, no `0a`). Vim with default `fixendofline` adds `\n`. VS Code's "Files: Insert Final Newline" setting does the same. Most formatters would "helpfully" strip the trailing space.
**How to avoid:** (a) The harness itself IS the detector — it fires and stops the phase until the bytes match. (b) Recommend adding `.gitattributes` entry `logpose/templates/* -text` to disable text-mode transforms for the two template files. (c) Document the trailing-space invariant in `logpose/templates/CLAUDE.md` (one line added).
**Warning signs:** `diff -a tests/golden/palserver.service.v0_1_19 <(python3 -c 'import logpose.main; ...')` shows a single-byte diff at EOF.

### Pitfall 2: Helper with default-arg game key (forbidden per PITFALLS Pitfall 6.1)
**What goes wrong:** Temporarily-introduced `def _fix_steam_sdk(steam_sdk_dst: Path = Path.home() / ".steam/sdk64") -> None:` as a "compat shim." Later, ARK calls into this helper and forgets to override the default — silent mis-configuration.
**How to avoid:** Make every parameterized helper's game-specific args **required positional (or keyword without defaults)**. No defaults for `server_dir`, `settings_path`, `service_name`, `template_name`, `rules_filename`. If a fallback feels needed for backwards-compat, it's a sign the refactor isn't minimum-diff — delete the old call and update the caller instead.
**Warning signs:** `grep -n "def _" logpose/main.py | grep '= Path\.home\|= "pal'` returns any result after Phase 2 is "done."

### Pitfall 3: `_palworld_parse` / `_palworld_save` body drift
**What goes wrong:** A well-meaning contributor "simplifies" the regex (`r"(\w+)=(\".*?\"|[^,]+)"` → `r"(\w+)=([^,]+)"`), breaking quoted string handling. Or "fixes" `should_quote` to use `isinstance` checks instead of `float()` ValueError. PAL-04's "verbatim" invariant is violated.
**How to avoid:** The commit that extracts these functions must produce zero changes to the logic. Use a **git-level verification**: `diff <(git show HEAD~1:logpose/main.py | sed -n '/def _parse_settings/,/^def /p') <(sed -n '/def _palworld_parse/,/^def /p' logpose/main.py)` — the non-signature lines should differ only in the `content = path.read_text()` vs `content = PAL_SETTINGS_PATH.read_text()` change. Add a comment `# verbatim from v0.1.19 _parse_settings — PAL-03 invariant` above each extracted function so future readers know to treat it as load-bearing.
**Warning signs:** Reviewer's `git diff` on the extraction commit shows any regex characters changed, any control-flow changed, or `should_quote` signature changed.

### Pitfall 4: Harness silently passes because it's running the helper unused code path
**What goes wrong:** The harness reads `TEMPLATE.read_bytes().format(**FIXTURE)` directly, bypassing `_create_service_file` entirely. `_create_service_file` is refactored incorrectly but the harness never exercises it, so it stays green. Phase 3/4/5 then inherit a broken helper.
**How to avoid:** In addition to the "render template directly" test, add a second test that **calls `_create_service_file`** and captures what it would write. This requires mocking `_run_command` (so `sudo tee` doesn't actually execute) OR refactoring `_create_service_file` to return the rendered string (and a thin caller does the `_run_command` tee). Recommend the latter — split `_create_service_file` into `_render_service_file(...) -> str` + `_write_service_file(content, path)`. The harness tests `_render_service_file`; `install()` calls `_write_service_file(_render_service_file(...), path)`. Minimum-diff additional helper, maximum regression coverage.
**Warning signs:** The harness passes, but manually running `logpose palworld install --port 8211 --players 32` and `diff` against the v0.1.19 install's `/etc/systemd/system/palserver.service` on a test VM shows differences. If CI has the harness green but manual E2E shows drift, the harness is testing the wrong path.

### Pitfall 5: Test file accidentally packaged into the wheel
**What goes wrong:** `pyproject.toml` has `packages = ["logpose"]` — safe, `tests/` not included. But if someone "improves" build config with `find:` or adds `logpose.tests`, the test + golden files ship in the wheel. Wheel bloat; potential runtime import failures on install.
**How to avoid:** Keep `packages = ["logpose"]` explicit; do NOT switch to `find:`. Phase 6's wheel verification (`unzip -p dist/*.whl ...`) should cross-check that `tests/` is absent from the wheel contents. Phase 2 does not need to act, just not regress.
**Warning signs:** `unzip -l dist/logpose_launcher-0.2.0-*.whl | grep -i test` returns anything in Phase 6.

### Pitfall 6: Section-rename string drift in `_create_settings_from_default`
**What goes wrong:** The hardcoded strings `"[/Script/Pal.PalWorldSettings]"` and `"[/Script/Pal.PalGameWorldSettings]"` get split across lines, indentation-adjusted, or quoted differently. Any change means the Palworld default-settings bootstrap silently stops working.
**How to avoid:** Pass these as a single `section_rename: Optional[tuple[str, str]]` parameter. Inside the helper, the replacement is a one-liner `content = content.replace(old, new)` — unchanged from v0.1.19. Preserve byte-for-byte.
**Warning signs:** A user running `logpose palworld edit-settings` on a freshly-installed server (no `PalWorldSettings.ini` yet) sees the interactive edit loop run on a file that still has `[/Script/Pal.PalWorldSettings]` — Palworld then ignores the edits at next launch.

## Parameterization Pattern Recommendation (Summary)

Pick **explicit per-parameter signatures** (not a dataclass bag, not a TypedDict, not `**kwargs`). Every game-specific value is a named function parameter. Phase 3 will wrap these same signatures behind `GameSpec`-sourced values; the helper bodies don't change.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Phase-2-only `PalworldPaths` dataclass | Churn: Phase 3 deletes it. Minimum-diff violated. |
| `TypedDict` param bag | Same churn problem; adds `typing_extensions` dep on 3.8 for full support. |
| `**kwargs: Any` with string keys | Silent typos, no IDE support, violates "explicit > implicit" and PITFALLS Pitfall 6 ("no module-global reads, make callers loud"). |
| Monkey-patch module globals inside tests | Brittle, order-dependent, fails on parallel pytest runs. |
| Instance method on a `PalworldLauncher` class | Reintroduces the `BaseGame` class hierarchy the user explicitly rejected (ARCH-05 invariant). |
| Closures capturing paths in `install()` | Hard to test; helpers become non-top-level; hurts Phase 3 factor. |

## Sources

### Primary (HIGH confidence)
- `/home/xzat/personal/palworld-server-launcher/logpose/main.py` — current helper bodies, signatures, call sites (read in full)
- `/home/xzat/personal/palworld-server-launcher/logpose/templates/palserver.service.template` — 323 bytes, 5 placeholders, trailing-space-no-newline verified via `xxd`
- `/home/xzat/personal/palworld-server-launcher/logpose/templates/palserver.rules.template` — 248 bytes, 1 placeholder (`{user}`), trailing-space-no-newline verified
- `git show v0.1.19:palworld_server_launcher/templates/*.template` — golden-source verified byte-identical via `diff` exit 0
- `/home/xzat/personal/palworld-server-launcher/pyproject.toml` — post-Phase-1 state confirmed (`name = "logpose-launcher"`, pinned `typer>=0.9,<0.21`)
- `.planning/research/ARCHITECTURE.md` — Phase 3's `GameSpec` schema used to validate Phase 2 signatures survive the transition
- `.planning/research/PITFALLS.md` — Pitfall 6 (refactor regression leaks) drives harness-as-oracle discipline
- `.planning/research/SUMMARY.md` — Risks 1 (Palworld regression) and the phase build-order rationale
- `.planning/phases/01-rename-hygiene/01-SUMMARY.md` — confirms Phase 1 preserved template byte-equivalence

### Secondary (MEDIUM confidence)
- User's global CLAUDE.md — routing preferences + core principles (simplicity, minimum-diff, root-causes)
- `/home/xzat/personal/palworld-server-launcher/CLAUDE.md` + `logpose/CLAUDE.md` + `logpose/templates/CLAUDE.md` — project-level documentation

### Tertiary (LOW confidence)
None. Phase 2 is entirely local-codebase-driven; no external library research needed.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Path.home().name` on the test box equals the login shell's `$USER` (Palworld install's `{user}` source) | Fixture Design | Minor — only relevant if someone mis-captures the golden on a box where `$USER != basename($HOME)`. Mitigation: hardcode `user="foo"` in the fixture and NEVER let the harness read `Path.home().name`. |
| A2 | `str(Path("/home/foo/.steam/steam/steamapps/common/PalServer"))` renders identically in the harness and in `_create_service_file` on all POSIX systems | Fixture Design | Negligible on POSIX; `pathlib.PosixPath.__str__` is deterministic. Would break on Windows, which is out of scope per REQUIREMENTS.md "Out of Scope" table. |
| A3 | Python 3.8 will run the harness correctly (only used stdlib + pytest) | Test Harness Recommendation | Low — harness uses `Path`, `bytes`, `.format()`, `subprocess` (in optional test), all 3.8-safe. No walrus, no `match`, no PEP-604 `X \| Y` unions (we use `Optional[...]`). |
| A4 | `pytest 9.x` behavior for a plain `def test_...` function matches `pytest 7.x` and 8.x (the pinned floor per typical project support) | Test Harness Recommendation | Negligible — bare assert-style tests are stable pytest API since 2.0. |
| A5 | The phase success criterion "script exits 0" is satisfied by either `pytest ... && echo ok` or `python tests/test_palworld_golden.py` | Test Harness Recommendation | Low — the dual-entrypoint design covers both interpretations. Plan-phase should confirm which the verifier will invoke. |

All five are `[ASSUMED]`-level claims the planner can confirm in one quick pass during `/gsd-plan-phase 2`.

## Open Questions (RESOLVED)

1. **Should `_create_service_file` split into `_render_service_file` + `_write_service_file`?**
   - What we know: Pitfall 4 above argues for the split (enables testing the real render path, not just a template-format shortcut).
   - What's unclear: Whether the Phase 2 exit criteria demand harness coverage of the helper specifically (criterion #3 says "renders `palserver.service` against fixture" — ambiguous about whether "renders" means calling the helper or formatting the template).
   - Recommendation: **Do the split.** Net +3 lines of code, much stronger regression coverage, and matches the minimum-diff principle because it's a pure refactor (no new logic).
   - **RESOLVED:** Split implemented in Plan 03 Task 2 (`02-03-parameterize-helpers-PLAN.md`). Harness in Plan 05 asserts byte-equality against real render path.

2. **Should the golden file be committed or gitignored + regenerated in CI?**
   - What we know: Committing the golden makes the regression check reproducible on any developer's machine without `git show v0.1.19`.
   - What's unclear: Whether `.planning/` gitignore conventions extend to `tests/golden/`. They don't — `tests/` is source code, not planning state.
   - Recommendation: **Commit the golden file.** ~260 bytes, changes essentially never (only if v0.1.19 Palworld service semantics are intentionally abandoned, which would be a major version bump).
   - **RESOLVED:** Golden committed in Plan 01 Task 2 (`02-01-golden-fixture-and-harness-PLAN.md`) at `tests/golden/palserver.service.golden`.

3. **Should Phase 2 also touch `_setup_polkit`?**
   - What we know: `_setup_polkit` hardcodes `palserver.rules` filename AND the rule body hardcodes `"palserver.service"`. ARCH-04 mentions `_setup_polkit` in Phase 3, not Phase 2.
   - What's unclear: Whether the plan-phase should parameterize the filename + template name in Phase 2 for symmetry, leaving the template body's `palserver.service` literal untouched until Phase 4 (merged polkit).
   - Recommendation: **Light touch in Phase 2** — parameterize the two path/filename args (`rules_filename`, `template_name`, `user`). Leave the template body's `palserver.service` literal alone until Phase 4. Matches the "partial" qualifier on ARCH-04.
   - **RESOLVED:** Light-touch parameterization implemented in Plan 03 Task 3. Rule body's `palserver.service` literal preserved verbatim for Phase 4.

## Validation Architecture

Skipped per `workflow.nyquist_validation: false` in `.planning/config.json` (line 19). Phase 2's regression harness is the substitute validation mechanism — it's the only test artifact the phase emits, and it's load-bearing for Phases 3–5.

## Metadata

**Confidence breakdown:**
- Current helper signatures: HIGH — verified by reading `logpose/main.py` end-to-end
- v0.1.19 byte-equivalence of templates: HIGH — `diff` exit 0 verified in this session
- Fixture placeholder enumeration: HIGH — `str.format()` placeholder set is deterministic from reading the template
- Parameterization pattern choice: HIGH — grounded in ARCHITECTURE.md's Phase 3 schema + minimum-diff principle from CLAUDE.md
- Harness framework choice: HIGH — pytest available, stdlib-only otherwise, dual-entrypoint pattern solves the "script exits 0" criterion
- Pitfalls: HIGH for template byte-drift, default-arg forbidden, verbatim-body discipline (all grounded in PITFALLS.md and observed v0.1.19 bytes)

**Research date:** 2026-04-12
**Valid until:** Phase 3 lands (which will supersede parameterization with `GameSpec`); the byte-diff harness itself is valid until Palworld semantics are intentionally changed (milestone v0.3+).

## RESEARCH COMPLETE
