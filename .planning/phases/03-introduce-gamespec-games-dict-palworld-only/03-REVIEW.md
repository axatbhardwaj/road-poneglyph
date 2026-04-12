---
phase: 03-introduce-gamespec-games-dict-palworld-only
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - logpose/main.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Phase 3 is a mechanical, byte-diff-preserving refactor that introduces two frozen dataclasses (`SettingsAdapter`, `GameSpec`), a module-scope `GAMES` registry with a single `"palworld"` entry, and a `post_install_hooks` pattern. All command call sites were rewired from `PAL_*` module globals to `spec = GAMES["palworld"]`; `_fix_steam_sdk` was wrapped in a zero-arg `_palworld_sdk_hook`.

The refactor is clean and preserves existing semantics. No bugs or security issues were introduced by Phase 3. However, the newly-added hook wrapper surfaces a long-standing shell-quoting latent bug (one of the paths threaded through it contains spaces), which is now worth flagging since it sits on the Phase 3 code path.

A few Info-level items note scaffolding fields wired in but not yet consumed (intended for Phases 4/5), plus a type-vs-guard mismatch on `default_settings_path` that is safe today but will bite if a future `GameSpec` legitimately sets it to `None`.

## Warnings

### WR-01: `_fix_steam_sdk` passes space-containing paths through `shell=True` without quoting

**File:** `logpose/main.py:172` (and the hook wrapper at `logpose/main.py:341-343`)

**Issue:** `_fix_steam_sdk` runs `_run_command(f"cp {steam_client_so} {steam_sdk_dst}/")` with `shell=True`. The `steam_client_so` value wired through `_palworld_sdk_hook` is `~/.steam/steam/steamapps/common/Steamworks SDK Redist/linux64/steamclient.so`, which contains spaces ("Steamworks SDK Redist"). Under `shell=True`, the shell word-splits `cp /a b c/file.so /dst/` into four arguments, and the command fails (or, worse, silently copies the wrong file if a partial path happens to exist).

This bug predates Phase 3 — it lived in `_fix_steam_sdk` before the hook extraction — but Phase 3 now explicitly owns the glue (`_palworld_sdk_hook` was added this phase and threads the path in), so it's worth recording here rather than letting it ride.

Also applies to the adjacent `_run_command(f"chmod +x {server_script}")` at line 164, though `server_script` (`PalServer.sh` under `PalServer/`) has no spaces today.

**Fix:** Use a list form with `shell=False`, or quote via `shlex.quote`:

```python
import shlex
# in _fix_steam_sdk:
_run_command(f"cp {shlex.quote(str(steam_client_so))} {shlex.quote(str(steam_sdk_dst))}/")
```

Or, preferred — bypass the shell entirely for a simple file copy:

```python
import shutil
# in _fix_steam_sdk:
shutil.copy2(steam_client_so, steam_sdk_dst)
```

Either fix belongs in a future phase; Phase 3's mandate was a byte-diff-preserving refactor, so changing `_fix_steam_sdk` semantics here would have violated the plan. Flag forward.

## Info

### IN-01: `GameSpec.default_settings_path: Optional[Path]` is passed to a non-Optional parameter

**File:** `logpose/main.py:41, 475-479, 261-265`

**Issue:** `GameSpec.default_settings_path` is typed `Optional[Path]`, but in `edit_settings` it is passed directly to `_create_settings_from_default(default_path: Path, ...)`. For the current `"palworld"` entry the value is non-None, so there is no runtime issue, but a future `GameSpec` that legitimately sets `default_settings_path=None` (e.g., an ARK entry whose workflow creates settings differently) would hit `AttributeError: 'NoneType' object has no attribute 'exists'` inside `_create_settings_from_default`.

**Fix:** Either tighten the field type to `Path` (if None is never intended) or guard at the call site:

```python
if spec.default_settings_path is None:
    rich.print("No default settings template registered for this game.", file=sys.stderr)
    sys.exit(1)
_create_settings_from_default(spec.default_settings_path, spec.settings_path, spec.settings_section_rename)
```

### IN-02: `install_options` dict is populated but never read

**File:** `logpose/main.py:49, 365`

**Issue:** `GameSpec.install_options` is defined as `dict[str, object]` and the palworld entry sets `{"port_default": 8211, "players_default": 32}`. Nothing in the module reads these values — `install()` still uses Typer's own `8211` / `32` defaults hard-coded in the option signatures. This is scaffolding for a later phase (likely 4's factory), so it's intentional dead data, but worth noting so the reader doesn't assume the `GameSpec` values are authoritative.

**Fix:** Add a comment at the `install_options` field declaration noting that it is reserved for Phase 4's `_build_game_app` factory, or defer the field's introduction until it's consumed.

### IN-03: `apt_packages` / `steam_sdk_paths` are declared but unused in Phase 3

**File:** `logpose/main.py:47-48, 363-364`

**Issue:** Same pattern as IN-02: `apt_packages=[]` and `steam_sdk_paths=[(_PAL_STEAM_CLIENT_SO, _PAL_SDK64_DST)]` are set on the palworld spec but never read (the hook in `post_install_hooks` drives the copy directly). These fields are forward-scaffolding for the factory phase; once the factory iterates them, the hook can collapse into a generic loop.

**Fix:** No action required in Phase 3. When Phase 4 lands the factory, either have it consume `steam_sdk_paths` uniformly (and drop `_palworld_sdk_hook`) or delete the field if `post_install_hooks` remains the sole mechanism.

### IN-04: `GAMES: dict[str, GameSpec]` is module-mutable

**File:** `logpose/main.py:346`

**Issue:** `GameSpec` is frozen, but the `GAMES` dict itself is a plain `dict` — a caller could mutate or replace entries at runtime (e.g., `GAMES["palworld"] = ...` in a test fixture that forgets to restore). Given this is an internal CLI tool, the practical risk is near-zero, but a `MappingProxyType` wrapper would make the registry read-only without touching any call site.

**Fix:**

```python
from types import MappingProxyType

_GAMES_MUTABLE: dict[str, GameSpec] = {"palworld": GameSpec(...)}
GAMES: "Mapping[str, GameSpec]" = MappingProxyType(_GAMES_MUTABLE)
```

Optional — pure hardening, no current defect.

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
