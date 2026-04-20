# Satisfactory Dedicated Server on Linux — Technical Research Brief

> Researched: 2026-04-13
> Target OS: Debian 12/13, Ubuntu 22.04/24.04
> Game: Satisfactory (Coffee Stain Studios)
> Steam App ID (Server): **1690800**
> Steam App ID (Client): 526870

---

## 1. Installation Method

### SteamCMD (Anonymous Login — No Account Required)

The Satisfactory dedicated server is distributed via SteamCMD using **app ID 1690800**.
No Steam account login is required (anonymous access).

#### Prerequisites (Debian/Ubuntu)

```bash
# Enable 32-bit architecture (required for SteamCMD)
sudo dpkg --add-architecture i386
sudo apt update

# Install dependencies
sudo apt install -y \
  lib32gcc-s1 \
  lib32stdc++6 \
  libsdl2-2.0-0:i386 \
  steamcmd \
  curl \
  tar \
  tmux

# If steamcmd is not in apt (Debian without non-free repo):
# Manual install from https://developer.valvesoftware.com/wiki/SteamCMD
```

#### Server Installation

```bash
# Create dedicated user (do NOT run as root)
sudo useradd -m -s /bin/bash satisfactory
sudo -u satisfactory -i

# Install via SteamCMD
steamcmd \
  +force_install_dir /home/satisfactory/SatisfactoryDedicatedServer \
  +login anonymous \
  +app_update 1690800 validate \
  +quit
```

#### Experimental Branch

```bash
steamcmd \
  +force_install_dir /home/satisfactory/SatisfactoryDedicatedServer \
  +login anonymous \
  +app_update 1690800 -beta experimental validate \
  +quit
```

#### Disk Space

- Linux server: ~8 GB (2 GB base engine + game files)
- Windows server: ~12.4 GB

---

## 2. Runtime Requirements

### System Requirements

| Resource   | Minimum          | Recommended        |
|------------|------------------|--------------------|
| CPU        | x86-64, single-thread rating 2000+ | i5-3570 / Ryzen 5 3600+ |
| RAM        | 8 GB             | 12–16 GB           |
| Storage    | 10 GB free       | 20 GB+ (saves grow) |
| Arch       | 64-bit x86-64 only | No ARM, no 32-bit |

**Important memory notes:**
- Autosaves temporarily spike RAM by 2–4 GB above baseline
- Large factories with trains/drones/fluids can push to 12+ GB
- Game simulation is **single-threaded** — one CPU core handles all processing
- Memory leaks were largely fixed in Patch 1.1.2.0 (Nov 2025)

### Required Packages

```bash
# Core runtime (the server binary is native 64-bit Linux)
sudo apt install -y lib32gcc-s1 lib32stdc++6

# For SteamCMD itself (32-bit tool)
sudo dpkg --add-architecture i386
```

**Note:** Unlike ARK, the Satisfactory server binary itself is 64-bit native Linux.
The i386 libs are only needed for SteamCMD, not the server runtime.

### User/Permissions

- Run as a **non-root** dedicated user (e.g., `satisfactory`)
- Root execution causes permission/library issues
- Typical home: `/home/satisfactory/`

### Binary Path

```
/home/satisfactory/SatisfactoryDedicatedServer/FactoryServer.sh    # Wrapper script
/home/satisfactory/SatisfactoryDedicatedServer/Engine/Binaries/Linux/FactoryServer-Linux-Shipping  # Actual binary
```

---

## 3. Configuration

### Config File Locations (Linux)

```
<install_dir>/FactoryGame/Saved/Config/LinuxServer/Engine.ini
<install_dir>/FactoryGame/Saved/Config/LinuxServer/Game.ini
<install_dir>/FactoryGame/Saved/Config/LinuxServer/GameUserSettings.ini
```

Server settings (binary format):
```
~/.config/Epic/FactoryGame/Saved/SaveGames/ServerSettings.<PORT>.sav
```

Save files:
```
~/.config/Epic/FactoryGame/Saved/SaveGames/server/
```

Blueprints:
```
~/.config/Epic/FactoryGame/Saved/SaveGames/blueprints/
```

### Config Format

All config files use **Unreal Engine INI format** (standard `[Section]` / `Key=Value`).

### Key Configuration Settings

#### Engine.ini — Port & Networking

```ini
[/Script/ReliableMessaging.ReliableMessagingTCPFactory]
PortRangeBegin=8888
PortRangeLength=512

[/Script/OnlineSubsystemUtils.IpNetDriver]
InitialConnectTimeout=120.0
ConnectionTimeout=120.0
NetServerMaxTickRate=30
LanServerMaxTickRate=30

[/Script/SocketSubsystemEpic.EpicNetDriver]
NetServerMaxTickRate=30
LanServerMaxTickRate=30

[/Script/Engine.Engine]
NetClientTicksPerSecond=30

[CrashReportClient]
bImplicitSend=False
```

#### Game.ini — Player Count

```ini
[/Script/Engine.GameSession]
MaxPlayers=8
```

Max theoretical is 127, but impractical due to single-threaded simulation.

#### Engine.ini — Autosave

```ini
[/Script/FactoryGame.FGSaveSession]
mNumRotatingAutosaves=5
```

Default autosave interval: 300 seconds (5 minutes).

#### GameUserSettings.ini — Seasonal Events

```ini
[/Script/FactoryGame.FGGameUserSettings]
FG.DisableSeasonalEvents=0
```

### Command-Line Arguments

| Argument | Purpose |
|----------|---------|
| `-Port=7777` | Game port (UDP) |
| `-ReliablePort=8888` | Reliable messaging port (TCP) — added in v1.1 |
| `-ExternalReliablePort=8888` | External reliable port (if NAT differs) |
| `-multihome=0.0.0.0` | Bind to specific interface |
| `-log` | Enable logging output |
| `-unattended` | Suppress interactive dialogs |
| `-DisableSeasonalEvents` | Disable FICSMAS |
| `-DisablePacketRouting` | Disable packet router |
| `-ini:<FILE>:[<SECTION>]:<KEY>=<VALUE>` | Override INI settings from CLI |

**Important:** Custom port arguments must be placed **BEFORE** `-log -unattended`.
Arguments after those flags may be ignored.

### Full Launch Example

```bash
./FactoryServer.sh \
  -Port=7777 \
  -ReliablePort=8888 \
  -ExternalReliablePort=8888 \
  -multihome=0.0.0.0 \
  -log \
  -unattended
```

---

## 4. Networking / Ports

### Current Port Layout (v1.1+, as of late 2025)

| Port | Protocol | Purpose | Notes |
|------|----------|---------|-------|
| 7777 | **UDP** | Game traffic | Also serves HTTPS API |
| 7777 | **TCP** | HTTPS REST API | Same port as game |
| 8888 | **TCP** | Reliable messaging | New in v1.1 |

### Deprecated Ports (pre-v1.1)

| Port | Protocol | Purpose | Status |
|------|----------|---------|--------|
| 15777 | UDP | Server Query (old) | **No longer used** |
| 15000 | UDP | Beacon (old) | **No longer used** |

### Firewall Rules (UFW)

```bash
sudo ufw allow 7777/udp comment "Satisfactory Game"
sudo ufw allow 7777/tcp comment "Satisfactory API"
sudo ufw allow 8888/tcp comment "Satisfactory Reliable Messaging"
```

### Firewall Rules (iptables)

```bash
iptables -A INPUT -p udp --dport 7777 -j ACCEPT
iptables -A INPUT -p tcp --dport 7777 -j ACCEPT
iptables -A INPUT -p tcp --dport 8888 -j ACCEPT
```

### Critical Note

Port redirection (external port ≠ internal port) is **not supported** for the game port.
The forwarded port must match the value passed to `-Port=`.
Incorrect port configuration is the #1 cause of "stuck on loading screen" issues.

---

## 5. Systemd Integration

### Service File: `/etc/systemd/system/satisfactory.service`

```ini
[Unit]
Description=Satisfactory dedicated server
Wants=network-online.target
After=syslog.target network.target nss-lookup.target network-online.target

[Service]
Environment=SteamAppId=1690800
ExecStartPre=/usr/games/steamcmd +force_install_dir "/home/satisfactory/SatisfactoryDedicatedServer" +login anonymous +app_update 1690800 validate +quit
ExecStart=/home/satisfactory/SatisfactoryDedicatedServer/FactoryServer.sh -Port=7777 -ReliablePort=8888 -multihome=0.0.0.0 -log -unattended
User=satisfactory
Group=satisfactory
WorkingDirectory=/home/satisfactory/SatisfactoryDedicatedServer
Type=simple
Restart=on-failure
RestartSec=60
KillSignal=SIGINT
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
```

### Key Directives

| Directive | Value | Reason |
|-----------|-------|--------|
| `Type` | `simple` | Server runs in foreground, does not fork |
| `KillSignal` | `SIGINT` | **Critical** — SIGTERM kills immediately without cleanup |
| `Restart` | `on-failure` | Auto-restart on crash |
| `RestartSec` | `60` | Wait 60s between restarts |
| `TimeoutStopSec` | `120` | Allow time for save on shutdown |
| `ExecStartPre` | SteamCMD update | Auto-update before each start |

### Graceful Shutdown

- **SIGINT** — graceful shutdown, processes exit behavior and logging
- **SIGTERM** — kills immediately, NO save, NO cleanup (avoid!)
- The server does **NOT** auto-save on shutdown (even graceful)
- Recommendation: Enable "Auto-Save on Player Disconnect" in Server Manager
- Or call the API `Shutdown` function which triggers a save first

### Service Management

```bash
sudo systemctl daemon-reload
sudo systemctl enable satisfactory
sudo systemctl start satisfactory
sudo systemctl stop satisfactory    # Sends SIGINT
sudo systemctl status satisfactory
journalctl -u satisfactory -f       # Live logs
```

---

## 6. Server Management

### No RCON — HTTPS API Instead

Satisfactory does **NOT** support traditional RCON (Source RCON protocol).
Management is done through an **HTTPS REST API** on the same port as the game (7777).

### HTTPS API Overview

- **Base URL:** `https://<server-ip>:7777/`
- **Auth:** Bearer token (Base64 JSON payload + HEX fingerprint)
- **Content-Type:** `application/json`
- **Certificate:** Self-signed (generated on first run)

#### Authentication Flow

1. First-time claim via in-game Server Manager (sets admin password)
2. API auth: `PasswordLogin` → returns Bearer token
3. Or generate persistent token: console command `server.GenerateAPIToken`
4. Local bypass: set `FG.DedicatedServer.AllowInsecureLocalAccess=1`

#### Key API Functions

| Function | Purpose | Auth Level |
|----------|---------|------------|
| `HealthCheck` | Is server alive? | None |
| `QueryServerState` | Current state/players | Client |
| `Shutdown` | Graceful shutdown | Admin |
| `SaveGame` | Save current session | Admin |
| `LoadGame` | Load a save file | Admin |
| `CreateNewGame` | New session | Admin |
| `DownloadSaveGame` | Download .sav file | Admin |
| `UploadSaveGame` | Upload .sav file | Admin |
| `EnumerateSessions` | List available saves | Admin |
| `DeleteSaveFile` | Remove save | Admin |
| `RunCommand` | Execute console command | Admin |
| `ApplyServerOptions` | Update settings | Admin |
| `ClaimServer` | First-time claim | InitialAdmin |
| `RenameServer` | Change server name | Admin |
| `SetClientPassword` | Set join password | Admin |
| `SetAdminPassword` | Set admin password | Admin |

#### Example API Call

```bash
# Health check (no auth required)
curl -k https://localhost:7777/api/v1 \
  -H "Content-Type: application/json" \
  -d '{"function":"HealthCheck"}'

# Save game (requires auth)
curl -k https://localhost:7777/api/v1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"function":"SaveGame","data":{"SaveName":"my_save"}}'
```

### Console Commands

Available via in-game Server Manager console tab or `RunCommand` API:

- `server.SaveGame <name>` — Create named save
- `quit` / `stop` / `exit` — Shutdown server

### Updating

```bash
# Manual update
steamcmd +force_install_dir /home/satisfactory/SatisfactoryDedicatedServer \
  +login anonymous +app_update 1690800 validate +quit

# Or simply restart the systemd service (ExecStartPre handles it)
sudo systemctl restart satisfactory
```

### Backup Strategy

```bash
# Save file location
~/.config/Epic/FactoryGame/Saved/SaveGames/server/

# Manual backup
cp -r ~/.config/Epic/FactoryGame/Saved/SaveGames/server/ /backups/satisfactory/$(date +%Y%m%d)/

# Or use API to download saves
curl -k https://localhost:7777/api/v1 \
  -H "Authorization: Bearer <token>" \
  -d '{"function":"DownloadSaveGame","data":{"SaveName":"my_save"}}' \
  --output my_save.sav
```

---

## 7. Quirks and Pitfalls

### First-Run Behavior

1. **Config files are NOT generated until the server shuts down gracefully for the first time.**
   - Start the server, let it fully initialize, then stop with SIGINT
   - Only then will `Engine.ini`, `Game.ini`, `GameUserSettings.ini` appear
   - Editing INI files before first graceful stop has no effect

2. **Server must be "claimed" in-game before it can be managed.**
   - The first player to connect via the in-game Server Manager claims the server
   - This sets the admin password
   - Without claiming, the API is mostly non-functional

3. **Self-signed HTTPS certificate** is generated on first start.
   - Clients must accept/ignore certificate warnings
   - Custom certs can be placed in `FactoryGame/Certificates/`

### INI File Warnings

- **Always edit INI files with the server stopped** — files are overwritten on graceful shutdown
- Changes may be lost after game updates/patches
- Do NOT set INI files to read-only

### Memory Pitfalls

- Base idle memory: ~4–6 GB (even with no players)
- Autosave spikes: +2–4 GB temporarily
- Large factories: 8–12 GB steady state
- **Recommendation:** 16 GB RAM minimum for production use
- OOM during autosave is a common crash cause

### Single-Threaded Simulation

- All game logic runs on **one CPU core**
- More cores don't help simulation performance
- High single-thread clock speed is more important than core count

### Linux-Specific Issues

- SIGTERM (systemd default) kills without cleanup — **must use SIGINT**
- Server does not auto-save on any shutdown signal
- First-run may take several minutes as shaders/caches are built
- Ensure `vm.max_map_count` is at least 262144 for large maps:
  ```bash
  echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-satisfactory.conf
  sudo sysctl --system
  ```

### Mods Support

- Mods ARE supported on dedicated servers (since SML 3.7.0)
- Use **Satisfactory Mod Manager (SMM)** or **ficsit-cli** to install
- Check per-mod server compatibility on https://ficsit.app
- Mods install into `<install_dir>/FactoryGame/Mods/`
- All connected clients must have matching mods
- SMM works on Linux via CLI mode

### Server Claiming / Authentication

- First player to join via Server Manager claims the server
- Admin password is set during claim
- Anyone with IP + admin password has full server control
- Use strong, unique admin password
- Server state saved in `ServerSettings.<PORT>.sav` (binary format)

---

## 8. Existing Wrapper Tools

### LinuxGSM (sfserver)

**Status:** Fully supported

```bash
# Install
adduser sfserver
su - sfserver
curl -Lo linuxgsm.sh https://linuxgsm.sh && chmod +x linuxgsm.sh && bash linuxgsm.sh sfserver
./sfserver install

# Management commands
./sfserver start
./sfserver stop
./sfserver restart
./sfserver update
./sfserver force-update
./sfserver validate
./sfserver backup
./sfserver details     # Show ports, passwords, config paths
./sfserver monitor     # Health check
./sfserver console     # Live console (CTRL+b d to detach)
./sfserver debug       # Troubleshooting mode
```

**Recommended cron jobs:**
```cron
*/5 * * * *  /home/sfserver/sfserver monitor > /dev/null 2>&1
*/30 * * * * /home/sfserver/sfserver update > /dev/null 2>&1
0 0 * * 0    /home/sfserver/sfserver update-lgsm > /dev/null 2>&1
```

**Supported distros:** Ubuntu 20.04+, Debian 11+, EL 8+ (any with tmux >= 1.6, glibc >= 2.17)

**Known issue:** v1.1 added ReliablePort (8888/TCP) which required LinuxGSM updates.
See: https://github.com/GameServerManagers/LinuxGSM/issues/4812

### Docker — wolveix/satisfactory-server

**Status:** Actively maintained, MIT license

**Docker Hub:** `wolveix/satisfactory-server:latest`
**GitHub:** https://github.com/wolveix/satisfactory-server

#### Docker Compose

```yaml
services:
  satisfactory-server:
    container_name: 'satisfactory-server'
    hostname: 'satisfactory-server'
    image: 'wolveix/satisfactory-server:latest'
    ports:
      - '7777:7777/tcp'
      - '7777:7777/udp'
      - '8888:8888/tcp'
    volumes:
      - './satisfactory-server:/config'
    environment:
      - MAXPLAYERS=4
      - PGID=1000
      - PUID=1000
      - STEAMBETA=false
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
```

#### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAXPLAYERS` | 4 | Player limit |
| `MAXOBJECTS` | 2162688 | Object limit |
| `MAXTICKRATE` | 30 | Server tick rate |
| `AUTOSAVENUM` | 5 | Rotating autosave count |
| `SERVERGAMEPORT` | 7777 | Game port |
| `SERVERMESSAGINGPORT` | 8888 | Reliable messaging port |
| `TIMEOUT` | 30 | Client timeout seconds |
| `STEAMBETA` | false | Use experimental branch |
| `SKIPUPDATE` | false | Skip auto-update on start |
| `PUID` | 1000 | Run-as user ID |
| `PGID` | 1000 | Run-as group ID |
| `MULTIHOME` | (empty) | Bind address |

#### Volume Structure (`/config`)

```
/config/backups/    — Automatic save backups on startup
/config/gamefiles/  — Persistent game files (8GB+)
/config/logs/       — Steam and Satisfactory logs
/config/saved/      — Blueprints, saves, server configuration
```

### Other Docker Images

- `vinanrra/Docker-Satisfactory` — Uses LinuxGSM inside Docker
- Various community forks on Docker Hub

### Community API SDKs

- **Python:** https://github.com/Programmer-Timmy/satisfactory-dedicated-server-api-SDK
- **Various:** Community wrappers for the HTTPS API

---

## 9. Comparison to Palworld / ARK for GameSpec Planning

| Aspect | Palworld | Satisfactory | ARK (arkmanager) |
|--------|----------|--------------|------------------|
| Install | SteamCMD (anon) | SteamCMD (anon) | SteamCMD (anon) |
| App ID | 2394010 | 1690800 | 376030 |
| Binary | PalServer.sh | FactoryServer.sh | ShooterGameServer |
| Config format | INI (UE) | INI (UE) | INI (UE) |
| Ports | 8211 UDP | 7777 UDP+TCP, 8888 TCP | 7777 UDP, 27015 UDP |
| RCON | Yes (25575) | **No** (HTTPS API instead) | Yes (27020) |
| Wrapper tool | None (native) | LinuxGSM (sfserver) | arkmanager |
| Shutdown signal | SIGTERM | **SIGINT** | SIGTERM |
| Auto-save on stop | Yes | **No** | Yes |
| First-run config gen | Yes | Only after graceful stop | Yes |
| Server claim | No | **Yes** (in-game) | No |
| Mods | Limited | Yes (ficsit.app/SMM) | Yes (Steam Workshop) |

### GameSpec Implications

1. **Installation:** Standard SteamCMD pattern (same as Palworld)
2. **Service type:** `Type=simple`, no forking
3. **Shutdown:** Must use `SIGINT` — unique among game servers
4. **No RCON:** Management via HTTPS API (Bearer token auth) — would need custom API client
5. **Save management:** API-driven (`SaveGame`, `DownloadSaveGame`) or manual file copy
6. **Config generation quirk:** Server must start and stop gracefully once before INI files exist
7. **Claim mechanism:** Adds an extra first-run step not present in Palworld/ARK
8. **Port simplicity:** Only 2 ports (7777 UDP+TCP, 8888 TCP) vs ARK's 3-4

---

## 10. Sources

- [Official Satisfactory Wiki — Dedicated Servers](https://satisfactory.wiki.gg/wiki/Dedicated_servers)
- [Official Wiki — Configuration Files](https://satisfactory.wiki.gg/wiki/Dedicated_servers/Configuration_files)
- [Official Wiki — Running as a Service](https://satisfactory.wiki.gg/wiki/Dedicated_servers/Running_as_a_Service)
- [LinuxGSM — Satisfactory Server (sfserver)](https://linuxgsm.com/servers/sfserver/)
- [wolveix/satisfactory-server (Docker)](https://github.com/wolveix/satisfactory-server)
- [wolveix — Official API Docs Wiki](https://github.com/wolveix/satisfactory-server/wiki/Official-API-Docs)
- [LinuxGSM Issue #4812 — ReliablePort](https://github.com/GameServerManagers/LinuxGSM/issues/4812)
- [Satisfactory Modding — Dedicated Server Setup](https://docs.ficsit.app/satisfactory-modding/latest/ForUsers/DedicatedServerSetup.html)
- [Satisfactory Q&A — RCON Request](https://questions.satisfactorygame.com/post/62477ace831c85205236daf9)
- [wolveix/satisfactory-server — Upgrading for 1.1](https://github.com/wolveix/satisfactory-server/wiki/Upgrading-for-1.1)
