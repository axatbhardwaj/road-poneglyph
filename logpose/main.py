"""
A simple tool to install and manage a Palworld dedicated server on Linux.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional
import re

import rich
import typer
from rich.console import Console

app = typer.Typer()
console = Console()
STEAM_DIR = Path.home() / ".steam/steam"
PAL_SERVER_DIR = STEAM_DIR / "steamapps/common/PalServer"
PAL_SETTINGS_PATH = PAL_SERVER_DIR / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini"
DEFAULT_PAL_SETTINGS_PATH = PAL_SERVER_DIR / "DefaultPalWorldSettings.ini"


def _get_os_id() -> str:
    """Gets the OS ID from /etc/os-release."""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    # Removes quotes if present, e.g., ID="ubuntu"
                    return line.strip().split("=")[1].strip('"')
    except FileNotFoundError:
        rich.print("Could not determine OS from /etc/os-release.", file=sys.stderr)
        return ""
    return ""


def _get_template(name: str) -> str:
    """Reads a template file from the script's directory."""
    template_path = Path(__file__).parent / "templates" / name
    try:
        return template_path.read_text()
    except FileNotFoundError:
        rich.print(
            f"Error: Template file not found at {template_path}", file=sys.stderr
        )
        sys.exit(1)


def _run_command(command: str, check: bool = True) -> None:
    """Runs a command and prints its output in real-time."""
    console.print(f"Executing: [bold cyan]{command}[/bold cyan]")
    try:
        with subprocess.Popen(
            command,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ) as process:
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    rich.print(line, end="")

            return_code = process.wait()

            if check and return_code != 0:
                raise subprocess.CalledProcessError(return_code, command)

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        rich.print(f"\nError executing command: {e}", file=sys.stderr)
        sys.exit(1)


def _repair_package_manager() -> None:
    """Tries to repair the apt/dpkg system."""
    console.print("Attempting to repair package manager...")
    _run_command("sudo pkill -f 'apt|dpkg'", check=False)
    _run_command("sudo rm /var/lib/apt/lists/lock", check=False)
    _run_command("sudo rm /var/cache/apt/archives/lock", check=False)
    _run_command("sudo rm /var/lib/dpkg/lock*", check=False)
    _run_command("sudo rm /var/cache/debconf/*.dat", check=False)
    _run_command("sudo DEBIAN_FRONTEND=noninteractive dpkg --configure -a", check=False)
    _run_command("sudo DEBIAN_FRONTEND=noninteractive apt-get -f install -y")
    _run_command("sudo apt-get autoremove -y", check=False)
    _run_command("sudo apt-get clean")
    _run_command("sudo apt-get update")


def _install_steamcmd() -> None:
    """Install steamcmd if not already installed."""
    _repair_package_manager()
    console.print("Checking for steamcmd...")
    try:
        subprocess.run(
            "command -v steamcmd", check=True, shell=True, capture_output=True
        )
        console.print("steamcmd is already installed.")
    except subprocess.CalledProcessError:
        console.print("steamcmd not found. Installing steamcmd...")
        _run_command(
            "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y software-properties-common"
        )
        _run_command("sudo add-apt-repository multiverse -y")
        _run_command("sudo dpkg --add-architecture i386")

        # Pre-accept the license agreement for steamcmd (must be before update/install)
        _run_command(
            "echo 'steam steam/question select I AGREE' | sudo debconf-set-selections"
        )
        _run_command("echo 'steam steam/license note' | sudo debconf-set-selections")
        _run_command(
            "echo 'steamcmd steamcmd/question select I AGREE' | sudo debconf-set-selections"
        )
        _run_command(
            "echo 'steamcmd steamcmd/license note' | sudo debconf-set-selections"
        )

        _run_command("sudo apt-get update")

        # Try to install steamcmd with additional license acceptance
        _run_command("sudo DEBIAN_FRONTEND=noninteractive apt-get install -y steamcmd")

        # If the above fails, try an alternative approach
        _run_command("sudo dpkg-reconfigure -fnoninteractive steamcmd", check=False)


def _run_steamcmd_update():
    """Runs steamcmd to install/update Palworld server."""
    _run_command(f"steamcmd +force_install_dir '{PAL_SERVER_DIR}' +login anonymous +app_update 2394010 validate +quit")
    pal_server_script = PAL_SERVER_DIR / "PalServer.sh"
    if pal_server_script.exists():
        _run_command(f"chmod +x {pal_server_script}")


def _install_palworld() -> None:
    """Install Palworld dedicated server using steamcmd."""
    console.print("Installing Palworld dedicated server...")
    _run_steamcmd_update()


def _fix_steam_sdk() -> None:
    """Fix Steam SDK errors."""
    console.print("Fixing Steam SDK errors...")
    steam_sdk_path = Path.home() / ".steam/sdk64"
    steam_sdk_path.mkdir(parents=True, exist_ok=True)
    steam_client_so = (
        STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"
    )
    if steam_client_so.exists():
        _run_command(f"cp {steam_client_so} {steam_sdk_path}/")
    else:
        rich.print(
            f"Warning: {steam_client_so} not found. This might cause issues.",
            file=sys.stderr,
        )


def _create_service_file(port: int, players: int) -> None:
    """Create a systemd service for the Pal Server."""
    console.print("Creating Pal Server service...")
    user = Path.home().name
    service_file = Path("/etc/systemd/system/palserver.service")
    template = _get_template("palserver.service.template")
    pal_server_dir = STEAM_DIR / "steamapps/common/PalServer"
    exec_start_path = pal_server_dir / "PalServer.sh"
    service_content = template.format(
        user=user,
        port=port,
        players=players,
        exec_start_path=exec_start_path,
        working_directory=pal_server_dir,
    )
    _run_command(f"echo '{service_content}' | sudo tee {service_file}")
    _run_command("sudo systemctl daemon-reload")


def _setup_polkit() -> None:
    """Allow user to control the service without sudo."""
    console.print("Setting up policy for non-sudo control...")
    user = Path.home().name
    policy_file = Path("/etc/polkit-1/rules.d/40-palserver.rules")
    _run_command(f"sudo mkdir -p {policy_file.parent}")
    template = _get_template("palserver.rules.template")
    policy_content = template.format(user=user)
    _run_command(f"echo '{policy_content}' | sudo tee {policy_file}")
    _run_command("sudo systemctl restart polkit.service")


def _parse_settings() -> dict[str, str]:
    """Parses the PalWorldSettings.ini file."""
    content = PAL_SETTINGS_PATH.read_text()
    match = re.search(r"OptionSettings=\((.*)\)", content)
    if not match:
        raise ValueError("Could not find OptionSettings in PalWorldSettings.ini")

    settings_str = match.group(1)
    # This regex handles quoted strings and other values
    settings_pairs = re.findall(r'(\w+)=(".*?"|[^,]+)', settings_str)
    return {key: value.strip('"') for key, value in settings_pairs}


def _save_settings(settings: dict[str, str]) -> None:
    """Saves the settings back to PalWorldSettings.ini."""
    content = PAL_SETTINGS_PATH.read_text()

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
    PAL_SETTINGS_PATH.write_text(new_content)
    console.print("Settings saved successfully.")


def _create_settings_from_default() -> None:
    """Creates PalWorldSettings.ini from the default template."""
    if not DEFAULT_PAL_SETTINGS_PATH.exists():
        console.print(
            f"Default configuration file not found at {DEFAULT_PAL_SETTINGS_PATH}",
            file=sys.stderr,
        )
        console.print(
            "Cannot create a new settings file. Please run `install` first or run the server once.",
            file=sys.stderr,
        )
        sys.exit(1)

    console.print(
        "Configuration file is missing, empty, or corrupted. Creating a new one from default settings."
    )
    PAL_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = DEFAULT_PAL_SETTINGS_PATH.read_text()
    # The game uses PalGameWorldSettings in the saved config, so we replace the section header
    content = content.replace(
        "[/Script/Pal.PalWorldSettings]",
        "[/Script/Pal.PalGameWorldSettings]",
    )
    PAL_SETTINGS_PATH.write_text(content)


def _display_settings(settings: dict[str, str]) -> None:
    """Displays the settings in a table."""
    table = rich.table.Table(
        title="Palworld Server Settings", show_header=True, header_style="bold magenta"
    )
    table.add_column("Setting", style="dim", width=40)
    table.add_column("Value")

    for key, value in settings.items():
        table.add_row(key, str(value))

    console.print(table)


def _interactive_edit_loop(settings: dict[str, str]) -> None:
    """Displays settings and allows interactive editing."""
    while True:
        _display_settings(settings)
        console.print(
            "\nEnter the name of the setting to edit, or type [bold green]save[/bold green] to finish, or [bold red]quit[/bold red] to exit without saving."
        )
        choice = typer.prompt("Setting to edit").strip()

        if choice.lower() == "save":
            break
        if choice.lower() == "quit":
            console.print("Exiting without saving.")
            sys.exit(0)

        if choice not in settings:
            console.print(f"[bold red]Invalid setting '{choice}'.[/bold red]")
            continue

        current_value = settings[choice]
        console.print(
            f"Current value for [bold cyan]{choice}[/bold cyan]: {current_value}"
        )
        new_value = typer.prompt("Enter new value")
        settings[choice] = new_value


@app.command()
def install(
    port: int = typer.Option(8211, help="Port to run the server on."),
    players: int = typer.Option(32, help="Maximum number of players."),
    start: bool = typer.Option(
        False, "--start", help="Start the server immediately after installation."
    ),
) -> None:
    """Install the Palworld dedicated server and create a systemd service."""
    if Path.home() == Path("/root"):
        rich.print("This script should not be run as root. Exiting.", file=sys.stderr)
        sys.exit(1)

    _install_steamcmd()
    _install_palworld()
    _fix_steam_sdk()
    _create_service_file(port, players)
    _setup_polkit()

    console.print("Installation complete!")

    if start:
        console.print("Starting the server...")
        _run_command("systemctl start palserver")
        console.print("Server started successfully!")
    else:
        console.print(
            "You can now start the server with: palworld-server-launcher start"
        )

    console.print(
        "To enable the server to start on boot, run: palworld-server-launcher enable"
    )


@app.command()
def start() -> None:
    """Start the Palworld server."""
    _run_command("systemctl start palserver")


@app.command()
def stop() -> None:
    """Stop the Palworld server."""
    _run_command("systemctl stop palserver")


@app.command()
def restart() -> None:
    """Restart the Palworld server."""
    _run_command("systemctl restart palserver")


@app.command()
def status() -> None:
    """Check the status of the Palworld server."""
    _run_command("systemctl status palserver", check=False)


@app.command()
def enable() -> None:
    """Enable the Palworld server to start on boot."""
    _run_command("systemctl enable palserver")


@app.command()
def disable() -> None:
    """Disable the Palworld server from starting on boot."""
    _run_command("systemctl disable palserver")


@app.command()
def update() -> None:
    """Update the Palworld dedicated server."""
    console.print("Updating Palworld dedicated server...")
    _run_steamcmd_update()
    console.print("Update complete! Restart the server for the changes to take effect.")


@app.command(name="edit-settings")
def edit_settings() -> None:
    """Edit the PalWorldSettings.ini file."""
    try:
        settings = _parse_settings()
    except (FileNotFoundError, ValueError):
        _create_settings_from_default()
        try:
            settings = _parse_settings()
        except (ValueError, FileNotFoundError) as e:
            rich.print(
                f"An error occurred after creating default settings: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        _interactive_edit_loop(settings)
        _save_settings(settings)
    except Exception as e:
        rich.print(f"An error occurred during settings edit: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    app()
