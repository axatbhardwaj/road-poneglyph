"""
A simple tool to install and manage a Palworld dedicated server on Linux.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from string import Formatter
from typing import Callable, Optional
import re

import rich
import typer
from rich.console import Console

app = typer.Typer(
    help="logpose — multi-game dedicated server launcher.",
    no_args_is_help=True,
)
console = Console()
STEAM_DIR = Path.home() / ".steam/steam"


@dataclass(frozen=True)
class SettingsAdapter:
    """Per-game settings file I/O. Two callables, no state."""

    parse: Callable[[Path], dict[str, str]]
    save: Callable[[Path, dict[str, str]], None]


@dataclass(frozen=True)
class GameSpec:
    """Frozen per-game configuration. Populated once at module scope in GAMES."""

    key: str
    display_name: str
    app_id: int
    server_dir: Path
    binary_rel_path: str
    settings_path: Path
    default_settings_path: Optional[Path]
    settings_section_rename: Optional[tuple[str, str]]
    service_name: str  # bare name, no ".service" suffix
    service_template_name: str
    settings_adapter: "SettingsAdapter"
    post_install_hooks: list[Callable[[], None]] = field(default_factory=list)
    apt_packages: list[str] = field(default_factory=list)
    steam_sdk_paths: list[tuple[Path, Path]] = field(default_factory=list)
    install_options: dict[str, object] = field(default_factory=dict)


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
        raise typer.Exit(code=1)


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
        raise typer.Exit(code=1)


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


def _run_steamcmd_update(server_dir: Path, app_id: int) -> None:
    """Runs steamcmd to install/update the dedicated server for the given app."""
    _run_command(
        f"steamcmd +force_install_dir '{server_dir}' +login anonymous "
        f"+app_update {app_id} validate +quit"
    )
    server_script = server_dir / "PalServer.sh"
    if server_script.exists():
        _run_command(f"chmod +x {server_script}")


def _fix_steam_sdk(steam_sdk_dst: Path, steam_client_so: Path) -> None:
    """Copy steamclient.so into the game's Steam SDK directory (Palworld: sdk64 only)."""
    console.print("Fixing Steam SDK errors...")
    steam_sdk_dst.mkdir(parents=True, exist_ok=True)
    if steam_client_so.exists():
        _run_command(f"cp {steam_client_so} {steam_sdk_dst}/")
    else:
        rich.print(
            f"Warning: {steam_client_so} not found. This might cause issues.",
            file=sys.stderr,
        )


def _render_service_file(
    service_name: str,
    template_name: str,
    user: str,
    working_directory: Path,
    exec_start_path: Path,
    port: int,
    players: int,
) -> str:
    """Render a systemd unit file from a template. Pure: no I/O side effects."""
    # `service_name` is accepted for signature symmetry with Phase 3 (caller derives
    # the install path from it); the service template itself does not reference it.
    _ = service_name  # silence "unused parameter" linters; kept for Phase 3 shape
    template = _get_template(template_name)
    return template.format(
        user=user,
        port=port,
        players=players,
        exec_start_path=exec_start_path,
        working_directory=working_directory,
    )


def _write_service_file(service_file: Path, content: str) -> None:
    """Write rendered service content to disk via sudo tee and reload systemd."""
    console.print("Creating Pal Server service...")
    _run_command(f"echo '{content}' | sudo tee {service_file}")
    _run_command("sudo systemctl daemon-reload")


def _setup_polkit(user: str) -> None:
    """Allow `user` to control every registered game service without sudo."""
    console.print("Setting up policy for non-sudo control of all registered games...")
    policy_file = Path("/etc/polkit-1/rules.d/40-logpose.rules")
    _run_command(f"sudo mkdir -p {policy_file.parent}")
    units = ", ".join(f'"{spec.service_name}.service"' for spec in GAMES.values())
    template = _get_template("40-logpose.rules.template")
    # Placeholder audit — fails fast if the template drifts
    placeholders = {f[1] for f in Formatter().parse(template) if f[1]}
    if placeholders != {"units", "user"}:
        raise RuntimeError(
            f"40-logpose.rules.template placeholder drift: {placeholders}"
        )
    policy_content = template.format(units=units, user=user)
    _run_command(f"echo '{policy_content}' | sudo tee {policy_file}")
    _run_command("sudo systemctl restart polkit.service")


def _palworld_parse(path: Path) -> dict[str, str]:
    """Parses a Palworld PalWorldSettings.ini file."""
    # verbatim from v0.1.19 — PAL-03 invariant
    content = path.read_text()
    match = re.search(r"OptionSettings=\((.*)\)", content)
    if not match:
        raise ValueError("Could not find OptionSettings in PalWorldSettings.ini")

    settings_str = match.group(1)
    # This regex handles quoted strings and other values
    settings_pairs = re.findall(r'(\w+)=(".*?"|[^,]+)', settings_str)
    return {key: value.strip('"') for key, value in settings_pairs}


def _palworld_save(path: Path, settings: dict[str, str]) -> None:
    """Saves settings back to a Palworld PalWorldSettings.ini file."""
    # verbatim from v0.1.19 — PAL-04 invariant
    content = path.read_text()

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
    path.write_text(new_content)
    console.print("Settings saved successfully.")


def _create_settings_from_default(
    default_path: Path,
    dst_path: Path,
    section_rename: Optional[tuple[str, str]],
) -> None:
    """Create a settings file from a default template, optionally renaming a section header."""
    if not default_path.exists():
        console.print(
            f"Default configuration file not found at {default_path}",
            file=sys.stderr,
        )
        console.print(
            "Cannot create a new settings file. Please run `install` first or run the server once.",
            file=sys.stderr,
        )
        raise typer.Exit(code=1)

    console.print(
        "Configuration file is missing, empty, or corrupted. Creating a new one from default settings."
    )
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    content = default_path.read_text()
    if section_rename is not None:
        # Game-specific behavior: some games need the section header renamed when
        # copying the default template into the saved config. ARK passes None.
        content = content.replace(section_rename[0], section_rename[1])
    dst_path.write_text(content)


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
            raise typer.Exit()

        if choice not in settings:
            console.print(f"[bold red]Invalid setting '{choice}'.[/bold red]")
            continue

        current_value = settings[choice]
        console.print(
            f"Current value for [bold cyan]{choice}[/bold cyan]: {current_value}"
        )
        new_value = typer.prompt("Enter new value")
        settings[choice] = new_value


# --- Palworld post-install hook + GAMES registry (Phase 3 Plan 01) ---
# Module-private helpers bound once at import time. These are NOT the same as
# the existing PAL_SERVER_DIR / PAL_SETTINGS_PATH / DEFAULT_PAL_SETTINGS_PATH
# module globals (those dissolve in Plan 03-02). The underscore prefix signals
# "internal to GAMES construction" — nothing outside this block reads them.
_PAL_SERVER_DIR_LOCAL = STEAM_DIR / "steamapps/common/PalServer"
_PAL_STEAM_CLIENT_SO = STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so"
_PAL_SDK64_DST = Path.home() / ".steam/sdk64"


def _palworld_sdk_hook() -> None:
    """Palworld post-install hook: copy steamclient.so into sdk64 (PAL-08)."""
    _fix_steam_sdk(_PAL_SDK64_DST, _PAL_STEAM_CLIENT_SO)


GAMES: dict[str, GameSpec] = {
    "palworld": GameSpec(
        key="palworld",
        display_name="Palworld",
        app_id=2394010,
        server_dir=_PAL_SERVER_DIR_LOCAL,
        binary_rel_path="PalServer.sh",
        settings_path=_PAL_SERVER_DIR_LOCAL / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini",
        default_settings_path=_PAL_SERVER_DIR_LOCAL / "DefaultPalWorldSettings.ini",
        settings_section_rename=(
            "[/Script/Pal.PalWorldSettings]",
            "[/Script/Pal.PalGameWorldSettings]",
        ),
        service_name="palserver",
        service_template_name="palserver.service.template",
        settings_adapter=SettingsAdapter(parse=_palworld_parse, save=_palworld_save),
        post_install_hooks=[_palworld_sdk_hook],
        apt_packages=[],
        steam_sdk_paths=[(_PAL_STEAM_CLIENT_SO, _PAL_SDK64_DST)],
        install_options={"port_default": 8211, "players_default": 32},
    ),
}


def _build_game_app(spec: GameSpec) -> typer.Typer:
    """Build a Typer sub-app that owns all nine verbs for a single GameSpec.

    Factory pattern (04-RESEARCH Pitfall 1): `spec` is captured as a CLOSURE
    variable; every inner @sub.command body references `spec.*` — never
    `GAMES["palworld"]`, never hardcoded service names. This is what makes
    the sub-apps safe to produce inside an `add_typer` loop over GAMES.
    """
    sub = typer.Typer(
        help=f"Manage {spec.display_name} dedicated server.",
        no_args_is_help=True,
    )
    try:
        port_default = int(spec.install_options["port_default"])
        players_default = int(spec.install_options["players_default"])
    except KeyError as e:
        raise RuntimeError(
            f"GameSpec for {spec.key!r} missing required install_options key: {e}"
        ) from e

    @sub.command()
    def install(
        port: int = typer.Option(port_default, help="Port to run the server on."),
        players: int = typer.Option(players_default, help="Maximum number of players."),
        start: bool = typer.Option(
            False, "--start", help="Start the server immediately after installation."
        ),
    ) -> None:
        """Install the dedicated server and create a systemd service."""
        if Path.home() == Path("/root"):
            rich.print("This script should not be run as root. Exiting.", file=sys.stderr)
            raise typer.Exit(code=1)

        _install_steamcmd()
        _run_steamcmd_update(spec.server_dir, spec.app_id)
        for hook in spec.post_install_hooks:
            hook()
        service_content = _render_service_file(
            service_name=spec.service_name,
            template_name=spec.service_template_name,
            user=Path.home().name,
            working_directory=spec.server_dir,
            exec_start_path=spec.server_dir / spec.binary_rel_path,
            port=port,
            players=players,
        )
        _write_service_file(
            Path(f"/etc/systemd/system/{spec.service_name}.service"), service_content
        )
        _setup_polkit(Path.home().name)

        console.print("Installation complete!")

        if start:
            console.print("Starting the server...")
            _run_command(f"systemctl start {spec.service_name}")
            console.print("Server started successfully!")
        else:
            console.print(
                f"You can now start the server with: logpose {spec.key} start"
            )

        console.print(
            f"To enable the server to start on boot, run: logpose {spec.key} enable"
        )

    @sub.command()
    def start() -> None:
        """Start the dedicated server."""
        _run_command(f"systemctl start {spec.service_name}")

    @sub.command()
    def stop() -> None:
        """Stop the dedicated server."""
        _run_command(f"systemctl stop {spec.service_name}")

    @sub.command()
    def restart() -> None:
        """Restart the dedicated server."""
        _run_command(f"systemctl restart {spec.service_name}")

    @sub.command()
    def status() -> None:
        """Check the status of the dedicated server."""
        _run_command(f"systemctl status {spec.service_name}", check=False)

    @sub.command()
    def enable() -> None:
        """Enable the dedicated server to start on boot."""
        _run_command(f"systemctl enable {spec.service_name}")

    @sub.command()
    def disable() -> None:
        """Disable the dedicated server from starting on boot."""
        _run_command(f"systemctl disable {spec.service_name}")

    @sub.command()
    def update() -> None:
        """Update the dedicated server via steamcmd."""
        console.print(f"Updating {spec.display_name} dedicated server...")
        _run_steamcmd_update(spec.server_dir, spec.app_id)
        console.print("Update complete! Restart the server for the changes to take effect.")

    @sub.command(name="edit-settings")
    def edit_settings() -> None:
        """Edit the game's settings file interactively."""
        try:
            settings = spec.settings_adapter.parse(spec.settings_path)
        except (FileNotFoundError, ValueError):
            _create_settings_from_default(
                spec.default_settings_path,
                spec.settings_path,
                spec.settings_section_rename,
            )
            try:
                settings = spec.settings_adapter.parse(spec.settings_path)
            except (ValueError, FileNotFoundError) as e:
                rich.print(
                    f"An error occurred after creating default settings: {e}",
                    file=sys.stderr,
                )
                raise typer.Exit(code=1)

        try:
            _interactive_edit_loop(settings)
            spec.settings_adapter.save(spec.settings_path, settings)
        except Exception as e:
            rich.print(f"An error occurred during settings edit: {e}", file=sys.stderr)
            raise typer.Exit(code=1)

    return sub


def _version_cb(value: bool) -> None:
    if value:
        import importlib.metadata

        try:
            v = importlib.metadata.version("logpose-launcher")
        except importlib.metadata.PackageNotFoundError:
            v = "unknown"
        typer.echo(f"logpose {v}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        None,
        "--version",
        callback=_version_cb,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """logpose — multi-game dedicated server launcher."""


for _key, _spec in GAMES.items():
    app.add_typer(
        _build_game_app(_spec),
        name=_key,
        help=f"Manage {_spec.display_name}.",
    )


if __name__ == "__main__":
    app()
