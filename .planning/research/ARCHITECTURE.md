# Architecture Research

**Domain:** Python/Typer CLI refactor — in-place generalization of a single-game launcher into a multi-game dispatcher (Palworld + ARK)
**Researched:** 2026-04-12
**Confidence:** HIGH (grounded in existing code; every recommendation minimum-diff)

## Standard Architecture

### System Overview (target shape)

```
┌─────────────────────────────────────────────────────────────┐
│                     logpose/main.py                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Typer root   │──│ per-game sub │  (factory-built)        │
│  │  app         │  │  apps        │                         │
│  └──────┬───────┘  └──────┬───────┘                         │
│         │                 │                                  │
├─────────┴─────────────────┴──────────────────────────────────┤
│                    GAMES: dict[str, GameSpec]                │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ "palworld"       │  │ "ark"            │                 │
│  │ GameSpec(...)    │  │ GameSpec(...)    │                 │
│  └────────┬─────────┘  └────────┬─────────┘                 │
├───────────┴─────────────────────┴───────────────────────────┤
│        Helper functions (parameterized by GameSpec)          │
│  _run_command, _install_steamcmd, _repair_package_manager,  │
│  _run_steamcmd_update(spec), _create_service_file(spec,...),│
│  _setup_polkit(), _fix_steam_sdk (hook), _edit_settings(spec)│
├─────────────────────────────────────────────────────────────┤
│                      Settings Adapters                       │
│   _palworld_parse/save (regex OptionSettings=(...))          │
│   _ark_parse/save (configparser stdlib)                      │
├─────────────────────────────────────────────────────────────┤
│                      Templates (flat)                         │
│  palserver.service.template (unchanged)                      │
│  arkserver.service.template (new)                            │
│  40-logpose.rules.template (new, merged polkit rule)         │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `logpose/main.py` | Single module entry — Typer root, factory, GAMES dict, all helpers, all adapters | Python 3.8+, stdlib + typer + rich only |
| `GAMES` dict | Frozen registry of per-game config (static data + callables) | `dict[str, GameSpec]` where `GameSpec` is a frozen dataclass |
| Typer sub-apps | Game-first subcommand routing (`logpose palworld install`) | Factory `_build_game_app(spec) -> typer.Typer`, registered via `app.add_typer(...)` in a loop |
| Settings adapter | Parse/save game config INI files behind uniform interface | Two callables (parse, save) on a `SettingsAdapter` dataclass — one instance per game |
| Templates | Render systemd unit + polkit rule | `str.format()`-based, flat filename namespace (`<game>server.service.template`) |

## `GameSpec` Dataclass — Canonical Schema

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

@dataclass(frozen=True)
class SettingsAdapter:
    parse: Callable[[Path], dict[str, str]]
    save: Callable[[Path, dict[str, str]], None]

@dataclass(frozen=True)
class GameSpec:
    key: str                                       # "palworld", "ark"
    display_name: str                              # "Palworld", "ARK: Survival Evolved"
    app_id: int                                    # SteamCMD app id
    server_dir: Path                               # STEAM_DIR / "steamapps/common/<subdir>"
    binary_rel_path: str                           # relative to server_dir
    settings_path: Path                            # absolute path to editable INI
    default_settings_path: Optional[Path]          # None for ARK
    settings_section_rename: Optional[tuple[str, str]]  # Palworld-only header rewrite
    service_name: str                              # "palserver" / "arkserver" (no suffix)
    service_template_name: str                     # filename in templates/
    settings_adapter: SettingsAdapter
    post_install_hooks: list[Callable[[], None]] = field(default_factory=list)
```

**Why dataclass over plain `dict`:** Typo-safe, frozen, autocomplete, zero runtime cost, stdlib only. Not a class hierarchy — it's a struct. User's constraint rejected `BaseGame` (behavior/polymorphism), not dataclasses (data shape).

**Fields dropped vs original proposal:**
- `launch_args_template` — duplicated in `service_template` (`ExecStart=` line) — drop
- `rules_template_name` — single merged polkit file covers all games — drop

**Fields added:**
- `display_name` — for user-facing messages (`console.print`, tables)
- `settings_section_rename` — preserves Palworld's `PalWorldSettings` → `PalGameWorldSettings` quirk
- `post_install_hooks` — `_fix_steam_sdk()` is Palworld-only, expressed declaratively

## Settings Adapter Pattern

**Recommendation:** Dataclass holding two top-level functions per game. No module split.

```python
def _palworld_parse(path: Path) -> dict[str, str]: ...  # existing regex logic
def _palworld_save(path: Path, settings: dict[str, str]) -> None: ...  # existing

def _ark_parse(path: Path) -> dict[str, str]:
    import configparser
    cp = configparser.ConfigParser(strict=False, interpolation=None, allow_no_value=True)
    cp.optionxform = str  # CRITICAL: preserve case; default folds to lowercase
    cp.read(path)
    return {f"{s}.{k}": cp[s][k] for s in cp.sections() for k in cp[s]}

def _ark_save(path: Path, settings: dict[str, str]) -> None:
    import configparser
    cp = configparser.ConfigParser(strict=False, interpolation=None, allow_no_value=True)
    cp.optionxform = str
    cp.read(path)  # preserve untouched keys
    for flat_key, value in settings.items():
        section, key = flat_key.split(".", 1)
        if not cp.has_section(section): cp.add_section(section)
        cp[section][key] = value
    with open(path, "w") as f:
        cp.write(f, space_around_delimiters=False)
```

**Rejected alternatives:** Separate modules (violates minimum-diff), plain dict with function refs (no type safety), lambdas (ARK parser state too complex), `BaseAdapter` class (abstraction cost > benefit with 2 impls).

## Typer Subcommand Composition Pattern

**Recommendation:** Factory function producing per-game `Typer` sub-app, registered in a loop.

```python
app = typer.Typer(help="logpose — multi-game dedicated server launcher.")

def _build_game_app(spec: GameSpec) -> typer.Typer:
    sub = typer.Typer(help=f"Manage {spec.display_name} dedicated server.")

    @sub.command()
    def start() -> None: _run_command(f"systemctl start {spec.service_name}")

    @sub.command()
    def stop() -> None: _run_command(f"systemctl stop {spec.service_name}")

    # ... restart, status, enable, disable, update, edit-settings

    # Per-game install — options differ
    if spec.key == "palworld":
        @sub.command()
        def install(port: int = typer.Option(8211),
                    players: int = typer.Option(32),
                    start: bool = typer.Option(False, "--start")) -> None:
            _install_game(spec, {"port": port, "players": players}, autostart=start)
    elif spec.key == "ark":
        @sub.command()
        def install(map: str = typer.Option("TheIsland"),
                    session_name: str = typer.Option("logpose-ark"),
                    admin_password: str = typer.Option(..., prompt=True, hide_input=True),
                    game_port: int = typer.Option(7777),
                    query_port: int = typer.Option(27015),
                    rcon_port: int = typer.Option(27020),
                    players: int = typer.Option(70),
                    start: bool = typer.Option(False, "--start")) -> None:
            _install_game(spec, {...}, autostart=start)

    return sub

for key, spec in GAMES.items():
    app.add_typer(_build_game_app(spec), name=key)
```

**Why factory over loop-with-decorators:** Naked `for` + `@sub.command()` decorators capture loop variables incorrectly — all closures bind to the last `spec`. Factory takes `spec` as parameter → binds correctly.

**Rejected alternatives:**
- Shared `install` with `**options` — Typer cannot introspect `**kwargs`; breaks `--help`
- One root command with `--game` flag — rejected by user (game-first ergonomics)

## Template Organization

**Recommendation:** Flat `templates/` with per-game filenames.

```
logpose/templates/
├── palserver.service.template       # unchanged from v0.1.19
├── arkserver.service.template       # NEW
└── 40-logpose.rules.template        # NEW (replaces palserver.rules.template)
```

**Why flat:** Zero churn to existing file. `pyproject.toml` glob `templates/*` unchanged. Per-subdir organization is premature at 2 games.

## Polkit Rule Strategy

**Recommendation:** Single merged rules file `40-logpose.rules`, regenerated on every install, listing all known game service units from the `GAMES` dict.

```javascript
// /etc/polkit-1/rules.d/40-logpose.rules (template)
polkit.addRule(function(action, subject) {{
    var units = [{units}];  // expanded at install time from GAMES
    if (action.id == "org.freedesktop.systemd1.manage-units" &&
        units.indexOf(action.lookup("unit")) !== -1 &&
        subject.user === "{user}") {{
        return polkit.Result.YES;
    }}
}});
```

**Rationale:**
- Adding a new game later → regenerate file with new unit list automatically from `GAMES.values()`
- Old `40-palserver.rules` from v0.1.19 coexists additively (Polkit merges across files) — no breakage for existing v0.1.19 installs
- Listing units that don't exist yet is a no-op — zero harm from pre-listing all known games

**PITFALLS note (flagged for PITFALLS.md):** Every `{` and `}` in JS template body must be doubled (`{{` / `}}`) for `str.format()` — more JS lines means more escape opportunities to miss.

## Build Order (Dependency-Justified)

Ordered to keep Palworld as the working oracle at every step:

1. **Rename package** (`palworld_server_launcher/` → `logpose/`, update `pyproject.toml` name + entry point). Pure mechanical, biggest diff, do first so all later diffs are against new paths. Use `git mv` to preserve history.
2. **Parameterize helpers without GAMES dict yet** — `_create_service_file(port, players)` → `_create_service_file(spec, overrides)`, etc. Palworld flow unchanged. Proves the parameterization works before committing to dict shape.
3. **Introduce `GameSpec` + `GAMES` dict with Palworld only.** One-game oracle still passes.
4. **Restructure Typer to factory pattern.** CLI surface changes from `logpose <verb>` → `logpose palworld <verb>`. README updates here.
5. **Merge polkit rule** → `40-logpose.rules.template` with GAMES-loop expansion.
6. **Add ARK `GameSpec`** + `arkserver.service.template` + `_ark_parse`/`_ark_save`.
7. **E2E regression + new-game test** on fresh Debian VM.

**Why rename first:** Every later diff would otherwise be against the old package path.
**Why ARK last:** Scaffolding must be right before the second game exposes bugs.

## What Stays Unchanged (Minimum-Diff Checklist)

- `_run_command` signature
- `_repair_package_manager` (load-bearing per CLAUDE.md)
- `_install_steamcmd` signature (generic, not game-specific)
- `_fix_steam_sdk` body (becomes Palworld-only post-install hook)
- `palserver.service.template` byte-identical
- Palworld `OptionSettings` regex byte-identical, wrapped in `_palworld_parse` / `_palworld_save`
- Palworld systemd service name `palserver.service`
- Palworld settings section rename quirk
- Python 3.8+ floor
- Dependencies (`typer`, `rich`) — no new runtime deps
- `pyproject.toml` `[tool.setuptools.package-data]` glob `templates/*`

## Flags Passed to PITFALLS.md

1. `configparser.optionxform` defaults to lowercase — must override to `str` or ARK keys corrupt silently
2. Typer + closures in loops — use factory pattern; naked decorator-in-loop breaks
3. Palworld section-header rewrite must be preserved verbatim
4. Polkit rule file additivity — old `40-palserver.rules` coexists with new `40-logpose.rules`
5. `_run_command` is non-negotiable — no raw `subprocess.Popen` in new code
6. `str.format()` literal-brace escaping — every `{`/`}` in JS polkit template must be doubled
7. Typer option names with hyphens — `--admin-password` ↔ Python `admin_password`
