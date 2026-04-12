# logpose

A simple command-line tool to help you install, manage, and run a dedicated game server on Linux. `logpose` is a multi-game launcher; in v0.2.0 the Palworld sub-command is the supported target. It automates the setup process — installing dependencies, configuring the server as a systemd service, and setting up permissions for easy management.

## Features

- **Automated Installation**: Installs SteamCMD and the Palworld dedicated server with a single command.
- **Package Manager Repair**: Automatically attempts to fix common `apt` and `dpkg` issues before installation.
- **Service Management**: Creates a `systemd` service to run the server in the background and start it on boot.
- **Permission Handling**: Configures Polkit rules (single merged `40-logpose.rules` covering every registered game) to allow server management (start, stop, restart) without needing `sudo`.
- **Unattended Setup**: Automatically accepts the SteamCMD license agreement for a smoother setup process.

## Prerequisites

- A Debian or Ubuntu Linux distribution.
- `sudo` privileges for the user running the script.

## Installation

```bash
pip install logpose-launcher
```

The PyPI distribution is named `logpose-launcher`; the installed CLI binary is `logpose`.

## Usage

After installation, you can use the `logpose palworld <verb>` command set:

### Install the Server

This command will install the server, configure it with the specified port and player count, and set it up as a systemd service.

```bash
# Install the server with default settings (port 8211, 32 players)
logpose palworld install

# Install with custom settings and start the server immediately
logpose palworld install --port 8211 --players 16 --start
```

### Manage the Server

Once installed, you can control the server state. Thanks to the Polkit setup, you do not need `sudo` for these commands.

```bash
# Start the server
logpose palworld start

# Stop the server
logpose palworld stop

# Restart the server
logpose palworld restart

# Check the server's status
logpose palworld status

# Enable the server to start automatically on boot
logpose palworld enable

# Disable the server from starting on boot
logpose palworld disable

# Update the server
logpose palworld update

# Edit the PalWorldSettings.ini file interactively
logpose palworld edit-settings
```

### Version

```bash
logpose --version
```
