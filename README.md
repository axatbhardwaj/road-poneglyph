# logpose

A multi-game dedicated server launcher for Linux. `logpose` installs, configures, and manages Palworld and ARK: Survival Evolved servers on Debian and Ubuntu using `systemd` and Polkit (Palworld) or `arkmanager` wrapped by a NOPASSWD sudoers fragment (ARK). Day-to-day start/stop/restart of Palworld needs no `sudo` at all; ARK management uses `sudo -u steam arkmanager ...` without a password prompt thanks to the installed `/etc/sudoers.d/logpose-ark` fragment.

## Features

- **Two games, one CLI**: `logpose palworld <verb>` installs a native systemd service for PalServer; `logpose ark <verb>` installs ark-server-tools (`arkmanager`) and wraps every verb.
- **Automated installation**: downloads SteamCMD, pulls the right app (Palworld app id 2394010 or ARK: Survival Evolved app id 376030), and writes a systemd unit.
- **Package manager repair**: attempts to fix common `apt`/`dpkg` breakage before running steamcmd.
- **Merged Polkit rule**: a single `/etc/polkit-1/rules.d/40-logpose.rules` authorises the invoking user to start/stop/restart every known game service unit without `sudo`.
- **ARK sudoers fragment**: `/etc/sudoers.d/logpose-ark` lets the invoking user run `sudo -u steam /usr/local/bin/arkmanager *` with no password prompt.
- **Opt-in autostart for ARK**: `arkserver.service` is installed but NOT enabled at boot by default — pass `--enable-autostart` to `logpose ark install` or run `logpose ark enable` later.
- **Interactive settings editor**: `edit-settings` parses the per-game config file (`PalWorldSettings.ini` for Palworld, `/etc/arkmanager/instances/main.cfg` for ARK) and lets you change values interactively.

## Prerequisites

- A Debian 12+/13 or Ubuntu 22.04+/24.04 server (Linux only).
- `sudo` privileges for the user running `logpose`.
- Python 3.8 or newer.
- For ARK only: apt components `contrib non-free` (Debian) or `multiverse` (Ubuntu). `logpose ark install` enables `contrib non-free` on Debian automatically; Ubuntu server images ship `multiverse` by default.

## Installation

```bash
pip install logpose-launcher
```

The PyPI distribution is named `logpose-launcher`; the installed CLI binary is `logpose`. A pipx install also works if you prefer an isolated user-level environment:

```bash
pipx install logpose-launcher
```

## Migration from palworld-server-launcher v0.1.19

`logpose` v0.2.0 replaces the older `palworld-server-launcher` v0.1.19 package. Read this section before upgrading — the distribution rename means a `pip install --upgrade` on the old name will NOT pull v0.2.0.

- **PyPI distribution renamed.** v0.1.19 shipped as `palworld-server-launcher`; v0.2.0 ships as `logpose-launcher`. `pip install --upgrade palworld-server-launcher` will not find v0.2.0 — the name changed.
- **Recommended path: fresh install.** Install the new distribution rather than trying to upgrade in place:

  ```bash
  pip install logpose-launcher
  pip uninstall palworld-server-launcher   # safe — separate distribution
  ```

- **CLI entry point changed.** The old binary was `palworld-server-launcher`; the new binary is `logpose`. Update shell aliases, cron entries, or shell scripts that invoke the legacy name.
- **Your existing Palworld server keeps working.** v0.1.19 installed `/etc/systemd/system/palserver.service` and game files under `~/Steam/steamapps/common/PalServer`. v0.2.0 operates on the same systemd unit and the same directory — `logpose palworld start`, `stop`, `restart`, `status` all target the service your v0.1.19 install created. No reinstall is required just to adopt the new CLI name.
- **Manual Polkit cleanup (POL-04).** v0.1.19 wrote `/etc/polkit-1/rules.d/40-palserver.rules`. v0.2.0 writes `/etc/polkit-1/rules.d/40-logpose.rules` instead — the merged rule covers every known game service unit. Polkit merges rule files additively, so the two files coexist harmlessly. Once you have confirmed that `logpose palworld start` / `stop` / `restart` work without a password under v0.2.0, remove the old rule:

  ```bash
  sudo rm /etc/polkit-1/rules.d/40-palserver.rules
  ```

## Quick Start

### Palworld

```bash
# Install at port 8211 with a 16-player cap and start immediately
logpose palworld install --port 8211 --players 16 --start
```

### ARK: Survival Evolved

```bash
# Install with an admin password (required) and start the server
logpose ark install --map TheIsland --admin-password 'your-strong-password' --start
```

If you prefer not to pick a password yourself, use `--generate-password` and `logpose` will generate a 128-bit url-safe admin password and print it once.

## Palworld Usage (`logpose palworld <verb>`)

Every Palworld verb targets the native `palserver.service` systemd unit. Start/stop/restart run without `sudo` thanks to `/etc/polkit-1/rules.d/40-logpose.rules`.

```bash
# Install (downloads SteamCMD, pulls PalServer, writes palserver.service)
logpose palworld install --port 8211 --players 32 --start
```
Creates the systemd unit at port 8211 with a 32-player cap and starts the server right away.

```bash
logpose palworld start
```
Starts `palserver.service` via `systemctl start` (no sudo required).

```bash
logpose palworld stop
```
Stops the server gracefully.

```bash
logpose palworld restart
```
Restarts the service — useful after editing `PalWorldSettings.ini`.

```bash
logpose palworld status
```
Shows current service status (`systemctl status palserver`).

```bash
logpose palworld enable
```
Enables `palserver.service` at boot.

```bash
logpose palworld disable
```
Disables `palserver.service` at boot.

```bash
logpose palworld update
```
Re-runs SteamCMD against the Palworld app id and leaves the service untouched. Restart the service afterwards to pick up changes.

```bash
logpose palworld edit-settings
```
Opens an interactive editor against `PalWorldSettings.ini`, preserving unknown keys.

## ARK Usage (`logpose ark <verb>`)

The ARK integration is an `arkmanager` (`ark-server-tools`) wrapper. `logpose ark install` creates a dedicated `steam` system user, drops `/etc/sudoers.d/logpose-ark` to allow the invoking user to call `sudo -u steam /usr/local/bin/arkmanager *` without a password, and writes `/etc/arkmanager/instances/main.cfg`. An `arkserver.service` unit is written but intentionally left disabled at boot — opt in with `--enable-autostart` (at install time) or `logpose ark enable` (afterwards).

Valid maps (12 supported): TheIsland, TheCenter, ScorchedEarth_P, Aberration_P, Extinction, Ragnarok, Valguero_P, CrystalIsles, LostIsland, Fjordur, Genesis, Genesis2.

```bash
# Minimal install
logpose ark install --admin-password 'strong-password'

# Full-featured install: autostart on boot, custom session name, start now
logpose ark install \
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
logpose ark start
```
Runs `sudo -u steam /usr/local/bin/arkmanager start` — boots the ARK server via `arkmanager`.

```bash
logpose ark stop
```
Graceful shutdown via `arkmanager stop` (saves world).

```bash
logpose ark restart
```
Runs `arkmanager restart`.

```bash
logpose ark status
```
`arkmanager status` — shows running state and connected players.

```bash
logpose ark saveworld
```
Forces a world save via `arkmanager saveworld` (uses RCON under the hood).

```bash
logpose ark backup
```
Creates a save backup via `arkmanager backup`.

```bash
logpose ark update
```
Updates the ARK server. Runs `arkmanager update --validate --beta=preaquatica` twice on purpose — steamcmd has a known first-run self-update quirk where the first invocation only updates steamcmd itself; the second invocation does the actual game update.

```bash
logpose ark enable
```
Enables `arkserver.service` at boot. Only effective if `arkserver.service` exists — pass `--enable-autostart` to `logpose ark install` if you did not already.

```bash
logpose ark disable
```
Disables `arkserver.service` from starting at boot.

```bash
logpose ark edit-settings
```
Opens an interactive editor against `/etc/arkmanager/instances/main.cfg` (arkmanager's instance config). It does NOT edit `GameUserSettings.ini` — arkmanager owns that file; editing it by hand is unsupported.

## Firewall / Port Reference

`logpose` does NOT manage your firewall. Open the ports below yourself (example `ufw` rules included).

| Game     | Protocol | Port  | Purpose                                  |
|----------|----------|-------|------------------------------------------|
| Palworld | UDP      | 8211  | Game + query (single port)               |
| ARK      | UDP      | 7777  | Game port (implicit in arkmanager)       |
| ARK      | UDP      | 7778  | `ark_Port` raw socket                    |
| ARK      | UDP      | 27015 | `ark_QueryPort` Steam query              |
| ARK      | TCP      | 27020 | `ark_RCONPort` RCON admin                |

Example ufw rules:

```bash
# Palworld
sudo ufw allow 8211/udp

# ARK
sudo ufw allow 7777/udp
sudo ufw allow 7778/udp
sudo ufw allow 27015/udp
sudo ufw allow 27020/tcp
```

## Permissions & Security Model

**Palworld.** The merged Polkit rule at `/etc/polkit-1/rules.d/40-logpose.rules` grants the installing user permission to invoke `org.freedesktop.systemd1.manage-units` on `palserver.service` (and every other registered game service unit) without `sudo`. You can verify the grant with:

```bash
pkcheck --action-id=org.freedesktop.systemd1.manage-units \
        --process $$ --allow-user-interaction
```

No part of the Palworld flow edits `/etc/sudoers` or asks for a password after installation.

**ARK.** The `arkmanager` tool runs as a dedicated `steam` system user, so every ARK verb is really `sudo -u steam /usr/local/bin/arkmanager ...`. `logpose ark install` writes `/etc/sudoers.d/logpose-ark`, which grants the installing user exactly `NOPASSWD: /usr/local/bin/arkmanager *` — no broader sudo rights, no wildcard path, no `ALL=(ALL)` clause. This is the minimum permission surface that still lets you run `logpose ark start`, `stop`, `saveworld`, `backup`, etc. without being prompted for a password.

## Version

```bash
logpose --version
```

## Supported OS

- Debian 12 (bookworm) and Debian 13 (trixie).
- Ubuntu 22.04 LTS and Ubuntu 24.04 LTS.
- Linux only. macOS and Windows are not supported.
- ARK prerequisite: `contrib non-free` apt components on Debian (enabled automatically by `logpose ark install`), or `multiverse` on Ubuntu (already present on stock Ubuntu server images).

## License

MIT — see `LICENSE`.
