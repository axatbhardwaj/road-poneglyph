# road-poneglyph

A multi-game dedicated server launcher for Linux. `road-poneglyph` installs, configures, and manages Palworld, ARK: Survival Evolved, and Satisfactory servers on Debian and Ubuntu using `systemd` and Polkit. Day-to-day start/stop/restart needs no `sudo` at all thanks to the merged Polkit rule and per-game sudoers fragments.

## Features

- **Three games, one CLI**: `road-poneglyph palworld <verb>` installs a native systemd service for PalServer; `road-poneglyph ark <verb>` wraps ark-server-tools (`arkmanager`); `road-poneglyph satisfactory <verb>` installs Satisfactory via SteamCMD with SIGINT-based graceful shutdown and HTTPS API save integration.
- **Automated installation**: downloads SteamCMD, pulls the right app (Palworld 2394010, ARK 376030, Satisfactory 1690800), and writes a systemd unit.
- **Package manager repair**: attempts to fix common `apt`/`dpkg` breakage before running steamcmd.
- **Merged Polkit rule**: a single `/etc/polkit-1/rules.d/40-road-poneglyph.rules` authorises the invoking user to start/stop/restart every known game service unit without `sudo`.
- **ARK sudoers fragment**: `/etc/sudoers.d/road-poneglyph-ark` lets the invoking user run `sudo -u steam /usr/local/bin/arkmanager *` with no password prompt.
- **Opt-in autostart for ARK**: `arkserver.service` is NOT installed by default. Pass `--enable-autostart` to `road-poneglyph ark install` to write and enable the systemd unit; without the flag, manage the server exclusively through `road-poneglyph ark start/stop/...` (which call `arkmanager` directly — no systemd unit needed).
- **Interactive settings editor**: `edit-settings` parses the per-game config file (`PalWorldSettings.ini` for Palworld, `/etc/arkmanager/instances/main.cfg` for ARK, `GameUserSettings.ini` for Satisfactory) and lets you change values interactively.
- **Satisfactory HTTPS API integration**: `road-poneglyph satisfactory save` triggers a save via the game's REST API; `stop` automatically saves before sending SIGINT.

## Prerequisites

- A Debian 12+/13 or Ubuntu 22.04+/24.04 server (Linux only).
- `sudo` privileges for the user running `road-poneglyph`.
- Python 3.8 or newer.
- For ARK only: apt components `contrib non-free` (Debian) or `multiverse` (Ubuntu). `road-poneglyph ark install` enables `contrib non-free` on Debian automatically; Ubuntu server images ship `multiverse` by default.

## Installation

```bash
pip install road-poneglyph
```

The PyPI distribution is named `road-poneglyph`; the installed CLI binary is `road-poneglyph`. A pipx install also works if you prefer an isolated user-level environment:

```bash
pipx install road-poneglyph
```

## Migration from palworld-server-launcher v0.1.19

`road-poneglyph` v0.2.0 replaces the older `palworld-server-launcher` v0.1.19 package. Read this section before upgrading — the distribution rename means a `pip install --upgrade` on the old name will NOT pull v0.2.0.

- **PyPI distribution renamed.** v0.1.19 shipped as `palworld-server-launcher`; v0.2.0 ships as `road-poneglyph`. `pip install --upgrade palworld-server-launcher` will not find v0.2.0 — the name changed.
- **Recommended path: fresh install.** Install the new distribution rather than trying to upgrade in place:

  ```bash
  pip install road-poneglyph
  pip uninstall palworld-server-launcher   # safe — separate distribution
  ```

- **CLI entry point changed.** The old binary was `palworld-server-launcher`; the new binary is `road-poneglyph`. Update shell aliases, cron entries, or shell scripts that invoke the legacy name.
- **Your existing Palworld server keeps working.** v0.1.19 installed `/etc/systemd/system/palserver.service` and game files under `~/Steam/steamapps/common/PalServer`. v0.2.0 operates on the same systemd unit and the same directory — `road-poneglyph palworld start`, `stop`, `restart`, `status` all target the service your v0.1.19 install created. No reinstall is required just to adopt the new CLI name.
- **Manual Polkit cleanup (POL-04).** v0.1.19 wrote `/etc/polkit-1/rules.d/40-palserver.rules`. v0.2.0 writes `/etc/polkit-1/rules.d/40-road-poneglyph.rules` instead — the merged rule covers every known game service unit. Polkit merges rule files additively, so the two files coexist harmlessly. Once you have confirmed that `road-poneglyph palworld start` / `stop` / `restart` work without a password under v0.2.0, remove the old rule:

  ```bash
  sudo rm /etc/polkit-1/rules.d/40-palserver.rules
  ```

## Quick Start

### Palworld

```bash
# Install at port 8211 with a 16-player cap and start immediately
road-poneglyph palworld install --port 8211 --players 16 --start
```

### ARK: Survival Evolved

```bash
# Install with the admin password you want to use (or omit --admin-password for a
# hidden prompt) and start the server
road-poneglyph ark install --map TheIsland --admin-password 'your-strong-password' --start
```

If you prefer not to pick a password yourself, use `--generate-password` and `road-poneglyph` will generate a 128-bit url-safe admin password and print it once.

### Satisfactory

```bash
# Install at the default ports and start immediately
road-poneglyph satisfactory install --port 7777 --reliable-port 8888 --players 4 --start
```

**First-run note:** After installation, the first player to connect via the in-game Server Manager must "claim" the server (sets admin password). Config files (`Engine.ini`, `GameUserSettings.ini`) are only generated after the first graceful shutdown — run `road-poneglyph satisfactory stop`, then `road-poneglyph satisfactory edit-settings`.

## Palworld Usage (`road-poneglyph palworld <verb>`)

Every Palworld verb targets the native `palserver.service` systemd unit. Start/stop/restart run without `sudo` thanks to `/etc/polkit-1/rules.d/40-road-poneglyph.rules`.

```bash
# Install (downloads SteamCMD, pulls PalServer, writes palserver.service)
road-poneglyph palworld install --port 8211 --players 32 --start
```
Creates the systemd unit at port 8211 with a 32-player cap and starts the server right away.

```bash
road-poneglyph palworld start
```
Starts `palserver.service` via `systemctl start` (no sudo required).

```bash
road-poneglyph palworld stop
```
Stops the server gracefully.

```bash
road-poneglyph palworld restart
```
Restarts the service — useful after editing `PalWorldSettings.ini`.

```bash
road-poneglyph palworld status
```
Shows current service status (`systemctl status palserver`).

```bash
road-poneglyph palworld enable
```
Enables `palserver.service` at boot.

```bash
road-poneglyph palworld disable
```
Disables `palserver.service` at boot.

```bash
road-poneglyph palworld update
```
Re-runs SteamCMD against the Palworld app id and leaves the service untouched. Restart the service afterwards to pick up changes.

```bash
road-poneglyph palworld edit-settings
```
Opens an interactive editor against `PalWorldSettings.ini`, preserving unknown keys.

## ARK Usage (`road-poneglyph ark <verb>`)

The ARK integration is an `arkmanager` (`ark-server-tools`) wrapper. `road-poneglyph ark install` creates a dedicated `steam` system user, drops `/etc/sudoers.d/road-poneglyph-ark` to allow the invoking user to call `sudo -u steam /usr/local/bin/arkmanager *` without a password, and writes `/etc/arkmanager/instances/main.cfg`. An `arkserver.service` unit is written **only when `--enable-autostart` is passed at install time**; otherwise no systemd unit exists for ARK and day-to-day management goes through `arkmanager` directly via `road-poneglyph ark <verb>`.

Valid maps (12 supported): TheIsland, TheCenter, ScorchedEarth_P, Aberration_P, Extinction, Ragnarok, Valguero_P, CrystalIsles, LostIsland, Fjordur, Genesis, Genesis2.

```bash
# Minimal install
road-poneglyph ark install --admin-password 'strong-password'

# Full-featured install: autostart on boot, custom session name, start now
road-poneglyph ark install \
    --map Ragnarok \
    --port 7778 --query-port 27015 --rcon-port 27020 \
    --players 20 \
    --session-name 'MyArkServer' \
    --admin-password 'strong-password' \
    --beta preaquatica \
    --enable-autostart --start
```
Runs a full `arkmanager` install: enables the required apt components on Debian, creates the `steam` user, fetches ark-server-tools, writes `main.cfg`, and optionally enables boot autostart.

```bash
road-poneglyph ark start
```
Runs `sudo -u steam /usr/local/bin/arkmanager start` — boots the ARK server via `arkmanager`.

```bash
road-poneglyph ark stop
```
Graceful shutdown via `arkmanager stop` (saves world).

```bash
road-poneglyph ark restart
```
Runs `arkmanager restart`.

```bash
road-poneglyph ark status
```
`arkmanager status` — shows running state and connected players.

```bash
road-poneglyph ark saveworld
```
Forces a world save via `arkmanager saveworld` (uses RCON under the hood).

```bash
road-poneglyph ark backup
```
Creates a save backup via `arkmanager backup`.

```bash
road-poneglyph ark update
```
Updates the ARK server. Runs `arkmanager update --validate --beta=preaquatica` twice on purpose — steamcmd has a known first-run self-update quirk where the first invocation only updates steamcmd itself; the second invocation does the actual game update.

```bash
road-poneglyph ark enable
```
Enables `arkserver.service` at boot. Only effective if `arkserver.service` exists — pass `--enable-autostart` to `road-poneglyph ark install` if you did not already.

```bash
road-poneglyph ark disable
```
Disables `arkserver.service` from starting at boot.

```bash
road-poneglyph ark edit-settings
```
Opens an interactive editor against `/etc/arkmanager/instances/main.cfg` (arkmanager's instance config). It does NOT edit `GameUserSettings.ini` — arkmanager owns that file; editing it by hand is unsupported.

## Satisfactory Usage (`road-poneglyph satisfactory <verb>`)

Satisfactory uses a native SteamCMD install (app 1690800) with a `satisfactory.service` systemd unit. The server shuts down via **SIGINT** (not SIGTERM) and does NOT auto-save on shutdown — `road-poneglyph satisfactory stop` calls the HTTPS API `SaveGame` endpoint before sending SIGINT.

**System requirements:** 12-16 GB RAM recommended (single-threaded simulation; autosaves spike memory).

```bash
# Install with default ports, 4-player cap, and start
road-poneglyph satisfactory install --port 7777 --reliable-port 8888 --players 4 --start

# With auto-update on every service start
road-poneglyph satisfactory install --port 7777 --reliable-port 8888 --players 4 --auto-update --start
```

```bash
road-poneglyph satisfactory start
```
Starts `satisfactory.service` via `systemctl start` (no sudo required).

```bash
road-poneglyph satisfactory stop
```
Calls the HTTPS API `SaveGame` first (pre-shutdown save), then sends SIGINT for graceful shutdown. The server does NOT auto-save on any signal.

```bash
road-poneglyph satisfactory restart
```
Restarts the service (triggers ExecStop save → SIGINT → ExecStart).

```bash
road-poneglyph satisfactory status
```
Shows systemd status + HTTPS API health check (if server is running and claimed).

```bash
road-poneglyph satisfactory save [name]
```
Triggers a save via the HTTPS REST API. Requires the server to be claimed (admin password set in-game). On first use, prompts for admin password and caches the Bearer token at `~/.config/road-poneglyph/satisfactory-api-token`.

```bash
road-poneglyph satisfactory enable
```
Enables `satisfactory.service` at boot.

```bash
road-poneglyph satisfactory disable
```
Disables `satisfactory.service` from starting at boot.

```bash
road-poneglyph satisfactory update
```
Re-runs SteamCMD to validate/update the server files.

```bash
road-poneglyph satisfactory edit-settings
```
Opens an interactive editor for `GameUserSettings.ini` (Unreal Engine INI format). **Note:** Config files only exist after the first graceful stop — start the server, let it initialize, then stop before editing.

### Satisfactory First-Run Guide

1. **Install:** `road-poneglyph satisfactory install --start`
2. **Wait:** Server takes 2-5 minutes to fully initialize on first boot.
3. **Claim:** Connect via the in-game Server Manager and "Claim" the server (sets admin password).
4. **Stop once:** `road-poneglyph satisfactory stop` — this generates config files.
5. **Edit settings:** `road-poneglyph satisfactory edit-settings` — now configs exist.
6. **Start:** `road-poneglyph satisfactory start` — ready for players.

## Firewall / Port Reference

`road-poneglyph` does NOT manage your firewall. Open the ports below yourself (example `ufw` rules included).

| Game         | Protocol | Port  | Purpose                                  |
|--------------|----------|-------|------------------------------------------|
| Palworld     | UDP      | 8211  | Game + query (single port)               |
| ARK          | UDP      | 7777  | Game port (implicit in arkmanager)       |
| ARK          | UDP      | 7778  | `ark_Port` raw socket                    |
| ARK          | UDP      | 27015 | `ark_QueryPort` Steam query              |
| ARK          | TCP      | 27020 | `ark_RCONPort` RCON admin                |
| Satisfactory | UDP      | 7777  | Game traffic                             |
| Satisfactory | TCP      | 7777  | HTTPS REST API (management, saves)       |
| Satisfactory | TCP      | 8888  | Reliable messaging                       |

Example ufw rules:

```bash
# Palworld
sudo ufw allow 8211/udp

# ARK
sudo ufw allow 7777/udp
sudo ufw allow 7778/udp
sudo ufw allow 27015/udp
sudo ufw allow 27020/tcp

# Satisfactory
sudo ufw allow 7777/udp
sudo ufw allow 7777/tcp
sudo ufw allow 8888/tcp
```

## Permissions & Security Model

**Palworld.** The merged Polkit rule at `/etc/polkit-1/rules.d/40-road-poneglyph.rules` grants the installing user permission to invoke `org.freedesktop.systemd1.manage-units` on `palserver.service` (and every other registered game service unit) without `sudo`. You can verify the grant with:

```bash
pkcheck --action-id=org.freedesktop.systemd1.manage-units \
        --process $$ --allow-user-interaction
```

No part of the Palworld flow edits `/etc/sudoers` or asks for a password after installation.

**ARK.** The `arkmanager` tool runs as a dedicated `steam` system user, so every ARK verb is really `sudo -u steam /usr/local/bin/arkmanager ...`. `road-poneglyph ark install` writes `/etc/sudoers.d/road-poneglyph-ark`, which grants the installing user exactly `NOPASSWD: /usr/local/bin/arkmanager *` — no broader sudo rights, no wildcard path, no `ALL=(ALL)` clause. This is the minimum permission surface that still lets you run `road-poneglyph ark start`, `stop`, `saveworld`, `backup`, etc. without being prompted for a password.

## Version

```bash
road-poneglyph --version
```

## Supported OS

- Debian 12 (bookworm) and Debian 13 (trixie).
- Ubuntu 22.04 LTS and Ubuntu 24.04 LTS.
- Linux only. macOS and Windows are not supported.
- ARK prerequisite: `contrib non-free` apt components on Debian (enabled automatically by `road-poneglyph ark install`), or `multiverse` on Ubuntu (already present on stock Ubuntu server images).

## License

MIT — see `LICENSE`.
