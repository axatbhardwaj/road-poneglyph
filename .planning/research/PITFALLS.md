# Pitfalls Research

**Domain:** Multi-game dedicated server launcher (Linux / SteamCMD / systemd / Polkit), generalizing `palworld-server-launcher` v0.1.19 into `logpose` with ARK: Survival Evolved added as a second game.
**Researched:** 2026-04-12
**Confidence:** HIGH for ARK Linux dependencies, steamclient.so paths, LimitNOFILE, SessionName/RCON semantics, configparser edge cases, polkit multi-unit patterns. MEDIUM for some SIGTERM propagation specifics (ARK's Linux binary does handle SIGTERM correctly; the historical "save rollback on stop" issue is primarily a Docker/shell-wrapper problem, not a raw systemd one). LOW for the specific "25-char SessionName truncation" claim — not substantiated by official or community sources; see Pitfall 8.

---

## Critical Pitfalls

### Pitfall 1: ARK Linux dependency package names drift between Debian releases

**What goes wrong:**
`_install_steamcmd()` installs `steamcmd` fine on Debian 12 / Ubuntu 22.04 / 24.04, but ARK's `ShooterGameServer` binary silently fails to launch (or exits code 127 with "error while loading shared libraries: libc.so.6: cannot open shared object file") on a fresh VM because ARK needs extra 32-bit libs that Palworld does not. The systemd unit logs show startup success for a split second, then repeated restart loops.

**Why it happens:**
ARK is a 64-bit binary but it pulls in the `steamclient.so` shim which transitively needs 32-bit glue. On Debian 11 / Ubuntu 20.04 the package was `lib32gcc1`; Debian 12 / Ubuntu 22.04+ renamed it to `lib32gcc-s1`. Blog posts and Steam guides are full of stale `apt install lib32gcc1` commands that error out with "Unable to locate package" on modern releases. Palworld didn't surface this because Palworld's UE5 binary is pure 64-bit with no 32-bit Steam shim dependency — it only needs `steamcmd` itself.

**How to avoid:**
- In a new `_install_game_dependencies(game_key)` helper, install ARK's extras explicitly with fallback: try `lib32gcc-s1` first, fall back to `lib32gcc1` if the first returns a non-zero on `apt-cache show`. Package set confirmed for Debian 12 / Ubuntu 22.04 / 24.04: `lib32gcc-s1 libc6-i386 libncurses5 libncursesw5` (and `libtinfo5:i386` on 22.04+; dropped from 24.04 but Steam guide still lists it — gate on `apt-cache search`).
- Treat this list as game-specific, not launcher-wide — Palworld should NOT install 32-bit libs (it doesn't need them and adding `dpkg --add-architecture i386` has already happened in `_install_steamcmd()`, but pulling `libc6-i386` onto Palworld-only boxes is pointless bloat and can create apt conflicts on tightened images).
- Add this to the `GAMES['ark']` dict: `apt_packages: ["lib32gcc-s1", "libc6-i386", "libncurses5", "libncursesw5"]`. Palworld's entry has an empty list.
- Run `apt-cache show <pkg>` before `apt-get install` — skip unknowns rather than failing the whole install.

**Warning signs:**
- `journalctl -u arkserver.service` shows `error while loading shared libraries` or `cannot open shared object file`
- Server status flips between `activating (auto-restart)` and `failed` in a loop
- `ldd ShooterGameServer` shows `=> not found` entries

**Phase to address:**
Phase "ARK install flow" — whichever phase wires up the ARK SteamCMD install. Must land before the first ARK `install` is attempted end-to-end on a fresh VM.

---

### Pitfall 2: `steamclient.so` wrong path for ARK (sdk32 vs sdk64)

**What goes wrong:**
The existing `_fix_steam_sdk()` copies `steamclient.so` from `Steamworks SDK Redist/linux64/steamclient.so` to `~/.steam/sdk64/`. For ARK, this path is insufficient: ARK also looks in `~/.steam/sdk32/steamclient.so` (32-bit shim) and in `<serverfiles>/Engine/Binaries/ThirdParty/SteamCMD/Linux/steamclient.so`. The server starts, but Steam's auth callbacks fail silently — the server never appears in the Unofficial server browser, no players can connect, and logs show `S_API FAIL SteamAPI_Init failed` or nothing relevant at all.

**Why it happens:**
ARK predates Palworld's cleaner UE5 Steam integration. It carries legacy 32-bit Steam glue even on a 64-bit build, and looks up `steamclient.so` in multiple fallback locations. Guides and LinuxGSM both explicitly document copying to BOTH `sdk32` and `sdk64`, plus symlinking the steamcmd dir into the ARK server's `Engine/Binaries/ThirdParty/SteamCMD/Linux`.

**How to avoid:**
- Generalize `_fix_steam_sdk()` into `_fix_steam_sdk(game_key)`. For Palworld, keep current behavior (sdk64 only). For ARK, additionally:
  - Copy (or symlink) `~/.steam/steam/linux32/steamclient.so` to `~/.steam/sdk32/steamclient.so`
  - Symlink the steamcmd data dir into the ARK serverfiles path `ShooterGame/Binaries/Linux/../../../Engine/Binaries/ThirdParty/SteamCMD/Linux`
- Put the sdk paths in `GAMES['ark']['steam_sdk_paths']` as a list of `(src, dst)` tuples so the helper is data-driven.
- Exact paths verified against ark.wiki.gg/Dedicated_server_setup and LinuxGSM arkserver docs.

**Warning signs:**
- ARK process runs (systemd is `active (running)`) but server never appears in Steam's Unofficial browser after 2+ minutes
- `grep -i steam <ARK log>` shows `SteamAPI` or `steamclient` warnings
- Players report "session not found" or "connection timed out" despite open UDP 7777/27015

**Phase to address:**
Same phase as Pitfall 1 (ARK install flow). The sdk fix runs right after SteamCMD completes, same as the Palworld flow does today.

---

### Pitfall 3: ARK silently crashes without `LimitNOFILE` raised

**What goes wrong:**
ARK's `ShooterGameServer` needs far more open file descriptors than the default systemd limit (1024 soft / 524288 hard on modern Debian). Without `LimitNOFILE=100000` (or higher), the server appears to start — high CPU, growing RSS — but never finishes loading. RAM plateaus well below the 5.5-6 GB it needs, the server never advertises in the browser, and the process eventually restarts or hangs indefinitely. Operators are left debugging network config when the real issue is ulimit.

**Why it happens:**
ARK loads tens of thousands of PAK/uasset files during world init. On a Linux VM the default soft limit (commonly 1024) is shredded before level loading finishes. systemd services do NOT inherit `/etc/security/limits.conf` entries — `LimitNOFILE=` on the unit is the only correct knob for services. Palworld didn't hit this because its world-loading file count is roughly an order of magnitude lower.

**How to avoid:**
- Add `LimitNOFILE=100000` to the ARK systemd service template (not Palworld's — keep Palworld's template untouched to preserve behavioral compatibility per PROJECT.md constraint).
- Represent as `GAMES['ark']['systemd_extra'] = {"LimitNOFILE": "100000"}`; have `_create_service_file()` render a block only when non-empty, so Palworld's rendered output is byte-identical to v0.1.19.
- Also add `TasksMax=infinity` defensively (ARK spawns many threads; modern systemd defaults to 15% of kernel pid_max which is fine, but there are historical reports of hitting it on small VMs).
- Do NOT use `LimitNOFILE=infinity` on systemd versions older than 240 — on older stacks this resolves to 4096, not unlimited. The project supports "Debian/Ubuntu only" (Debian 11+/Ubuntu 20.04+) so systemd is >= 245; `infinity` is safe but a numeric `100000` is clearer for ops.

**Warning signs:**
- `systemctl status arkserver` shows `active (running)` but `ss -tuln | grep 7777` shows nothing even 5+ minutes later
- `cat /proc/$(pgrep ShooterGame)/limits | grep "Max open files"` shows `1024 524288`
- `lsof -p <pid> | wc -l` climbing toward 1000 then the server stalls

**Phase to address:**
Phase "ARK systemd service template" — when creating `arkserver.service.template`. Verify with `cat /proc/<pid>/limits` after first start.

---

### Pitfall 4: Hard-kill during shutdown → ARK save-file rollback

**What goes wrong:**
User runs `logpose ark stop` or `systemctl stop arkserver`. systemd sends SIGTERM, waits `TimeoutStopSec=` (default 90s), then SIGKILLs. ARK's Linux binary does handle SIGTERM as a graceful shutdown if the signal reaches it directly, but (a) if the ExecStart uses a shell wrapper that does not forward signals, the kill falls through to SIGKILL and (b) ARK's "save on shutdown" on large worlds can take 30-120 seconds. Result: the last N minutes of world state are rolled back; on bad timing, the save file can be left partially written and corrupt.

**Why it happens:**
ARK's autosave interval is typically 15 minutes. When an admin stops the server "to apply a change," everyone's progress since the last autosave is at risk. The Palworld launcher never had to think about this because Palworld autosaves aggressively and the UE5 binary exits cleanly on SIGTERM within a few seconds.

**How to avoid:**
- `ExecStart` must exec the ARK binary directly (no shell wrapper swallowing signals). Specifically: use `ExecStart=/absolute/path/ShooterGameServer <args>` rather than `ExecStart=/bin/bash -c "..."`. If a wrapper script is needed (e.g. to set env or cd), the script must `exec "$@"` as its last line.
- Set `TimeoutStopSec=300` on the ARK unit — 5 minutes of headroom for save completion. Default 90s is not enough for a large world with many tribes.
- Set `KillSignal=SIGINT` on the ARK unit. ARK's Linux binary (and Wildcard's docs) treat Ctrl-C (SIGINT) as the canonical "save and exit" signal; SIGTERM works on recent builds but SIGINT is the documented-safe choice.
- Do NOT add a custom `ExecStop=` that runs RCON `DoExit` unless RCON is confirmed up — a failing ExecStop turns `systemctl stop` into a hard-kill regardless. If RCON pre-save is desired, do it from the CLI wrapper (`logpose ark stop` runs RCON `saveworld` then `systemctl stop`) with timeouts, never from the unit file.
- Document in README that `saveworld` via RCON before stop is the belt-and-suspenders move. Optional: offer `logpose ark stop --save` flag that does RCON saveworld first.

**Warning signs:**
- Players reporting "lost X minutes of progress" after every restart
- `.ark` save file mtime equals last autosave time, not "a few seconds before stop"
- `systemctl stop arkserver` returns quickly (< 10s) on a populated world — save did not run

**Phase to address:**
Phase "ARK systemd service template". KillSignal + TimeoutStopSec are template values; the exec-style ExecStart is a template authoring discipline.

---

### Pitfall 5: `configparser` trips on ARK's `GameUserSettings.ini` in three distinct ways

**What goes wrong:**
You happily write `cfg = configparser.ConfigParser(); cfg.read(path)` on ARK's `GameUserSettings.ini` and hit one of three blow-ups:

1. `InterpolationSyntaxError` on any value containing a literal `%` (common in `MessageOfTheDay` or server descriptions: "50% XP boost weekends!"). Stdlib `ConfigParser` treats `%` as interpolation syntax.
2. `DuplicateOptionError` when `ServerSettings` has duplicated keys. This genuinely happens in the wild — ARK itself writes out duplicates in some cases, and mods/operators layering edits add more. The stdlib default `strict=True` refuses the file entirely.
3. Case-folded keys: `configparser` lower-cases option names via `optionxform()`. ARK cares about case: `ServerPassword` is not `serverpassword`. If you read, mutate, and write back, every key in the output file is lowercased, and the server silently reverts those settings to defaults (the game matches by exact case).

**Why it happens:**
`configparser` was designed for Python config files, not game engine configs. Its three defaults — interpolation on, strict mode on, case-folding on — are all wrong for Unreal Engine `.ini` files. Empty `ServerPassword=` (no value) with `strict=True` and `allow_no_value=False` is also a potential issue (ARK's default file has `ServerPassword=` blank).

**How to avoid:**
All three fixes are set at constructor time. Use this exact incantation for ARK:

```python
import configparser

def _make_ark_parser():
    cfg = configparser.RawConfigParser(
        strict=False,          # tolerate duplicate keys (last wins)
        allow_no_value=True,   # accept ServerPassword= blank
        interpolation=None,    # disable %-interpolation (protects MessageOfTheDay)
        delimiters=("=",),     # ARK never uses colons as separators
        comment_prefixes=(";", "#"),
    )
    cfg.optionxform = str      # preserve case — CRITICAL, use = str, not lambda
    return cfg
```

Notes:
- `RawConfigParser` is the safer base class (no interpolation at all); passing `interpolation=None` to regular `ConfigParser` works too but RawConfigParser signals intent.
- `optionxform = str` must be set as an attribute assignment, not by subclassing alone. The stdlib's subclass-and-override trick has bitten people (see cpython docs).
- ARK section names like `[/Script/Engine.GameSession]` and `[/Script/ShooterGame.ShooterGameMode]` are valid configparser section headers (slashes and dots are fine; only `]` inside the name breaks it).
- When writing back, `cfg.write(f, space_around_delimiters=False)` — ARK files use `Key=Value` with no spaces; the default `Key = Value` works at runtime but diffs dirty and some third-party tools are picky.
- Preserve trailing blank lines and top-of-file comments by reading the file through `cfg.read_file()` on an already-opened handle rather than `cfg.read(path)`, and preserving any pre-section preamble manually if present. (ARK's default file is clean but operators add headers.)

**Warning signs:**
- `ValueError: invalid interpolation syntax in ...` or `InterpolationSyntaxError` on first read
- `DuplicateOptionError: ... in 'ServerSettings'`
- After running `edit-settings`, ARK boots with default password, or `grep -i ServerPassword` in the ini shows `serverpassword=` (lowercase)

**Phase to address:**
Phase "ARK settings adapter". The adapter helper is the place; not the CLI. The parser factory should live in a single function referenced from `GAMES['ark']['settings_adapter']`.

---

### Pitfall 6: Refactor regression — `GAMES` dict values leak between Palworld and ARK code paths

**What goes wrong:**
The refactor introduces `GAMES = {"palworld": {...}, "ark": {...}}` and switches helpers to read from it. Common ways this silently breaks Palworld behavior:

1. Default-argument trap. Someone writes `def _fix_steam_sdk(game: str = "palworld"):` as a compat shim. Later, `install()` for ARK forgets to pass `game="ark"` through one call, and the ARK install calls `_fix_steam_sdk()` with Palworld defaults — the ARK install "succeeds" but Steam SDK is mis-configured. Silent.
2. Module-level constants still reference Palworld. The existing `STEAM_DIR`, `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` are module globals at top of `main.py`. If you "parameterize" helpers but leave one helper still reading `PAL_SETTINGS_PATH` directly, ARK commands clobber Palworld's ini on a machine that has both installed.
3. Typer command decorators at import time. `@app.command()` runs at import. If a helper formerly at module scope (like `_parse_settings()` which reads `PAL_SETTINGS_PATH` eagerly via `.read_text()`) is kept but wrapped, an `ImportError` on a box that has ARK but not Palworld can break all ARK commands too.
4. Mutable dict shared across invocations. `GAMES["ark"]["launch_args"]` if built as a mutable list and appended to inside a helper, accumulates across multi-command CLI invocations in tests. Test suites (even ad-hoc) hit this fast.
5. `str.format()` placeholder drift. Palworld template uses `{user}`, `{port}`, `{players}`, `{exec_start_path}`, `{working_directory}`. ARK adds `{query_port}`, `{rcon_port}`, `{map}`, `{session_name}`, `{admin_password}`. If the new ARK template accidentally uses a placeholder name that also appears in Palworld's template, a shared `format()` call with a union dict silently succeeds but produces wrong output. Worse: a typo like `{port}` in ARK's template when ARK has `{game_port}` — silent mis-render of Palworld's port for the ARK service.
6. Polkit rule filename collision. `40-palserver.rules` gets overwritten when the ARK install ships a rule file with the same numeric prefix. Or the ARK install deletes/overwrites the Palworld rule because the code uses one global path.

**How to avoid:**
- Kill all module-level Palworld globals. `STEAM_DIR`, `PAL_SERVER_DIR`, `PAL_SETTINGS_PATH`, `DEFAULT_PAL_SETTINGS_PATH` move into `GAMES["palworld"]` values (computed at import still, but dict-scoped). No top-level name starts with `PAL_`.
- No default-arg game keys. Every game-aware helper takes `game: str` as a positional required arg. `_fix_steam_sdk(game)`, `_create_service_file(game, port, players)`, `_install_game(game)`. This forces call sites to be explicit; the type checker / grep catches missed sites.
- One-shot comparison test. Before ANY `GAMES` refactor lands, snapshot the current rendered `palserver.service` and `palserver.rules` for a known fixture (user=`foo`, port=`8211`, players=`32`). After refactor, re-render with `game="palworld"` and `diff` byte-for-byte. Zero bytes of difference, or the commit does not merge. This single check catches 80% of regressions.
- Namespace polkit rule files by game. `40-palserver.rules` stays exactly where it is; ARK gets `40-arkserver.rules` (separate file). Two files beats one merged rule with an array — see Pitfall 10.
- Namespace launch arg templates by game key in `GAMES`, and build the launch arg string with a pure function that takes only `GAMES[game]` + CLI inputs. Never mutate `GAMES[game]` in-place.
- Explicit placeholder-name test. For each game, assert `set(template.placeholders) == set(format_dict.keys())` before calling `.format()`. Use `string.Formatter().parse()` to extract placeholder names; if not equal, abort with a clear error. This catches template-drift typos before they hit disk.

**Warning signs:**
- `diff` of rendered `palserver.service` before/after refactor is non-empty
- Running `logpose palworld install` on a machine that also has `logpose ark install` leaves the wrong ServerAdminPassword in Palworld's settings
- `grep -rn 'PAL_' palworld_server_launcher/main.py` returns matches after the refactor is "done"
- `logpose ark start` on a Palworld-only box errors out with a `PAL_SETTINGS_PATH` NameError instead of a clean "ark not installed"

**Phase to address:**
Phase "Refactor to GAMES dict". This is where the discipline lives. The byte-diff check is the single most important artifact — make it a script (`scripts/verify_palworld_compat.sh`) that the phase exit-criteria demands.

---

### Pitfall 7: Typer nested subcommand help and exit-code footguns

**What goes wrong:**
After converting to `logpose <game> <command>` with `add_typer`, symptoms include:
- `logpose --help` shows `palworld` and `ark` as commands but with no descriptions, or with auto-generated ones that are confusing.
- `logpose palworld --help` shows the wrong command list or "No such command" because the sub-Typer was not given a name.
- A global `--verbose` flag at the top-level does not propagate into subcommands — every subcommand has to re-declare it.
- `logpose palworld install` exits `0` even when `_install_palworld()` raised and `sys.exit(1)` was called — because a callback higher up swallowed the exception with a broad `except:` or because Typer's exception handling converted the `SystemExit(1)` into `typer.Exit(code=0)` via an errant `standalone_mode` tweak.
- `logpose` with no args prints usage but exits `0` (should be `2` per Unix convention for "missing required arg").

**Why it happens:**
- `app.add_typer(palworld_app, name="palworld")` with no `help=` gives a bare help line. Always pass `help="..."` on both `add_typer()` AND on the sub-Typer constructor.
- Global options belong in the callback (`@app.callback()`), not on individual commands. Typer's docs explicitly call this out — but the pattern is non-obvious to someone porting a flat `@app.command()` layout.
- Typer wraps Click; Click's `standalone_mode=True` (default) calls `sys.exit(...)` on exceptions. If any code path catches `typer.Exit` or `click.exceptions.*` broadly, exit codes get clobbered.
- Typer's default `no_args_is_help=False` on sub-apps means an invocation like `logpose palworld` (no command) falls through to Click and prints help with exit 0 — which violates the "missing required arg" expectation.

**How to avoid:**
- Construct each sub-app with explicit help text and `no_args_is_help=True`:
  ```python
  palworld_app = typer.Typer(help="Manage the Palworld dedicated server.", no_args_is_help=True)
  ark_app = typer.Typer(help="Manage the ARK: Survival Evolved dedicated server.", no_args_is_help=True)
  app = typer.Typer(help="logpose — multi-game dedicated server launcher.", no_args_is_help=True)
  app.add_typer(palworld_app, name="palworld", help="Manage the Palworld dedicated server.")
  app.add_typer(ark_app, name="ark", help="Manage the ARK: Survival Evolved dedicated server.")
  ```
- Any global flag (like `--verbose` or `--dry-run`) goes in `@app.callback()`, stored on `ctx.obj`:
  ```python
  @app.callback()
  def main(ctx: typer.Context, verbose: bool = typer.Option(False, "--verbose", "-v")):
      ctx.obj = {"verbose": verbose}
  ```
  Subcommands retrieve via `ctx: typer.Context` parameter. Do NOT re-declare `--verbose` on sub-commands.
- Never `except Exception:` around a `typer.Exit` or `SystemExit`. Re-raise both.
- For each command, prefer `raise typer.Exit(code=1)` over `sys.exit(1)` — the existing `main.py` calls `sys.exit(1)` directly; migrate to `typer.Exit` during the refactor so exit codes survive Typer's test harness.
- Manual CLI smoke test as phase exit criteria: run `logpose`, `logpose --help`, `logpose palworld`, `logpose palworld --help`, `logpose palworld install --help`, `logpose ark`, `logpose ark install --help`, and `logpose bogus` — verify exit codes and help trees are all sane.

**Warning signs:**
- `logpose` alone exits 0 with a usage dump (should exit 2)
- `logpose palworld --help` shows no "Commands:" section or shows wrong commands
- Sub-command docstrings appear identical (autogenerated from command function name) — means `help=` was never set
- CI scripts that chain `logpose ark install && logpose ark start` proceed on failure

**Phase to address:**
Phase "Convert Typer CLI to game-first nested subcommands". Exit-code and help-tree smoke tests go in that phase's exit criteria.

---

### Pitfall 8: ARK command-line SessionName quoting and special-character mangling

**What goes wrong:**
Operator runs `logpose ark install --session-name "My Cool Server [PvE]"`. The CLI dutifully passes this as a launch arg. ARK parses the launch string and shows `"My"` in the server browser — everything after the first space is dropped. Or the bracket character breaks the parser and the session name becomes `Cool Server`. Either way: the `GameUserSettings.ini` value was set correctly, but the command-line override passed via `?SessionName=...` clobbers it at runtime with a mangled value.

Separately, ARK uses `?` as its arg separator (Unreal Engine URL syntax), not `--flag`. So `?SessionName=My Cool Server?QueryPort=27015` parses as:
- `SessionName=My Cool Server` (first `?`-separated chunk) — but the space breaks shell quoting and/or ARK's internal tokenizer
- `QueryPort=27015`

**Why it happens:**
ARK's ShooterGameServer takes `<map>?option=value?option=value`. Values with spaces must be quoted at the shell level AND the launcher must decide whether to put the SessionName on the command line or ONLY in the INI. Community consensus is clear: put SessionName with spaces ONLY in `GameUserSettings.ini` under `[SessionSettings]`, never on the command line. arkmanager issues #44 and #15 both document this.

Regarding a "25-character truncation": I could not verify this claim in any authoritative source. The observed truncation in the wild is caused by spaces when passed via command line, not by character count. There is a known "very long names truncate in the server browser UI" issue, with community guidance of "keep under ~60 chars," but no confirmed hard 25-char limit. Confidence: LOW. Do not enforce a 25-char limit in the CLI; enforce a generous 63-char limit (a common UDP-advertised string limit) and warn above that.

**How to avoid:**
- Install flow writes `SessionName` to `[SessionSettings]` in `GameUserSettings.ini` only. Never add `?SessionName=...` to the launch command.
- Validate in CLI: reject `\r`, `\n`, `?`, `[`, `]`, `"` in session name (these break INI parsing and/or URL-style launch arg parsing even for values the launcher does not pass to the command line, because operators sometimes re-run with `--session-name` intending to update).
- Allow spaces freely; they're safe once they're in the INI.
- Warn (don't reject) if length > 63 chars.
- The map name, ports, and `listen` DO go on the command line — those are simple tokens.

**Warning signs:**
- Steam server browser shows truncated name (first word only)
- `grep SessionName GameUserSettings.ini` shows full name, but browser shows partial — it's a command-line override bug
- Bracket or punctuation chars in operator-supplied name appear dropped in-game

**Phase to address:**
Phase "ARK install flow" — specifically the install command's CLI validation and the templated launch command construction.

---

### Pitfall 9: RCON silently off because only the launch arg — or only the INI — was set

**What goes wrong:**
Operator thinks RCON is enabled because `GameUserSettings.ini` has `RCONEnabled=True` and `RCONPort=32330`. They try to connect and the port is closed or refuses. Alternatively, they have `?RCONEnabled=True?RCONPort=32330` on the command line but no `ServerAdminPassword=` in the INI — RCON binds but rejects all auth.

**Why it happens:**
ARK needs three things aligned:
1. `RCONEnabled=True` in `[ServerSettings]` of `GameUserSettings.ini` AND `?RCONEnabled=True` on the command line (community reports differ on whether one is enough; the safe move is both).
2. `RCONPort=<port>` matching on both.
3. `ServerAdminPassword=<password>` set in `[ServerSettings]` — this is the RCON password, not a separate RCON-only password.

Without all three, the server starts fine, but RCON is either off or uselessly unauthable.

**How to avoid:**
- In ARK's install flow, always write `RCONEnabled=True`, `RCONPort=32330` (default), and `ServerAdminPassword=<generated>` into `[ServerSettings]` unless the operator passes `--no-rcon`.
- Also include `?RCONEnabled=True?RCONPort=<port>` in the launch args template.
- Generate an admin password via `secrets.token_urlsafe(16)` if not supplied. Log it ONCE to the console with a clear "save this now" banner. Do not persist it anywhere logpose reads back — the INI is the source of truth.
- `logpose ark status` output should include "RCON: enabled on port 32330" or "RCON: disabled" by reading the INI.
- Open UDP 7777+27015 and TCP (or UDP per RCON spec) 32330 — document this in install output. Do NOT auto-open firewall; log explicit instructions. (See Pitfall 12 for firewall discipline.)

**Warning signs:**
- `ss -tuln | grep 32330` empty despite `RCONEnabled=True` in INI
- RCON client connects but every command returns "auth failed" — `ServerAdminPassword` is empty
- Operator's password contains characters that `configparser` interpolates — see Pitfall 5; ALL values with `%` must be escaped as `%%` OR the parser must be built with `interpolation=None`

**Phase to address:**
Phase "ARK install flow" for defaulting. Phase "ARK settings adapter" for INI round-trip. Phase "ARK status/CLI wiring" for the status readback.

---

### Pitfall 10: Polkit rule for two services — merge vs split, and the "works for game A, silently prompts sudo for game B" trap

**What goes wrong:**
`40-palserver.rules` currently whitelists only `palserver.service`. After adding ARK, if the polkit rule is not updated, `systemctl start arkserver` (or `stop`, `restart`) silently demands sudo — user sees a password prompt or (when run via CLI subprocess) gets a non-interactive failure. Alternately, if someone writes a single merged rule with bad JS logic (e.g. uses `||` where `&&` was intended, or forgets to return YES in one of the two branches), one of the services breaks silently.

If the existing `40-palserver.rules` is edited to cover both, and later an operator uninstalls ARK, the rule still references `arkserver.service` (harmless but messy). If it's a separate `40-arkserver.rules`, uninstall can clean it up cleanly.

**Why it happens:**
Polkit rule files are JavaScript. The lookup of `action.lookup("unit")` returns a string like `"palserver.service"`. Comparing to a single literal is easy; covering two units requires either `indexOf` on an array or an explicit OR. The JS syntax is obscure to Python devs. Also, the existing template uses `{{ }}` for literal JS braces under Python `str.format()` — changing the rule shape without preserving those escapes breaks the template.

**How to avoid:**
Recommendation: TWO separate rule files, one per game. Rationale:
- Clean install/uninstall semantics (ARK install creates `40-arkserver.rules`; uninstall removes it — Palworld's rule is untouched).
- Zero risk of breaking Palworld's existing behavior (file stays identical to v0.1.19).
- Each rule file is trivially auditable (matches one unit).
- Polkit processes all rule files in `/etc/polkit-1/rules.d/` in sorted order until one returns a value — two separate YES-returning rules compose fine.
- Cost: a few extra lines of template authoring. The "clean sweep" benefit dwarfs this.

Concretely:
- Keep `palserver.rules.template` as-is. Filename at install: `40-palserver.rules`.
- Add `arkserver.rules.template` — identical shape, but matches `"arkserver.service"`. Filename at install: `40-arkserver.rules`.
- Both go under `GAMES[game]['polkit_rule_template']` and `GAMES[game]['polkit_rule_filename']`.
- `_setup_polkit(game)` writes only the one file for the installing game — installing ARK never touches Palworld's rule and vice versa.

Alternative (rejected): single merged rule. Would use a JS array with `indexOf()` to check `action.lookup("unit")` against both service names. This works, but:
- Couples Palworld and ARK install state (installing ARK rewrites Palworld's rule file).
- Uninstall of one game requires regenerating the rule to remove the other.
- More surface area for a template typo to break both games at once.

**Warning signs:**
- `logpose ark start` on a fresh install prompts for sudo or times out non-interactively
- `pkcheck --action-id org.freedesktop.systemd1.manage-units --detail unit arkserver.service --process $$` returns "not authorized"
- `journalctl /usr/libexec/polkitd -f` during a failing `systemctl start` shows "No JS rule authorized this action"

**Phase to address:**
Phase "Polkit rule generalization". Two-file approach documented as the chosen pattern in PROJECT.md "Key Decisions" once decided.

---

### Pitfall 11: PyPI metadata — new package name, stale `egg-info/` in repo, author attribution drift

**What goes wrong:**
Observed in this repo: `palworld_server_launcher.egg-info/PKG-INFO` is tracked in git (shown in `git status` as modified). This is pre-built distribution metadata from a local `pip install -e .` or `setup.py develop` run. Symptoms after the refactor to `logpose`:

1. Build picks up stale egg-info. `python -m build` can find `palworld_server_launcher.egg-info/` and get confused about the project name — some backends happily generate a wheel named `palworld_server_launcher-X.Y-py3-none-any.whl` even though `pyproject.toml` says `name = "logpose"`. The upload to PyPI then either fails or (worse) succeeds with the wrong name.
2. Name already taken / typosquat risk. "logpose" is a reasonable English-ish word; check PyPI before release. Fallbacks named in PROJECT.md: `logpose-launcher`, `logpose-server-launcher`.
3. Author attribution + PyPI trust. Publishing a new package from the same author as `palworld-server-launcher` is fine — but if `pyproject.toml` keeps the existing author entry and the old package is labeled as abandoned without a deprecation notice, users hitting `pip install palworld-server-launcher` get a working but frozen v0.1.19 with no signal to migrate.
4. Classifiers and keywords drift. Keywords/classifiers from the Palworld package (e.g. "palworld", "pal world") getting copied verbatim into `logpose` is misleading — PyPI search will surface `logpose` for unrelated Palworld queries.

**How to avoid:**
- Delete `palworld_server_launcher.egg-info/` and add to `.gitignore`. Egg-info is build output, not source. It should never have been committed. This is safe: `pip install -e .` regenerates it on demand.
- Add `*.egg-info/`, `build/`, `dist/` to `.gitignore` (if not already present).
- Before first `logpose` release, `rm -rf build/ dist/ *.egg-info/` then `python -m build` from a clean tree. Inspect `dist/*.whl` with `unzip -p ... METADATA` to confirm `Name: logpose`.
- Verify on PyPI: `curl -sI https://pypi.org/pypi/logpose/json` — a 404 means the name is free. Reserve by doing a test upload to TestPyPI first.
- Update `pyproject.toml` keywords to game-agnostic terms: `["steamcmd", "game-server", "dedicated-server", "systemd", "palworld", "ark-survival-evolved"]`. Keep both game names to aid discovery without misleading.
- Add a deprecation note to `palworld-server-launcher` on PyPI via a v0.1.20 README-only release with a banner: "This package is frozen; see `logpose` for multi-game support including Palworld." Do NOT auto-migrate users — PROJECT.md explicitly calls this out as out of scope.
- Use PyPI Trusted Publishing (OIDC via GitHub Actions) to avoid token rot. Documentation and release phase.

**Warning signs:**
- `git status` shows `palworld_server_launcher.egg-info/PKG-INFO` modified (it does right now — see `gitStatus`)
- `python -m build` output mentions `palworld_server_launcher` when you are building `logpose`
- `twine upload` fails with "name already taken" or "you do not own this package"
- PyPI page for `logpose` shows description that mentions only Palworld

**Phase to address:**
Phase "PyPI publishing" (release phase). Egg-info cleanup is a one-liner for Phase "Refactor to GAMES dict" exit criteria — any phase touching `main.py` will regenerate it, so cleaning it up + adding to `.gitignore` early avoids repeated `git status` noise.

---

### Pitfall 12: Firewall and Port conflicts — two games, same default ports, one box

**What goes wrong:**
Operator installs Palworld (default UDP 8211) and ARK (default UDP 7777 game + 27015 query + 32330 RCON) on the same VM. Starts one, then starts the other. Everything works — until they change Palworld's port to 7777 because "that's the port I remember," or install a third game later that uses 27015, and suddenly one server silently fails to advertise because both processes bind 0.0.0.0:27015 race. The systemd unit says `active (running)` but UDP `ss -uln` shows the socket bound to only one PID.

Also: no firewall manipulation. If operator runs on a cloud VM with `ufw` or cloud-provider SG rules that do not open the ARK ports, the ARK install silently "works" but no one can connect. Palworld's single port is easier to remember to open; ARK's three ports are easy to miss.

**Why it happens:**
- No cross-game port validation in the install flow.
- systemd doesn't error on UDP bind conflicts the way TCP listen sockets fail loudly — UDP SO_REUSEADDR + race = two binds, one of them getting zero traffic.
- Default port overlap: 7777 is UE1/UE3/UE4 default across many games. 27015 is Valve query default across all Source games AND Steam Query Protocol — any Steam-advertised server wants it.

**How to avoid:**
- In `logpose <game> install`, before writing the service file, check `ss -uln`/`ss -tln` for each port the game will bind. Refuse to install if occupied (unless `--force`).
- Also check the other game's installed config if present — if Palworld is installed with port 8211 and ARK's QueryPort is also being set to 8211, refuse.
- Document the full port list per game in `GAMES[game]['ports']` as a list of `(port, protocol, purpose)` tuples. Print them at end of install: "Open UDP 7777, UDP 27015, TCP 32330 on your firewall."
- Do NOT run `ufw allow` automatically — surprise firewall mutations are a support nightmare. Print the exact `ufw`/`firewalld`/cloud-provider commands the operator should run.
- `logpose <game> status` should include port-bind check: for each expected port, verify there's a socket, color red if missing.

**Warning signs:**
- Two `logpose install` flows succeed in sequence, but only one server shows up in its browser
- `ss -ulnp | grep 27015` shows PID of wrong process
- Cloud VM with a public IP but server never appears — UDP inbound blocked at SG/firewall level

**Phase to address:**
Phase "ARK install flow" (port collision check — Palworld then ARK). Phase "Release polish" (status command port readback, README firewall docs).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `PAL_SERVER_DIR` as module global "just for Palworld" | One fewer line to change | Any "ARK-only box" install path hits `NameError`/wrong path; refactor regression surface | Never — fold into `GAMES["palworld"]` |
| Share a single polkit rule file for both games | Small template change | ARK uninstall either leaves stale rule or needs "regenerate both" dance; template typo breaks both at once | Never — two files is cleaner |
| Ship `steamclient.so` sdk64 fix for ARK too, skip sdk32 | Symmetry with Palworld | Server launches but never advertises; hours debugging network before realizing it's sdk32 | Never — ARK needs both paths |
| Use `configparser.ConfigParser()` with defaults for ARK INI | "It's INI, should just work" | `%` in MOTD crashes edit; duplicate keys crash edit; case-folded output reverts settings to defaults | Never — always `RawConfigParser(strict=False, interpolation=None)` + `optionxform=str` |
| Skip the byte-diff Palworld-compat test during refactor | Faster phase completion | Any subtle drift in service/polkit file leaks to production; ops hit weird "why did my service restart differently?" bugs | Never — takes <30 lines of code to write the check |
| Hard-code `--session-name` on the command line | Works for alphanumeric names | First operator with spaces/brackets in name hits truncation then ticket | Never — always via INI |
| Install `libc6-i386` unconditionally on every apt install (Palworld too) | One less code path | Drags i386 arch onto slim images; conflicts on hardened containers; zero benefit for Palworld | Never — gate by `GAMES[game]['apt_packages']` |
| Keep `sys.exit(1)` in Typer commands post-refactor | Works | Breaks Typer's test runner exit-code assertions; harder to wrap in callbacks | Only during initial port; convert to `raise typer.Exit(1)` in the refactor phase |
| Ignore committed `*.egg-info/` until release | "Not broken" | Release-time surprise: wheel name mismatch; stale PKG-INFO confuses `pip show` | Never — delete + gitignore on first refactor commit |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SteamCMD | Assume it's idempotent and retry-safe on network flake | Use `+app_update <id> validate` every time (already done in v0.1.19). On failure, retry with full re-validate rather than partial. Accept license via `debconf-set-selections` before first `apt-get install steamcmd` (already done). |
| SteamCMD (ARK) | Forget `dpkg --add-architecture i386` before installing 32-bit libs | Keep the existing `dpkg --add-architecture i386` line in `_install_steamcmd()`. It's load-bearing for ARK even though Palworld did not need the i386 libs themselves. |
| systemd (ARK) | Use `Type=simple` with a shell wrapper; SIGTERM eaten | `Type=exec` + direct binary path in `ExecStart`. If wrapper is unavoidable, `exec "$@"` as last line. |
| systemd (Palworld, preserve) | Accidentally change `Type=` or `Restart=` values in shared template logic | Byte-for-byte diff the rendered unit file against v0.1.19 baseline. |
| Polkit | Edit the rule file but forget `systemctl restart polkit.service` | `_setup_polkit()` already calls this. Preserve during refactor. |
| Polkit (uninstall) | No `logpose <game> uninstall` path removes the rule file — stale rules accumulate | Even if uninstall is not in v0.2.0 scope (it's not in PROJECT.md), document in README that `sudo rm /etc/polkit-1/rules.d/40-arkserver.rules && sudo systemctl restart polkit.service` is the manual removal step. |
| Steam Workshop / ARK mods | Attempting to auto-install mods during `install` | Out of scope for v0.2.0 (not in PROJECT.md). Do not accidentally wire mod logic into the ARK launch args builder. Mods via `?GameModIds=...` is a known follow-up, not now. |
| RCON | Trust `RCONEnabled=True` in the INI alone | Also pass on command line AND set `ServerAdminPassword`. Verify with `ss -tln | grep <rcon_port>` in a post-install check. |
| apt / dpkg on fresh GCP VM | Assume `apt-get update` works out of the box | `_repair_package_manager()` is load-bearing per CLAUDE.md. Do not remove or "tidy." |
| PyPI upload | Upload to production PyPI first | Dry-run via TestPyPI first: `twine upload --repository testpypi dist/*`; verify with `pip install -i https://test.pypi.org/simple/ logpose` in a throwaway venv. |

---

## Performance Traps

Not really a performance domain — the tool is a one-shot installer, not a hot path — but a few scale-adjacent things:

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `LimitNOFILE` too low for ARK | ARK stuck at "loading world" with high CPU, never advertises | `LimitNOFILE=100000` on arkserver.service | First populated ARK world on any VM (immediate) |
| TimeoutStopSec too low | Save rollback / corruption on `systemctl stop` | `TimeoutStopSec=300` on arkserver.service | Large worlds, 100+ tribes, first restart after multi-day uptime |
| Steam runtime logs filling `/var/log/journal` | Disk full after weeks of uptime | `LogRateLimitIntervalSec=30s`, `LogRateLimitBurst=10000` on ARK unit, OR `SystemMaxUse=2G` in journald.conf | 2-4 weeks of uptime on default journald config with a chatty ARK build |
| `configparser` re-reads full file on every edit | Trivial for human-scale edits | Not worth optimizing — the ini is a few KB | Never at this scale; note for future mods-heavy adapters |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Default `ServerAdminPassword` left blank or set to predictable value | Anyone with RCON access can wipe the world | Generate via `secrets.token_urlsafe(16)` during install; print once; write to INI only |
| Polkit rule matches user by name only — if username is reused across boxes, someone might expect sudo protection | Low (user already owns the box), but worth noting | Current approach is correct for single-user VM; document in README that multi-user boxes need per-user scoping |
| Polkit rule file world-readable | Username/path disclosure; low risk | `sudo tee` writes 0644 by default — acceptable; do NOT try to tighten to 0600 (polkitd reads as its own user) |
| RCON exposed to public Internet | Remote code execution via RCON commands | Document that RCON port should be firewalled to admin IPs only; do not auto-open it; strongly recommend tunneling via SSH |
| `ServerAdminPassword` in plaintext in INI (world-readable by default) | Other users on the box can read it | Ensure the GameUserSettings.ini file is `0600`; set this explicitly after first write; ARK defaults to `0644` |
| Logging the admin password to stdout at install time, and into scrollback / systemd journal | Disclosure via `journalctl` | Print with clear "copy this now, it will not be shown again" banner; do NOT log it via the `_run_command` path that goes to journald |
| Passing `--admin-password` on CLI (ps-readable) | `ps aux` leaks to other local users mid-install | Accept via `typer.Option(..., prompt=True, hide_input=True)` if user insists on custom; default to generating |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Same command name across games (`logpose install`) without a game prefix | Operator runs "install" expecting one game, gets another | Game-first nesting (`logpose <game> install`) per PROJECT.md — already the chosen direction |
| Silent Palworld regression after refactor | Existing operators rerun `install` and find subtle diffs (new port default, new logging verbosity, etc.) | Byte-diff rendered files + changelog note explicitly stating "no behavior change for Palworld" |
| No "what's next?" after install | Operator unsure whether to start now, enable on boot, or edit settings first | Keep existing v0.1.19 pattern: print next-step hints. Extend for ARK with port-open reminder. |
| ARK install asks for session name but silently rejects it at game runtime due to characters | User confused why their server shows wrong name | CLI-level validation with clear error messages ("SessionName cannot contain `?`; try quotes or brackets") |
| `edit-settings` opens a raw INI editor instead of matching Palworld's interactive flow | Inconsistent UX across games | ARK's `edit-settings` uses the same interactive picker as Palworld's, driven by the parsed `configparser` dict (one key at a time, prompt for new value) |
| `logpose ark status` prints `systemctl status arkserver` raw output only | No port / RCON / session info visible | Parse and surface: session name from INI, RCON port + enabled status, bind-check for game port |
| Typer auto-help shows command names but no descriptions | "What does `logpose ark enable` do?" | Docstrings on every command function; `help=` on every `Typer()` and `add_typer()` |

---

## "Looks Done But Isn't" Checklist

- [ ] **ARK install:** Often missing `steamclient.so` in `sdk32` — verify `[ -f ~/.steam/sdk32/steamclient.so ]` after install
- [ ] **ARK install:** Often missing 32-bit deps — verify `ldd $HOME/.steam/steam/steamapps/common/ARK/ShooterGame/Binaries/Linux/ShooterGameServer | grep 'not found'` returns nothing
- [ ] **ARK systemd:** Often missing `LimitNOFILE` — verify `grep LimitNOFILE /etc/systemd/system/arkserver.service` shows 100000
- [ ] **ARK systemd:** Often missing `TimeoutStopSec` and `KillSignal=SIGINT` — verify in unit file
- [ ] **ARK settings adapter:** Often fails on `%` in MOTD — verify round-trip with a test MOTD containing `50% XP`
- [ ] **ARK settings adapter:** Often loses case — verify `ServerAdminPassword` (exact case) is present in the file after an edit round-trip
- [ ] **Palworld compat:** Rendered `palserver.service` and `palserver.rules` are byte-identical to v0.1.19 fixtures
- [ ] **Polkit:** Two separate rule files exist per installed game — verify `ls /etc/polkit-1/rules.d/40-*server.rules`
- [ ] **Typer CLI:** `logpose palworld` (no subcommand) exits 2 and prints help — not exit 0
- [ ] **Typer CLI:** Global `--verbose` works from root AND propagates into subcommands via `ctx.obj`
- [ ] **RCON:** After ARK install, `ss -tln | grep <rcon_port>` shows the socket listening
- [ ] **Port check:** `logpose ark install` refuses to proceed if 7777/27015/32330 are bound by another process
- [ ] **egg-info:** `palworld_server_launcher.egg-info/` is deleted and in `.gitignore`
- [ ] **PyPI:** Test upload to TestPyPI succeeds and `pip install` from there works in a fresh venv before production upload
- [ ] **README:** Migration note present: "`palworld-server-launcher` v0.1.19 stays frozen; `logpose` is a new package"

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| ARK won't launch (missing lib32gcc-s1) | LOW | `sudo apt-get install -y lib32gcc-s1 libc6-i386 libncurses5 libncursesw5` then `systemctl restart arkserver` |
| ARK launches but server not in browser (sdk32 missing) | LOW | `mkdir -p ~/.steam/sdk32 && cp ~/.steam/steam/linux32/steamclient.so ~/.steam/sdk32/` then restart |
| ARK hangs at world load (LimitNOFILE) | LOW | Edit `/etc/systemd/system/arkserver.service`, add `LimitNOFILE=100000` under `[Service]`, `systemctl daemon-reload && systemctl restart arkserver` |
| ARK save rollback after `systemctl stop` | MEDIUM | Restore from `.ark` backup if present in `ShooterGame/Saved/SavedArks/`; sort by mtime; pick the pre-stop one. Add `TimeoutStopSec=300` + `KillSignal=SIGINT` to prevent next time. |
| `configparser` crashes on ARK INI edit | LOW | Rebuild parser with `RawConfigParser(strict=False, interpolation=None)` + `optionxform=str`; shipping a fix is one code change |
| ARK INI lost case after edit (all keys lowercase) | MEDIUM | Restore from ARK's own `.ini.bak` (ARK writes one on first startup); or regenerate from defaults and re-apply operator changes |
| Palworld regression after refactor (rendered service differs) | HIGH | `git revert` the offending commit; byte-diff test becomes mandatory exit criterion. Any live Palworld installs: `logpose palworld install` to re-render, then restart. |
| Wrong PyPI package name uploaded | MEDIUM | PyPI does NOT allow re-uploading the same version. Bump version (e.g. v0.2.0 to v0.2.1) with fixed name; yank the bad upload; document in changelog |
| Polkit merged rule breaks both games | MEDIUM | Ship a hotfix release that replaces merged rule with two per-game rules (the recommended pattern) |
| Port conflict between Palworld and ARK | LOW | Change one game's port via `edit-settings` or reinstall with `--port <other>`; document check in status output |
| ARK SessionName truncated in browser | LOW | Edit `GameUserSettings.ini` `[SessionSettings] SessionName=...`; remove any `?SessionName=...` from launch args; restart |
| RCON connects but auth rejected | LOW | Verify `ServerAdminPassword` in `[ServerSettings]` of GameUserSettings.ini matches what RCON client is sending; watch for `%` in password needing `%%` escaping if parser has interpolation on (shouldn't, per Pitfall 5 fix) |

---

## Pitfall-to-Phase Mapping

Assumes the following rough phase outline for v0.2.0 (roadmap will finalize):

- P-REFACTOR: Refactor `main.py` to `GAMES` dict + per-game helpers; package rename `palworld_server_launcher` to `logpose`
- P-TYPER: Convert CLI to nested game-first subcommands
- P-ARK-INSTALL: ARK SteamCMD install, sdk fix, dependencies
- P-ARK-SYSTEMD: ARK systemd service template + polkit rule
- P-ARK-SETTINGS: ARK `GameUserSettings.ini` adapter + `edit-settings`
- P-RELEASE: README updates, PyPI publish

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. ARK Linux deps (`lib32gcc-s1` etc.) | P-ARK-INSTALL | Fresh VM end-to-end install; `ldd ShooterGameServer | grep 'not found'` empty |
| 2. `steamclient.so` sdk32 | P-ARK-INSTALL | `ls ~/.steam/sdk32/steamclient.so` exists; server visible in browser |
| 3. `LimitNOFILE` missing | P-ARK-SYSTEMD | `cat /proc/$(pgrep ShooterGame)/limits` shows 100000 |
| 4. Hard-kill save rollback | P-ARK-SYSTEMD | Test `systemctl stop` on populated world; save file mtime within 10s of stop |
| 5. `configparser` on ARK ini | P-ARK-SETTINGS | Round-trip test with `%`, duplicate keys, mixed-case keys; output is byte-equal for unchanged keys |
| 6. Refactor regression | P-REFACTOR | Byte-diff `palserver.service` and `palserver.rules` vs v0.1.19 fixtures |
| 7. Typer nested footguns | P-TYPER | Manual CLI smoke test matrix (no-args, --help at each level, bad subcommand) |
| 8. ARK SessionName mangling | P-ARK-INSTALL | CLI rejects `?[]"` in name; spaces routed to INI only, never launch args |
| 9. RCON silently off | P-ARK-INSTALL + P-ARK-SETTINGS | Post-install: `ss -tln | grep <rcon_port>` shows listening; RCON client auth succeeds |
| 10. Polkit multi-unit | P-ARK-SYSTEMD | `pkcheck` for both units under installing user returns authorized |
| 11. PyPI metadata / egg-info | P-REFACTOR (gitignore) + P-RELEASE | `dist/*.whl` METADATA shows `Name: logpose`; TestPyPI install works |
| 12. Port conflicts / firewall | P-ARK-INSTALL + P-RELEASE | `ss -uln` pre-flight check rejects occupied ports; README lists firewall commands |

---

## Sources

### ARK Linux server (deps, paths, SIGTERM, RCON, sessionname)
- ARK Official Community Wiki, Dedicated server setup — https://ark.wiki.gg/wiki/Dedicated_server_setup (HIGH)
- ARK Fandom Wiki, Dedicated server setup — https://ark.fandom.com/wiki/Dedicated_server_setup (HIGH; cross-checked with official wiki)
- ARK Official Community Wiki, Server configuration — https://ark.wiki.gg/wiki/Server_configuration (HIGH)
- LinuxGSM arkserver docs — https://linuxgsm.com/servers/arkserver/ (HIGH)
- arkmanager/ark-server-tools — https://github.com/arkmanager/ark-server-tools (HIGH; canonical community tooling)
- arkmanager issues on SessionName with spaces: #15, #44, #562 (HIGH)
- ServerMania KB, ARK on Linux — https://www.servermania.com/kb/articles/how-to-install-ark-survival-evolved-server-on-linux (MEDIUM; mentions `sdk32` explicitly)
- linuxvox.com guide — https://linuxvox.com/blog/ark-dedicated-server-linux/ (MEDIUM)
- pimylifeup ARK on Linux, ulimit — https://pimylifeup.com/ark-dedicated-server-linux/ (MEDIUM)
- Akliz RCON on ARK — https://help.akliz.net/docs/use-rcon-with-your-ark-server (MEDIUM)
- Steam Community ARK shutdown discussions — https://steamcommunity.com/app/346110/discussions/0/615086038674610998/ (MEDIUM; community consensus on graceful shutdown)

### Python configparser edge cases
- Python docs, configparser — https://docs.python.org/3/library/configparser.html (HIGH)
- cpython issue #107428, duplicate section/option handling (HIGH)
- cpython issue #123186, `%` interpolation (HIGH)
- Python bug tracker #854484 (dup options) (HIGH)
- LinuxGSM issue #1104, ARK duplicate params (MEDIUM; confirms duplicates occur in ARK ini files in practice)

### Polkit
- freedesktop polkit reference — https://www.freedesktop.org/software/polkit/docs/latest/polkit.8.html (HIGH)
- ArchWiki Polkit — https://wiki.archlinux.org/title/Polkit (HIGH)
- Debian Wiki PolicyKit — https://wiki.debian.org/PolicyKit (HIGH)

### Typer
- Typer docs, nested subcommands — https://typer.tiangolo.com/tutorial/subcommands/nested-subcommands/ (HIGH)
- Typer docs, subcommand name and help — https://typer.tiangolo.com/tutorial/subcommands/name-and-help/ (HIGH)
- Typer discussion #1123, global options (MEDIUM)
- jacobian.org Til, common arguments with Typer (MEDIUM; explicit callback-based global-options pattern)

### systemd
- systemd.exec(5), LimitNOFILE — https://www.freedesktop.org/software/systemd/man/systemd.exec.html (HIGH)
- Red Hat KB, systemd service limits — https://access.redhat.com/solutions/1257953 (MEDIUM)

### Project-local
- `.planning/PROJECT.md` — scope, constraints, key decisions (HIGH)
- `palworld_server_launcher/main.py` — current code structure, globals, helpers (HIGH)
- `palworld_server_launcher/templates/palserver.rules.template` — current polkit rule shape, JS escape pattern (HIGH)
- Observed: `palworld_server_launcher.egg-info/PKG-INFO` tracked in git — per initial `gitStatus` snapshot

### Confidence notes
- HIGH: items cross-verified between official docs and at least one other independent source
- MEDIUM: single authoritative source or multiple community sources converging
- LOW: "25-char SessionName truncation" — not substantiated; community evidence points to space/special-character mangling at the command-line level, not a character count limit. Documented as Pitfall 8 with the real root cause.

---
*Pitfalls research for: multi-game dedicated server launcher (logpose), ARK + Palworld on Debian/Ubuntu*
*Researched: 2026-04-12*
