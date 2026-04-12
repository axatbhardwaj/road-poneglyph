# Feature Research

**Domain:** Linux dedicated game server launcher CLI (Palworld + ARK: Survival Evolved)
**Researched:** 2026-04-12
**Confidence:** HIGH for ARK launch parameters and `GameUserSettings.ini` keys (cross-verified against ARK wiki, ark-survival.net, arkmanager, LinuxGSM). MEDIUM for multi-game CLI UX patterns (verified against Typer docs and kubectl conventions; limited direct prior art for "game-as-subcommand" CLIs).

## Scope Notes (from PROJECT.md)

- Target: `logpose palworld <command>` / `logpose ark <command>`.
- ARK = **ASE only** (app id `376030`). ASA (Ascended) is explicitly out of scope — no native Linux binary.
- `edit-settings` for ARK covers **only `GameUserSettings.ini`**. `Game.ini` editing is out of scope for v0.2.0.
- No new runtime dependencies beyond Typer + Rich + stdlib `configparser`.
- No `BaseGame` class / no `core/` split — a `GAMES` dict + helper functions is the agreed shape.

## Feature Landscape

### Table Stakes (Users Expect These)

Features users will assume exist; their absence will make `logpose ark` feel broken.

| Feature | Why Expected | Complexity | Maps to (install flag / INI key) |
|---------|--------------|------------|----------------------------------|
| `logpose ark install` works on a fresh Debian/Ubuntu box | Parity with `logpose palworld install` | MEDIUM | New CLI command using existing `_install_steamcmd`, `_repair_package_manager`, `_fix_steam_sdk`; app id `376030`; binary `ShooterGame/Binaries/Linux/ShooterGameServer` |
| Map selection at install time | ARK has 12+ official maps; single-map hardcoding is unusable | LOW | `--map TheIsland` → baked into `ExecStart` as `ShooterGameServer <Map>?...` (map is a **positional URL arg**, not a `-flag`) |
| Game port, Query port, RCON port configurable at install | ARK needs 3 ports (vs Palworld's 1); all three clash with typical defaults | LOW | `--port 7777` (`?Port=`), `--query-port 27015` (`?QueryPort=`), `--rcon-port 27020` (`?RCONPort=` + `?RCONEnabled=True`) |
| `SessionName` at install time | Server is invisible in browser without a recognizable name | LOW | `--session-name "..."` → `?SessionName=` in launch args |
| `ServerAdminPassword` at install time | Without it you cannot run admin commands or use RCON | LOW | `--admin-password` → `?ServerAdminPassword=` |
| `ServerPassword` (optional) at install time | Private servers are common; many admins password-gate on day one | LOW | `--password` → `?ServerPassword=` (omit param entirely if empty — ARK treats empty-string differently from absent) |
| `MaxPlayers` at install time | ARK default is 70; many operators want 10 or 20 for friend groups | LOW | `--players 70` → `?MaxPlayers=` and also `MaxPlayers=` in `[ServerSettings]` |
| `-automanagedmods` flag in launch args | LinuxGSM and arkmanager default this on; required for Steam Workshop mods | LOW | Always-on by default in template; no flag needed (can be disabled later via edit path, post-v0.2.0) |
| `-crossplay` / EOS support awareness | Post-Wildcard patches, crossplay is how Epic users connect | LOW | Leave **off** by default (requires `-PublicIPForEpic=<ip>`); document as a post-install edit, do not take as install flag in v0.2.0 |
| `BattlEye` on by default | Official ARK servers use it; disabling should be explicit | LOW | Default: no flag (BE on). Expose `--no-battleye` install flag that adds `-NoBattlEye` |
| `start`, `stop`, `restart`, `status`, `enable`, `disable`, `update` work for `ark` identically to `palworld` | Users will type `logpose ark status` and expect systemd output | LOW | Refactor existing helpers to read service name from `GAMES[game_key]` |
| `logpose ark edit-settings` opens `GameUserSettings.ini` with same interactive UX as Palworld | Parity; users already learned the "pick setting by name → prompt new value" flow | MEDIUM | stdlib `configparser`; edit `[ServerSettings]` section; preserve file via `configparser.write()` |
| Graceful failure when server has not been launched once | `GameUserSettings.ini` does not exist until first launch; must not crash | LOW | Mirror existing Palworld pattern (`_create_settings_from_default`) — detect missing, prompt to start once, then retry |
| `logpose --help` / `logpose ark --help` discovery | Every multi-command CLI is expected to self-document | LOW | Typer emits this automatically; just ensure `help=` strings are populated per subcommand |
| Non-root enforcement | Existing tool already rejects `uid=0`; Steam refuses to run as root anyway | LOW | Reuse existing `Path.home() == Path("/root")` check in ARK install path |
| `steamclient.so` SDK fix applied for ARK too | ARK crashes on startup without the SDK redist symlink; same root cause as Palworld | LOW | Reuse existing `_fix_steam_sdk()` — ARK needs the same `~/.steam/sdk64/steamclient.so` |
| `logpose --version` | Ubiquitous CLI convention | LOW | Typer `--version` callback reading `importlib.metadata.version("logpose")` |

### Differentiators (Competitive Advantage vs arkmanager / LinuxGSM)

Where `logpose` can actually win: arkmanager and LinuxGSM are bash scripts with sprawling config files; `logpose` is Python + Typer + Rich with a single opinionated path.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Single-command install to a working autostart server (no config file to hand-edit) | arkmanager and LinuxGSM require editing `.cfg` before first launch; `logpose ark install --map ... --session-name ... --admin-password ... --start` produces a running server in one command | MEDIUM | Already the Palworld UX; extend to ARK |
| Passwordless systemd control via Polkit out of the box | arkmanager runs as a dedicated user with sudoers rules; LinuxGSM uses tmux sessions owned by the install user. Polkit is cleaner and survives logout | LOW | Reuse existing `_setup_polkit()` with a rule that covers both `palserver.service` **and** `arkserver.service` |
| Rich-formatted interactive edit UX | arkmanager edits INI by running `sed`; LinuxGSM has no built-in editor (opens nano). `logpose edit-settings` with a Rich table + prompt-by-name is a real DX win | LOW | Already shipped for Palworld; apply same pattern to ARK's `[ServerSettings]` |
| Unified CLI across games (same verbs, same flags where possible) | Operators managing two games today learn two separate tool vocabularies. `logpose palworld status` / `logpose ark status` is trivially transferable | LOW | Natural outcome of the `GAMES` dict + game-first Typer subcommand structure |
| Reliable apt/dpkg self-repair before install | `_repair_package_manager()` handles the broken-dpkg state common on fresh GCP/Oracle Cloud VMs — a real pain point; arkmanager's install script silently fails here | LOW | Already exists; keep it load-bearing (flagged in PROJECT.md Constraints) |
| Map aliases / validation at install time | Typo'd map names produce a silent server that starts and crashes 30s later with no log. Validating `--map` against the known list of 12 catches this at `install` time | LOW | Literal `typing.Literal["TheIsland","TheCenter",...]` or Typer `Enum` on the flag |
| `logpose ark install --start` follows through to a running server | Existing Palworld `--start` flag. For ARK, the user gets immediate feedback that ports are correctly bound and mods (if any) downloaded | LOW | Reuse existing `--start` pattern; post-install run `systemctl start arkserver` and tail status |

### Anti-Features (Commonly Requested, Explicitly Out of Scope for v0.2.0)

Features that look reasonable but violate the minimum-diff / Debian-only / out-of-scope constraints in PROJECT.md. Document clearly so future requests can be triaged against this list.

| Feature | Why Requested | Why Out of Scope | Alternative |
|---------|---------------|------------------|-------------|
| Mod management UI (`logpose ark mods add 12345`) | Steam Workshop mod IDs are ARK's single largest config surface; existing tools like `arkmanager` expose `installmod`/`removemod`/`updatemods` | Requires SteamCMD anonymous-user mod download logic, mod-state tracking, and a CLI sub-tree. Mods are editable via `ActiveMods=` in `GameUserSettings.ini` through existing `edit-settings` flow, and `-automanagedmods` handles updates automatically | Document: edit `ActiveMods=` in `GameUserSettings.ini` via `logpose ark edit-settings`; `-automanagedmods` is on by default so updates happen at start |
| Backup / restore (`logpose ark backup`) | `arkmanager backup` / LinuxGSM's backup command are popular; ARK's `.ark` save files are large and mod wipes can brick a save | Backup ≠ launcher scope. It's a file-copy job with retention policy, compression tradeoffs, and "restore into live server" safety questions that are a rabbit hole | Document `cron` + `tar` one-liner against `ShooterGame/Saved/SavedArks/` in README |
| Cluster management (`logpose ark cluster add server2`) | ARK clusters via `-ClusterId` and `-ClusterDirOverride` allow cross-map transfers; serious ARK communities run 4–10 maps in one cluster | Multi-instance management is a massive scope expansion (shared dirs, ID coordination, NFS, instance-naming). v0.2.0 assumes **one server per host per game** | Defer to v0.3+; in v0.2.0, operators add `-ClusterId=...` / `-ClusterDirOverride=...` manually to the service file if needed |
| Multi-instance / running two ARK servers on one box | LinuxGSM's core feature; ARK operators commonly run a cluster on one host across multiple ports | Requires instance-name parameter on every command, per-instance systemd units, per-instance port de-confliction — fundamentally changes the CLI shape. Explicitly deferred in PROJECT.md ("single service per game") | Two hosts, or run `logpose` for primary instance + hand-write a second systemd unit |
| Web dashboard / GUI | WindowsGSM, ARK Server Manager (Windows), AMP (CubeCoders) all have GUIs | logpose is a CLI, full stop. A web dashboard is a separate product | Use `logpose status` + `journalctl -u arkserver -f` for logs; refer to AMP if GUI is a hard requirement |
| `Game.ini` editing | `Game.ini` controls engram unlocks, per-dino spawn rates, harvest component overrides — power users tune it heavily | Out of scope per PROJECT.md. `Game.ini` has no canonical `[ServerSettings]` section; its keys are sparse, free-form overrides. Interactive editing is a harder UX problem than `[ServerSettings]` | Document: hand-edit `ShooterGame/Saved/Config/LinuxServer/Game.ini`; consider for v0.3+ |
| Auto-update scheduler (`logpose ark update --on-schedule daily`) | `arkmanager`'s `cron` subcommand; public servers want nightly restarts + updates | Scheduling is a systemd-timer concern, not a launcher concern. Keeps the tool's blast radius small | Document: `systemctl edit arkserver.service` + a systemd timer unit in README |
| RCON client (`logpose ark rcon "broadcast hello"`) | `arkmanager rconcmd` is heavily used for in-game admin (saveworld, broadcast, listplayers) | RCON client is a separate feature surface (TCP protocol, auth, interactive mode). v0.2.0 is install + settings + service control only | Document: use `mcrcon` or `rcon-cli` with `ServerAdminPassword` + RCON port |
| Arch Linux / RPM support | Palworld/ARK run fine on Arch; some users ask | Explicitly out of scope per PROJECT.md — `_repair_package_manager()` is apt/dpkg-specific | Deferred to future milestone |
| ARK: Survival Ascended (ASA, app id `2430930`) | Many users will assume "ARK" means "Ascended" in 2026 | Explicitly out of scope — ASA has no native Linux dedicated server binary; requires Proton/Wine hacks that violate the "just works on Debian" promise | Document clearly in `--help` and README: "ASE only; ASA unsupported" |

## Recommended ARK Install-Time Flag Set

Concrete, minimal, and cross-checked against arkmanager, LinuxGSM, and the ARK wiki launch syntax.

```
logpose ark install \
  [--map TheIsland]                         # default: TheIsland
  [--port 7777]                             # UDP game port
  [--query-port 27015]                      # UDP Steam query port (NOT 27020-27050, Steam reserves)
  [--rcon-port 27020]                       # TCP RCON port
  [--players 70]                            # ARK stock default
  [--session-name "ARK Server"]             # required-feeling; generated default if omitted
  [--admin-password <REQUIRED>]             # refuse to install without this
  [--password ""]                           # optional; empty → omit from launch line
  [--no-battleye]                           # flag; adds -NoBattlEye
  [--start]                                 # parity with Palworld
```

### Flag rationale & anti-gotchas

| Flag | Default | Notes |
|------|---------|-------|
| `--map` | `TheIsland` | Validate against `Literal["TheIsland","TheCenter","ScorchedEarth","Ragnarok","Aberration","Extinction","Valguero","CrystalIsles","Fjordur","LostIsland","Genesis","Gen2"]`. `Gen2` not `Genesis2` — ARK's internal map name is `Gen2`. |
| `--port` | `7777` | UDP. Also implicitly reserves `port+1` (peer port 7778) — do not document as separate flag; ARK binds it automatically. |
| `--query-port` | `27015` | **Critical pitfall**: Steam reserves 27020–27050 for Steam client; do not let users pick in that range. Validate at install time. |
| `--rcon-port` | `27020` | TCP, not UDP. Set `RCONEnabled=True` in INI alongside. |
| `--players` | `70` | ARK stock default. Appears in both launch-line `?MaxPlayers=` **and** `[ServerSettings]` `MaxPlayers=` — ARK reads both but launch-line wins. |
| `--session-name` | generated (e.g. `"logpose ARK Server"`) | If omitted, a default is inserted. Wrap in quotes in `ExecStart`. |
| `--admin-password` | **no default; required** | Without this, RCON auth and admin commands fail permanently. Refuse to install if missing and warn users to record it. |
| `--password` | `""` (none) | If empty, omit `?ServerPassword=` entirely from launch line — ARK treats `?ServerPassword=` (empty) as a zero-length password, which crashes some clients. |
| `--no-battleye` | False (BattlEye on) | Adds `-NoBattlEye` to launch. Default on matches official servers. |
| `--start` | False | Same semantics as Palworld. |

### Explicitly NOT in the v0.2.0 install flag set

| Not included | Rationale | Where it goes |
|--------------|-----------|---------------|
| `--mods "123,456"` | Mod management is an anti-feature for v0.2.0 | `ActiveMods=` via `edit-settings` |
| `--cluster-id` / `--cluster-dir` | Cluster mgmt is an anti-feature | Manual systemd-unit edit; document in README |
| `--crossplay` / `--public-ip` | Crossplay/EOS adds two launch flags and an IP detection question — not MVP | Manual systemd-unit edit |
| `--pve` | ARK's PvE vs PvP toggle lives in `ServerPVE=` in `[ServerSettings]` and `?ServerPVE=True` in launch line. Keep it out of install-time surface; let `edit-settings` handle it post-install | `edit-settings` |
| `--difficulty` / multipliers | All live in `GameUserSettings.ini`; no reason to surface them at install | `edit-settings` |

## Recommended Multi-Game CLI UX

Anchor on Typer's idiom (`add_typer(sub, name="<game>")`) and kubectl-style `<resource> <verb>` hierarchy, grounded against what actually works with Typer's auto-generated help.

### Command shape

```
logpose                        # root; lists game groups + shared commands
logpose --version
logpose palworld <verb>        # all existing commands, scoped
logpose ark <verb>             # new game, same verbs
```

### Game discovery

| Option | Recommendation |
|--------|----------------|
| Typer auto-generated `logpose --help` lists `palworld` and `ark` as subcommand groups | **Use this. Keep it.** This is discovery in Typer. Users running `logpose --help` will see both games listed — that's the discovery mechanism. |
| `logpose games` / `logpose list-games` explicit subcommand | **Skip for v0.2.0.** When there are 2 games, `--help` is sufficient. Adding a dedicated discovery command for 2 items is over-engineered and conflicts with the "minimum diff" constraint. Add it only when 4+ games exist. |
| Shell completion (`--install-completion`) | Typer ships this for free — it lists `palworld` and `ark` automatically. Mention in README; no code needed. |

### Shared vs game-specific flags

| Flag style | Convention |
|------------|------------|
| Every game's `install` has `--start` | Same flag name across games. Consistency > purity. |
| `--port` is game-specific | Palworld has 1 port; ARK has 3. Don't pretend they're the same. Each game's subcommand owns its install flag schema. |
| `--help` at every level works | `logpose --help`, `logpose ark --help`, `logpose ark install --help` all render — Typer default behavior; preserve it. |

### Per-verb behavior: same verbs, different wiring

| Verb | Palworld | ARK | Difference |
|------|----------|-----|------------|
| `install` | 2 flags (`--port`, `--players`) + `--start` | 8 flags (map/ports/names/passwords) + `--start` | Flag surface; service file template; app id |
| `start`/`stop`/`restart`/`status`/`enable`/`disable` | `systemctl <verb> palserver` | `systemctl <verb> arkserver` | Service name only (from `GAMES` dict) |
| `update` | `steamcmd +app_update 2394010 validate` | `steamcmd +app_update 376030 validate` | App id + install dir |
| `edit-settings` | Regex parser for `OptionSettings=(...)` | `configparser` for `[ServerSettings]` | Settings adapter (separate parse/save callable pair) |

### Help/UX polish worth doing in v0.2.0

- Populate `help=` in every `@app.command()` — Typer uses the docstring by default, but explicit `help=` strings render cleaner.
- Top-level `logpose` `--help` should have a one-line description of each game group (set via `app.add_typer(ark_app, name="ark", help="ARK: Survival Evolved (ASE) dedicated server")`).
- Refuse silently-bad inputs early: validate `--map` against the enum, validate ports are in 1024–65535 and not in Steam's 27020–27050 (except RCON which uses 27020 intentionally — RCON is TCP, Steam client reservation is UDP; these do not clash).
- Admin-password required: exit-with-hint if missing rather than installing a server with a blank admin password.

## `edit-settings` UX for ARK: Recommended Approach

ARK's `GameUserSettings.ini` `[ServerSettings]` block has ~80 knobs. The existing Palworld editor's "dump all + prompt by name" flow scales to ~30 keys and already works; the question is whether it scales to 80.

### Three UX options considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **(A) Dump-all + prompt-by-name** (Palworld parity) | Zero new UX code. Consistent with existing tool. Power users can discover every knob. | 80 keys is a lot of vertical scroll. Newcomers will not know which keys matter. | **Ship this in v0.2.0.** Matches minimum-diff. |
| **(B) Category-grouped menu** (arkmanager-style) | Easier for newcomers; groups like "Rates", "PvP/PvE", "Structures", "Dinos" | Requires hand-curating category metadata for every key. Couples `logpose` to knowing ARK's semantics rather than just parsing INI. | **Defer to v0.3+.** Violates minimum-diff. |
| **(C) Filter-by-name search** (`/term` to filter) | Scales to many settings; familiar (like `less`) | Requires non-trivial Rich + prompt loop refactor. Applies equally to Palworld; changes existing UX. | **Defer.** Nice polish, not MVP. |

### v0.2.0 implementation pattern for option (A)

- Read `ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini` with stdlib `configparser` (case-sensitive via `optionxform = str` override).
- Display `[ServerSettings]` keys in a Rich table (same visual style as Palworld).
- Reuse the existing `_interactive_edit_loop()` verbatim — it already prompts by key name, supports `save` / `quit`.
- On save: write back with `configparser.write()`; preserve other sections (`[SessionSettings]`, `[MultiHome]`, etc.) untouched.
- **Gotcha**: `configparser` drops comments on write. ARK's default `GameUserSettings.ini` has no comments, but test this; if any appear, note it as a known limitation.
- **Gotcha**: `configparser` lowercases keys by default. ARK keys are mixed case (`MaxPlayers`, `ServerPVE`). Must override `optionxform = str`.

### Most commonly edited `[ServerSettings]` keys (informs what users will look for)

Ground-truth from ark-survival.net and ARK wiki:

| Key | Default | Typical edits |
|-----|---------|---------------|
| `MaxPlayers` | 70 | Small private servers drop to 10–20 |
| `ServerPassword` | (empty) | Set or unset post-install |
| `ServerAdminPassword` | (set at install) | Rarely changed |
| `ServerPVE` | False | PvE servers flip to True |
| `DifficultyOffset` | 0.2 | Often 1.0 (max-level dinos) |
| `OverrideOfficialDifficulty` | 5.0 | Paired with DifficultyOffset=1.0 for "true max" |
| `XPMultiplier` | 1.0 | 2–10x on private/boosted servers |
| `TamingSpeedMultiplier` | 1.0 | 3–10x on boosted servers |
| `HarvestAmountMultiplier` | 1.0 | 2–5x on boosted servers |
| `DayCycleSpeedScale` / `DayTimeSpeedScale` / `NightTimeSpeedScale` | 1.0 | Extend day, shorten night |
| `DinoCountMultiplier` | 1.0 | Raise for denser worlds |
| `StructureDamageMultiplier` / `StructureResistanceMultiplier` | 1.0 | PvP tuning |
| `AllowThirdPersonPlayer` | False | Almost always flipped to True on private servers |
| `ServerCrosshair` | False | Often flipped True on PvE |
| `RCONEnabled` | False | Already set True by install |
| `RCONPort` | (set at install) | Rarely changed |

`ActiveMods` lives in `[ServerSettings]` but is a comma-separated workshop-id list — Option A's "prompt-for-new-value" flow handles it fine.

## Feature Dependencies

```
logpose ark install
    └── requires ── SteamCMD installed (shared with Palworld)
    └── requires ── _repair_package_manager (shared)
    └── requires ── _fix_steam_sdk (shared; ARK needs it too)
    └── requires ── GAMES dict populated with ARK entry
    └── requires ── arkserver.service template
    └── requires ── Polkit rule covering arkserver.service

logpose ark edit-settings
    └── requires ── ARK settings adapter (configparser-based, new)
    └── requires ── GameUserSettings.ini to exist
                        └── requires ── server launched at least once
                                              (OR copy a stub INI at install time)

logpose ark {start,stop,...}
    └── requires ── arkserver.service installed
    └── requires ── Polkit rule active

Game-first Typer subcommand structure
    └── enables ── per-game install flag schemas
    └── enables ── per-game help text
    └── enables ── future games without CLI shape breakage
```

### Key dependency note

- **`edit-settings` vs "server never launched"**: The existing Palworld flow handles this by copying `DefaultPalWorldSettings.ini` as a seed. ARK has no such default file shipped by SteamCMD — the server writes `GameUserSettings.ini` on first boot. Decision for v0.2.0: either (a) ship a stub `GameUserSettings.ini` seed inside `logpose`'s package (containing just `[ServerSettings]\nMaxPlayers=...\n...` using install-time flag values), or (b) require `logpose ark start` once before `logpose ark edit-settings` works. **Recommendation: option (a)** — at install time, write a minimal `GameUserSettings.ini` with the install-flag values. This makes `edit-settings` always work and also ensures install-time `--players`/`--password` take effect even before first launch.

## MVP Definition (v0.2.0)

### Launch With (v0.2.0)

Table stakes from the section above — non-negotiable:

- [ ] `logpose palworld <all existing verbs>` — identical behavior to v0.1.19
- [ ] `logpose ark install` with flags: `--map`, `--port`, `--query-port`, `--rcon-port`, `--players`, `--session-name`, `--admin-password`, `--password`, `--no-battleye`, `--start`
- [ ] `logpose ark {start,stop,restart,status,enable,disable,update}` mapped to `arkserver.service`
- [ ] `logpose ark edit-settings` with configparser-based adapter on `[ServerSettings]`
- [ ] Install-time write of minimal `GameUserSettings.ini` seed (so `edit-settings` works pre-first-launch)
- [ ] `-automanagedmods` on by default in ARK launch args
- [ ] Polkit rule covering both `palserver.service` and `arkserver.service`
- [ ] Typer `--help` at all levels populated; ARK `--map` validated against enum

### Add After Validation (v0.3.x)

- [ ] `Game.ini` editing — once `GameUserSettings.ini` flow is proven
- [ ] Mod management subcommand (`logpose ark mods add/remove/list`) — once user feedback demands it; requires mod-state tracking
- [ ] Category-grouped `edit-settings` UX — once 80-key flat list complaints arrive
- [ ] Filter-by-name search in `edit-settings` — apply uniformly to both games
- [ ] `logpose list-games` / shared discovery subcommand — when game count hits 3+
- [ ] `--crossplay` / `--public-ip` install flags for ARK EOS support

### Future Consideration (v1.0+)

- [ ] Cluster management (`-ClusterId`, `-ClusterDirOverride`)
- [ ] Multi-instance (two ARK servers, one host)
- [ ] RCON client (`logpose ark rcon ...`)
- [ ] Backup/restore
- [ ] Auto-update scheduler / cron integration
- [ ] Additional games (Valheim, Satisfactory, CS2) — explicitly deferred per PROJECT.md
- [ ] ARK: Survival Ascended — only if Wildcard ships a native Linux binary

## Feature Prioritization Matrix (v0.2.0 scope)

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `logpose ark install` with all table-stakes flags | HIGH | MEDIUM | P1 |
| ARK `edit-settings` via configparser | HIGH | LOW | P1 |
| ARK systemd + polkit parity with Palworld | HIGH | LOW | P1 |
| `-automanagedmods` default on | HIGH | LOW | P1 |
| Map enum validation | MEDIUM | LOW | P1 |
| `--no-battleye` flag | MEDIUM | LOW | P1 |
| Install-time seed `GameUserSettings.ini` | MEDIUM | LOW | P1 |
| `--crossplay` install flag | MEDIUM | LOW | P2 |
| `logpose list-games` discovery command | LOW | LOW | P3 |
| Mod management subcommand | HIGH | HIGH | P3 |
| Category-grouped `edit-settings` | MEDIUM | MEDIUM | P3 |
| RCON client | HIGH | HIGH | P3 |
| Cluster management | MEDIUM | HIGH | P3 (defer) |

## Competitor Feature Analysis

| Feature | arkmanager (ark-server-tools) | LinuxGSM | logpose (planned) |
|---------|-------------------------------|----------|-------------------|
| Install UX | Bash script; edit `/etc/arkmanager/instances/<name>.cfg` before start | `./arkserver install` interactive; generates `arkserver.cfg` | Single `logpose ark install --map ... --admin-password ... --start` one-shot |
| Config editing | Manual `sed`/editor on `.cfg`; maps to launch args | Edit `arkserver.cfg`; LGSM doesn't edit `GameUserSettings.ini` directly | Interactive Rich editor on `GameUserSettings.ini` |
| Service mgmt | Own `arkdaemon` concept; systemd unit optional | tmux sessions; optional systemd | systemd + polkit (no sudo, no tmux) |
| Mod mgmt | `arkmanager installmod <id>`, `updatemods` | `-automanagedmods` via config var | `-automanagedmods` on by default; edit `ActiveMods` via `edit-settings` |
| Backup | `arkmanager backup` | `./arkserver backup` | Explicit anti-feature for v0.2.0 |
| Cluster | Manual via instance configs | Not first-class | Explicit anti-feature for v0.2.0 |
| RCON | `arkmanager rconcmd` | `./arkserver console` | Explicit anti-feature for v0.2.0 |
| Multi-game | ARK-only | Supports 100+ games via game-specific scripts (`./arkserver`, `./pwserver`, etc.) | 2 games (Palworld + ARK) via `logpose <game> <verb>` |
| Distro support | Ubuntu/Debian/CentOS/Fedora | Many distros | Debian/Ubuntu only (v0.2.0) |
| Install target audience | Experienced Linux admins | Hobbyist to pro | Debian/Ubuntu hobbyist who wants "just works" |

**Where logpose wins:** opinionated single-path install, passwordless systemd, unified CLI across two popular games, Rich interactive settings editor, aggressive apt/dpkg self-repair. **Where it loses:** no backup, no cluster, no RCON, no multi-instance, single distro family. The v0.2.0 tradeoff (win on install UX, lose on feature breadth) is correct for the target audience — operators setting up their first Palworld/ARK server on a fresh VM — and aligns with the Core Value statement in PROJECT.md ("zero sudo prompts, working autostart-capable server on a fresh Debian/Ubuntu box").

## Sources

- [ARK Official Community Wiki — Dedicated server setup](https://ark.wiki.gg/wiki/Dedicated_server_setup) — HIGH confidence (official wiki); default ports 7777/27015/27020, launch syntax with `?` URL args, map names
- [ARK Official Community Wiki — Server configuration](https://ark.wiki.gg/wiki/Server_configuration) — HIGH confidence; `[ServerSettings]` key reference, `-ClusterId` / `-ClusterDirOverride` semantics
- [ARK Fandom Wiki — Dedicated server setup](https://ark.fandom.com/wiki/Dedicated_server_setup) — MEDIUM; corroborates map list and launch syntax
- [ark-survival.net — Server Command Line Arguments & GameUserSettings.ini](https://www.ark-survival.net/server-command-line-arguments-gameusersettings-ini-configuration/) — MEDIUM; common-edit `[ServerSettings]` defaults, `-NoBattlEye`, `-automanagedmods`, `-crossplay` flags
- [arkmanager / ark-server-tools GitHub](https://github.com/arkmanager/ark-server-tools) and [Server Options wiki](https://github.com/arkmanager/ark-server-tools/wiki/Server-Options) — HIGH; port var names (`ark_Port`, `ark_QueryPort`, `ark_RCONPort`), `-automanagedmods` as default, command verbs (`backup`, `update`, `rconcmd`, `saveworld`, `cron`)
- [LinuxGSM ARK docs](https://docs.linuxgsm.com/game-servers/ark-survival-evolved) — MEDIUM; default RAM per map, default session name pattern, `-MultiHome`/`-AutoManagedMods`/`-Crossplay` in default cmdline
- [LinuxGSM basic-usage](https://docs.linuxgsm.com/other/basic-usage) — MEDIUM; short/long verb convention (`st`/`start`, `sp`/`stop`), per-instance scripts pattern
- [Typer — Nested SubCommands](https://typer.tiangolo.com/tutorial/subcommands/nested-subcommands/), [Add Typer](https://typer.tiangolo.com/tutorial/subcommands/add-typer/), [SubCommand Name and Help](https://typer.tiangolo.com/tutorial/subcommands/name-and-help/) — HIGH; `add_typer(name=..., help=...)` pattern, auto-completion, auto-help
- [ARK server cluster discussions (Steam, PlayServers)](https://playservers.medium.com/ark-survival-evolved-server-cluster-guide-1dbe0802b019) — MEDIUM; cluster ID and ClusterDirOverride usage (used to justify *excluding* from v0.2.0)
- [Steam community — Query port 27020-27050 reserved by Steam client](https://steamcommunity.com/app/346110/discussions/0/358417008719184407/) — LOW-MEDIUM; corroborates the QueryPort validation rule

---
*Feature research for: multi-game dedicated server launcher CLI (Palworld + ARK: Survival Evolved) on Debian/Ubuntu*
*Researched: 2026-04-12*
