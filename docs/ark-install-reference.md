# ARK Dedicated Server Install — Session Record

Install performed on **2026-04-12** on this host. This document captures every step taken, every deviation from the source guide, and enough detail to reproduce or reverse the install.

---

## 1. Host profile

| Item | Value |
|---|---|
| OS | Debian GNU/Linux 13 (trixie) |
| Kernel | Linux 6.12.57+deb13-amd64 |
| Arch | amd64 (+ i386 foreign arch added) |
| CPU | 8 cores |
| RAM | 15 GiB total, no swap |
| Disk | /dev/vda4 — 503 GB, 28 GB used before install |
| User | root (uid 0, also in docker group) |
| Hostname | v2202512319819411995 |
| Public IP | 159.195.60.199 |

**Existing services on the box (not touched):** caddy, docker, grafana, node (nodesource), azure-cli, and an unknown listener on tcp/3456. UFW was already active with rules for 22, 80, 443, 3456.

Two pre-existing apt repository signing-key issues were noted and **not fixed** (user asked to leave other apps alone):
- `dl.cloudsmith.io/public/caddy/stable` — subkey expired 2025-12-28.
- `deb.nodesource.com/node_24.x` — SHA1 signature no longer accepted by Debian sqv policy (effective 2026-02-01).

These only produce warnings during `apt update`; the caddy/node packages themselves still work from their previously cached indexes.

---

## 2. Decisions made (diverging from the pasted guide)

The guide was written for Ubuntu on a clean VPS. This box is Debian 13 and already runs other services, so the install was deliberately de-scoped:

| Guide step | Action taken | Reason |
|---|---|---|
| `add-apt-repository multiverse` | Added `contrib non-free` to `/etc/apt/sources.list` instead | `multiverse` is Ubuntu-only; Debian equivalent is `contrib`/`non-free` |
| `sysctl fs.file-max=100000` | **Skipped** | System-wide kernel tunable, already high by default on modern kernels, would persist in `/etc/sysctl.conf` and affect all services |
| `limits.conf` soft/hard nofile | **Skipped** | Global change affecting every user/session; use per-service systemd `LimitNOFILE` if needed |
| `pam_limits.so` in common-session | **Skipped** | Same — global PAM change |
| Method 1 (raw SteamCMD + systemd) | **Skipped** | User chose Method 2 (arkmanager) |
| Fjordur map | **TheIsland** instead | Lower RAM ceiling (~6–8 GB vs 10–12 GB) — necessary given co-resident services |
| Mods | **None** | User choice |
| Example Python panel bugs | **Rewritten** | Original had missing `@` on `@app.route`/`@requires_auth` decorators, `requires_auth` was defined but never applied, and JS template literal escaping produced literal `\n` instead of newlines |

---

## 3. Final configuration

| Setting | Value |
|---|---|
| Map | TheIsland |
| Session name | `bunty's game` |
| Max players | 10 |
| Admin password | `33-22-11-00` |
| Server password | *(empty — public)* |
| Game port | 7777/udp |
| Raw socket | 7778/udp |
| Query port | 27015/udp |
| RCON | 27020/tcp (enabled) |
| Branch | `preaquatica` (Aquatica beta opt-out — needed for Linux mod support) |
| Web panel | bunty / bunty@332211 on tcp/5000 |
| Service user | `steam` (uid 1000, home `/home/steam`) |

---

## 4. Execution log (step by step)

### 4.1 Enable contrib/non-free and i386 arch

```bash
sed -i 's|trixie main non-free-firmware|trixie main contrib non-free non-free-firmware|' /etc/apt/sources.list
sed -i 's|trixie-security main non-free-firmware|trixie-security main contrib non-free non-free-firmware|' /etc/apt/sources.list
sed -i 's|trixie-updates main non-free-firmware|trixie-updates main contrib non-free non-free-firmware|' /etc/apt/sources.list
dpkg --add-architecture i386
apt-get update
```

### 4.2 Pre-accept Steam license (non-interactive)

```bash
echo steam steam/question select "I AGREE" | debconf-set-selections
echo steam steam/license note '' | debconf-set-selections
echo steamcmd steam/question select "I AGREE" | debconf-set-selections
echo steamcmd steam/license note '' | debconf-set-selections
```

### 4.3 Install prerequisites + steamcmd

```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    perl-modules curl lsof libc6-i386 lib32gcc-s1 lib32stdc++6 \
    bzip2 tar rsync sed python3-flask python3-psutil steamcmd
```

Result: `steamcmd` at `/usr/games/steamcmd` (Debian package, i386 binary).

### 4.4 Create steam user

```bash
useradd -m -s /bin/bash steam
# Home: /home/steam   uid: 1000   gid: 1000
```

No password was set — the account is only used via `sudo -u steam` from root.

### 4.5 Install arkmanager

```bash
curl -sL https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/netinstall.sh \
    | bash -s steam
# v1.6.68 installed
```

This placed:
- `/usr/local/bin/arkmanager`
- `/usr/local/libexec/arkmanager/`
- `/usr/local/share/arkmanager/`
- `/etc/arkmanager/arkmanager.cfg`
- `/etc/arkmanager/instances/main.cfg`

### 4.6 Point arkmanager at the system steamcmd

`/etc/arkmanager/arkmanager.cfg` was edited (in place, other keys untouched):

```bash
steamcmdroot="/usr/games"
steamcmdexec="steamcmd"
steamcmd_appinfocache="/home/steam/.steam/appcache/appinfo.vdf"
steamcmd_workshoplog="/home/steam/.steam/logs/workshop_log.txt"
steamcmd_user="steam"   # unchanged, already correct
```

### 4.7 Instance config — `/etc/arkmanager/instances/main.cfg`

Relevant non-default keys:

```ini
arkserverroot="/home/steam/ARK"
serverMap="TheIsland"
ark_RCONEnabled="True"
ark_RCONPort="27020"
ark_SessionName="bunty's game"
ark_Port="7778"
ark_QueryPort="27015"
ark_ServerPassword=""
ark_ServerAdminPassword="33-22-11-00"
ark_MaxPlayers="10"
ark_ShowFloatingDamageText="true"
```

All other keys in the example file were left commented/at defaults.

### 4.8 Firewall rules (UFW — additive, existing rules untouched)

```bash
ufw allow 7777/udp  comment 'ARK game'
ufw allow 7778/udp  comment 'ARK raw socket'
ufw allow 27015/udp comment 'ARK query'
ufw allow 27020/tcp comment 'ARK RCON'
ufw allow 5000/tcp  comment 'ARK web panel'
```

Pre-existing rules (22/80/443/3456) were preserved.

### 4.9 Download server files (preaquatica beta)

```bash
sudo -u steam arkmanager install --beta=preaquatica --validate
```

**Gotcha hit:** the first invocation returned exit 0 after ~15 seconds with only `Restarting steamcmd by request...` in the log. This is a known steamcmd quirk — the first run self-updates and bails, returning success without downloading anything. **Always re-run once after the initial self-update.**

The second invocation downloaded the full payload:
- Final install size: **18 GB** at `/home/steam/ARK/`
- Binary path: `/home/steam/ARK/ShooterGame/Binaries/Linux/ShooterGameServer`
- App ID: 376030, branch preaquatica, build 13834083, version 358.24

### 4.10 Start the server

```bash
sudo -u steam arkmanager start
```

Resolved command line (from `ps`):

```
ShooterGameServer TheIsland?RCONEnabled=True?RCONPort=27020?SessionName=bunty's game
?Port=7778?QueryPort=27015?ServerPassword?ServerAdminPassword=33-22-11-00
?MaxPlayers=10?ShowFloatingDamageText=true?ServerPassword?listen
```

`arkmanager status` immediately after:

```
Server running:    Yes
Server PID:        2961585
Server listening:  No          # normal — first map load takes 5–10 min
Server branch:     preaquatica
Server version:    358.24
```

RAM after start: 9.5 GB / 15.6 GB used (~63%).

The benign log line `[S_API FAIL] SteamAPI_Init() failed; SteamAPI_IsSteamRunning() failed` is expected on a dedicated server (no Steam client running) and can be ignored.

---

## 5. Web panel

### 5.1 Script — `/root/ark_panel.py`

Rewrite of the guide's script with bugs fixed:
- Added missing `@app.route(...)` and `@requires_auth` decorators.
- Applied auth to **every** route (guide's version left them all public despite defining the decorator).
- Replaced the "RAM > 6 GB ⇒ server running" heuristic with a real process check (`psutil.process_iter` looking for `ShooterGameServer`).
- Fixed JavaScript escape sequences in the template literals.
- Used `functools.wraps` so Flask's endpoint names stay unique.

Key config block at the top:

```python
USERNAME = 'bunty'
PASSWORD = 'bunty@332211'
PORT     = 5000
SAVE_DIR = '/home/steam/ARK/ShooterGame/Saved/SavedArks/'
```

Endpoints:

| Path | Method | Purpose |
|---|---|---|
| `/` | GET | HTML UI |
| `/stats` | GET | JSON: total/used RAM, `ark_running` bool |
| `/files` | GET | JSON: savegame listing, newest first |
| `/download/<name>` | GET | Download a savegame file |
| `/run/<cmd>` | POST | Run one of `start` / `stop` / `restart` / `saveworld` via `sudo -u steam arkmanager` |

All routes require HTTP Basic auth.

### 5.2 Systemd unit — `/etc/systemd/system/ark-panel.service`

```ini
[Unit]
Description=ARK Web Panel
After=network.target

[Service]
User=root
WorkingDirectory=/root
ExecStart=/usr/bin/python3 /root/ark_panel.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enabled and started:

```bash
systemctl daemon-reload
systemctl enable --now ark-panel
```

Verification:

```
GET  /          no-auth → 401
GET  /          auth     → 200
GET  /stats     auth     → {"ark_running":true,"percent":63.3,
                            "total_gb":15.62,"used_gb":9.47}
```

---

## 6. File map

| Path | Purpose |
|---|---|
| `/home/steam/ARK/` | Server root (18 GB) |
| `/home/steam/ARK/ShooterGame/Binaries/Linux/ShooterGameServer` | Server executable |
| `/home/steam/ARK/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini` | Runtime game settings (rates, PvE flags, …) |
| `/home/steam/ARK/ShooterGame/Saved/Config/LinuxServer/Game.ini` | Deeper tuning (engrams, dino spawns) |
| `/home/steam/ARK/ShooterGame/Saved/SavedArks/` | Savegame `.ark` files (served by panel) |
| `/home/steam/ARK/ShooterGame/Saved/Logs/` | Server logs |
| `/home/steam/ARK-Backups/` | arkmanager backup target |
| `/etc/arkmanager/arkmanager.cfg` | Global arkmanager config |
| `/etc/arkmanager/instances/main.cfg` | Default instance config |
| `/usr/games/steamcmd` | steamcmd wrapper script |
| `/root/ark_panel.py` | Web panel source |
| `/etc/systemd/system/ark-panel.service` | Panel systemd unit |
| `/tmp/ark-install.log` | Output of the install commands (can be deleted) |

---

## 7. Operating the server

All arkmanager subcommands run as the `steam` user. From root:

```bash
sudo -u steam arkmanager start       # start
sudo -u steam arkmanager stop        # graceful stop with save
sudo -u steam arkmanager restart     # stop + start
sudo -u steam arkmanager status      # pid, listening, branch, version
sudo -u steam arkmanager saveworld   # force world save via RCON
sudo -u steam arkmanager backup      # tar current save into /home/steam/ARK-Backups
sudo -u steam arkmanager update --validate --beta=preaquatica   # pull patches
sudo -u steam arkmanager rconcmd "broadcast Hello"              # send RCON command
```

Web panel: `http://159.195.60.199:5000` → login `bunty` / `bunty@332211`.

Panel service:

```bash
systemctl status  ark-panel
systemctl restart ark-panel
systemctl stop    ark-panel
journalctl -u ark-panel -f
```

---

## 8. Things explicitly **not** done

- No auto-start at boot for the ARK server itself. If the box reboots, the panel comes back up but the game server stays down until `arkmanager start` is run (or the panel's Start button is used). A systemd unit can be added on request.
- No `sysctl` / `limits.conf` / PAM edits. If large player counts or heavy modding are added later, `LimitNOFILE=100000` can be added to a future ark systemd unit without touching global config.
- No Caddy reverse proxy for the panel (see §9).
- No mods. Adding mods later: set `ark_GameModIds="id1,id2,…"` in `main.cfg`, then `sudo -u steam arkmanager installmods && sudo -u steam arkmanager restart`.
- No scheduled backups. Recommend a cron entry like `0 */6 * * * /usr/bin/sudo -u steam /usr/local/bin/arkmanager backup`.
- No changes to `GameUserSettings.ini` / `Game.ini` — left at ARK's own defaults.

---

## 9. Security notes

- **Panel is plain HTTP.** HTTP Basic auth sends `bunty:bunty@332211` as base64 on every request. Anyone sniffing traffic on any network hop can read it trivially. Acceptable for a personal hobby server but not great. Two reasonable upgrades:
  1. Put the panel behind the existing Caddy reverse proxy with HTTPS (auto-TLS via Let's Encrypt) on a hostname you own, keeping the Flask process bound to `127.0.0.1` and closing `ufw deny 5000/tcp`.
  2. Keep 5000 closed at the firewall and reach the panel through an SSH tunnel: `ssh -L 5000:127.0.0.1:5000 root@159.195.60.199`, then hit `http://localhost:5000` in a browser.
- **Admin password `33-22-11-00` is low-entropy** (8 digits + dashes). Anyone who guesses it or recovers it from a log has full RCON. Rotate if the server is public-facing.
- **Flask dev server** is in use (noted in the systemd journal). Fine for a single-user admin panel but not for anything production-scale. If migrating, wrap with gunicorn/uwsgi.
- The panel runs as **root** so it can `sudo -u steam` without a password. Anyone who can authenticate to the panel can stop/start arkmanager, but cannot directly execute arbitrary commands — `run_cmd` uses a fixed allowlist of four subcommands.

---

## 10. Reversal / uninstall checklist

If this install needs to be removed cleanly:

```bash
# Stop everything
systemctl disable --now ark-panel
sudo -u steam arkmanager stop

# Remove ark files and user
rm -rf /home/steam/ARK /home/steam/ARK-Backups /home/steam/.steam /home/steam/Steam
userdel -r steam

# Remove arkmanager
rm -rf /etc/arkmanager /usr/local/bin/arkmanager \
       /usr/local/libexec/arkmanager /usr/local/share/arkmanager

# Remove panel
rm /root/ark_panel.py /etc/systemd/system/ark-panel.service
systemctl daemon-reload

# Remove firewall rules
for port in 7777/udp 7778/udp 27015/udp 27020/tcp 5000/tcp; do
    ufw delete allow "$port"
done

# Optional: remove steamcmd and i386 arch
apt-get purge -y steamcmd
dpkg --remove-architecture i386   # only if nothing else needs it
apt-get autoremove -y

# Optional: revert sources.list to main non-free-firmware only
# (only if you don't want contrib/non-free for other reasons)
```

The global system changes were limited to:
- apt sources (`contrib non-free` added)
- foreign architecture (`i386` added)
- four apt packages actually needed (`steamcmd`, `python3-flask`, `python3-psutil`, i386 runtime libs)

Nothing outside those categories was modified.
