"""
A simple tool to install and manage a Palworld dedicated server on Linux.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from string import Formatter
from typing import Callable, Iterable, Optional
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


def _write_via_sudo_tee(path: Path, content: str) -> None:
    """Pipe `content` to `sudo tee {path}` via stdin (no shell interpolation)."""
    console.print(f"Writing {path} via sudo tee...")
    proc = subprocess.run(
        ["sudo", "tee", str(path)],
        input=content,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        rich.print(f"sudo tee failed: {proc.stderr}", file=sys.stderr)
        raise typer.Exit(code=1)


def _write_service_file(service_file: Path, content: str) -> None:
    """Write rendered service content to disk via sudo tee and reload systemd."""
    console.print("Creating Pal Server service...")
    _write_via_sudo_tee(service_file, content)
    _run_command("sudo systemctl daemon-reload")


def _setup_polkit(user: str, specs: Iterable[GameSpec]) -> None:
    """Allow `user` to control every registered game service without sudo."""
    console.print("Setting up policy for non-sudo control of all registered games...")
    policy_file = Path("/etc/polkit-1/rules.d/40-logpose.rules")
    _run_command(f"sudo mkdir -p {policy_file.parent}")
    units = ", ".join(f'"{spec.service_name}.service"' for spec in specs)
    template = _get_template("40-logpose.rules.template")
    # Placeholder audit — fails fast if the template drifts
    placeholders = {f[1] for f in Formatter().parse(template) if f[1]}
    if placeholders != {"units", "user"}:
        raise RuntimeError(
            f"40-logpose.rules.template placeholder drift: {placeholders}"
        )
    policy_content = template.format(units=units, user=user)
    _write_via_sudo_tee(policy_file, policy_content)
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


# --- arkmanager adapter (ARK-08 + ARK-09 + SET-02) -------------------------
# main.cfg is sourced bash, NOT INI. ConfigParser would mangle it (no [section]
# headers, bash-style key="value" assignments). Regex line editor preserves
# comments, blank lines, and unrelated keys in place.

_ARKMANAGER_LINE_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?(.*?)"?\s*$')


def _ark_should_quote(value: str) -> bool:
    """Quote unless value is True/False/numeric — mirrors Palworld should_quote."""
    if value.lower() in ("true", "false"):
        return False
    try:
        float(value)
        return False
    except ValueError:
        return True


def _arkmanager_parse(path: Path) -> dict[str, str]:
    """Parse arkmanager main.cfg (sourced bash key=\"value\"). Ignores comments + blanks."""
    settings: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _ARKMANAGER_LINE_RE.match(line)
        if m:
            settings[m.group(1)] = m.group(2)
    return settings


def _arkmanager_save(path: Path, settings: dict[str, str]) -> None:
    """Rewrite main.cfg in place: preserve all lines; mutate matching key= lines.

    ARK-09: original line order + comments + unrelated keys untouched.
    New keys (not present in file) appended at end in insertion order.
    """
    lines = path.read_text().splitlines(keepends=True)
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line.lstrip().startswith("#"):
            out.append(line)
            continue
        m = _ARKMANAGER_LINE_RE.match(line)
        if m and m.group(1) in settings:
            key = m.group(1)
            value = settings[key]
            # Preserve quoting style of the original line when possible.
            rhs = line.split("=", 1)[1] if "=" in line else ""
            original_quoted = '"' in rhs
            trailing_newline = "\n" if line.endswith("\n") else ""
            if original_quoted or _ark_should_quote(value):
                out.append(f'{key}="{value}"{trailing_newline}')
            else:
                out.append(f"{key}={value}{trailing_newline}")
            seen.add(key)
        else:
            out.append(line)
    # Append keys not present in original — install-time seed for fresh main.cfg.
    for key, value in settings.items():
        if key in seen:
            continue
        if _ark_should_quote(value):
            out.append(f'{key}="{value}"\n')
        else:
            out.append(f"{key}={value}\n")
    path.write_text("".join(out))


# --- ARK install scaffolding (ARK-11 + ARK-14..ARK-18) ----------------------
# Composes docs/ark-install-reference.md §4.1-4.9 as Python helpers. Does NOT
# render arkserver.service (opt-in; see Plan 05-02) and does NOT start the
# server (caller's --start flag).

_ARK_INSTANCE_CFG = Path("/etc/arkmanager/instances/main.cfg")
_ARK_GLOBAL_CFG = Path("/etc/arkmanager/arkmanager.cfg")
_ARK_APT_PACKAGES = (
    "steamcmd libc6-i386 lib32gcc-s1 lib32stdc++6 curl bzip2 tar rsync sed "
    "perl-modules lsof"
)


def _get_os_version_codename() -> str:
    """Reads VERSION_CODENAME= from /etc/os-release. Empty string on failure."""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("VERSION_CODENAME="):
                    return line.strip().split("=", 1)[1].strip('"')
    except FileNotFoundError:
        pass
    return ""


def _enable_debian_contrib_nonfree(codename: str) -> None:
    """Rewrite /etc/apt/sources.list to include contrib non-free (Debian only).

    Install record §4.1: three sed commands targeting main, main-security,
    main-updates. Idempotent — re-runs are no-ops because the replacement
    pattern won't match after first run.
    """
    if not codename:
        rich.print(
            "Warning: VERSION_CODENAME unknown; skipping contrib/non-free enable.",
            file=sys.stderr,
        )
        return
    for suffix in ("", "-security", "-updates"):
        _run_command(
            f"sudo sed -i 's|{codename}{suffix} main non-free-firmware|"
            f"{codename}{suffix} main contrib non-free non-free-firmware|' "
            f"/etc/apt/sources.list",
            check=False,
        )
    _run_command("sudo dpkg --add-architecture i386")
    _run_command("sudo apt-get update")


def _accept_steam_eula() -> None:
    """Pre-accept Steam EULA via debconf — mandatory before apt install steamcmd.

    Install record §4.2 (ARK-15). Must run before `apt-get install steamcmd`
    otherwise apt blocks on a TUI dialog.
    """
    for pkg in ("steam", "steamcmd"):
        _run_command(
            f"echo '{pkg} steam/question select I AGREE' | sudo debconf-set-selections"
        )
        _run_command(
            f"echo '{pkg} steam/license note' | sudo debconf-set-selections"
        )


def _ensure_steam_user() -> None:
    """Create `steam` service user if absent. ARK-16 — install record §4.4.

    arkmanager's install.sh does NOT create the user; it validates via
    getent and exits non-zero if missing.
    """
    result = subprocess.run(
        ["getent", "passwd", "steam"], capture_output=True, check=False
    )
    if result.returncode == 0:
        console.print("steam user already exists; skipping useradd.")
        return
    _run_command("sudo useradd -m -s /bin/bash steam")


def _install_arkmanager_if_absent() -> None:
    """Install arkmanager via upstream netinstall.sh. ARK-14 — install record §4.5.

    Idempotent — skips if /usr/local/bin/arkmanager already exists.
    """
    if Path("/usr/local/bin/arkmanager").exists():
        console.print("arkmanager already installed; skipping netinstall.")
        return
    _run_command(
        "curl -sL https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/"
        "netinstall.sh | sudo bash -s steam"
    )


def _arkmanager_install_validate(branch: str) -> None:
    """Run arkmanager install --validate TWICE. ARK-17 — install record §4.9.

    First call self-updates steamcmd and exits 0 with no payload (known quirk).
    Second call downloads the actual server files.
    """
    cmd = (
        f"sudo -u steam /usr/local/bin/arkmanager install "
        f"--beta={branch} --validate"
    )
    _run_command(cmd, check=False)  # first call: self-update, exit 0, no payload
    _run_command(cmd)                # second call: actual download


def _install_sudoers_fragment(user: str) -> None:
    """Install /etc/sudoers.d/logpose-ark with NOPASSWD for arkmanager. ARK-18.

    MUST validate via `visudo -c -f` before atomic install — a bad sudoers
    fragment locks out ALL sudo (Pitfall 2).
    """
    template = _get_template("logpose-ark.sudoers.template")
    content = template.format(user=user)
    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sudoers") as tf:
        tf.write(content)
        tmppath = tf.name
    try:
        result = subprocess.run(
            ["sudo", "visudo", "-c", "-f", tmppath],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            rich.print(
                f"sudoers validation FAILED — refusing to install. stderr:\n{result.stderr}",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        _run_command(
            f"sudo install -m 0440 -o root -g root {tmppath} "
            f"/etc/sudoers.d/logpose-ark"
        )
    finally:
        _run_command(f"rm -f {tmppath}", check=False)


def _seed_ark_main_cfg(values: dict[str, str]) -> None:
    """Seed /etc/arkmanager/instances/main.cfg with the 10 install-flag keys. ARK-10.

    Also edits /etc/arkmanager/arkmanager.cfg to point at system steamcmd
    (install record §4.6). After write, tightens perms (Pitfall 5 — admin
    password must not be world-readable).
    """
    _arkmanager_save(_ARK_INSTANCE_CFG, values)
    _arkmanager_save(
        _ARK_GLOBAL_CFG,
        {"steamcmdroot": "/usr/games", "steamcmdexec": "steamcmd"},
    )
    _run_command(f"sudo chmod 0640 {_ARK_INSTANCE_CFG}")
    _run_command(f"sudo chgrp steam {_ARK_INSTANCE_CFG}")


def _install_ark(
    *,
    branch: str,
    main_cfg_values: dict[str, str],
    invoking_user: str,
) -> None:
    """Compose install record §4.1-4.9 as a single idempotent helper.

    Does NOT render arkserver.service (opt-in — handled by caller via
    --enable-autostart). Does NOT start the server (caller's --start flag).
    Does NOT re-run polkit setup (caller does that after GAMES-aware
    _setup_polkit invocation).
    """
    _repair_package_manager()
    os_id = _get_os_id()
    if os_id == "debian":
        codename = _get_os_version_codename()
        _enable_debian_contrib_nonfree(codename)
    else:
        # Ubuntu path — reuse the existing multiverse + i386 setup pattern.
        _run_command("sudo add-apt-repository multiverse -y", check=False)
        _run_command("sudo dpkg --add-architecture i386")
        _run_command("sudo apt-get update")
    _accept_steam_eula()
    _run_command(
        f"sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "
        f"--no-install-recommends {_ARK_APT_PACKAGES}"
    )
    _ensure_steam_user()
    _install_arkmanager_if_absent()
    _seed_ark_main_cfg(main_cfg_values)
    _install_sudoers_fragment(invoking_user)
    _arkmanager_install_validate(branch)


# --- ARK CLI-boundary validation helpers (ARK-06 + ARK-07 + ARK-04) --------
_ARK_SUPPORTED_MAPS: tuple[str, ...] = (
    "TheIsland",
    "TheCenter",
    "ScorchedEarth_P",
    "Aberration_P",
    "Extinction",
    "Ragnarok",
    "Valguero_P",
    "CrystalIsles",
    "LostIsland",
    "Fjordur",
    "Genesis",
    "Genesis2",
)
_ARK_FORBIDDEN_SESSION_CHARS = ('"', "$", "`", "\\")


def _validate_ark_map(value: str) -> str:
    """Typer callback — rejects unsupported maps. ARK-06."""
    if value not in _ARK_SUPPORTED_MAPS:
        raise typer.BadParameter(
            f"Invalid map '{value}'. Supported: {', '.join(_ARK_SUPPORTED_MAPS)}"
        )
    return value


def _validate_ark_session_name(name: str) -> str:
    """Typer callback — rejects unsafe chars; warns on >63 chars. ARK-04."""
    for bad in _ARK_FORBIDDEN_SESSION_CHARS:
        if bad in name:
            raise typer.BadParameter(
                f"Session name contains unsupported character {bad!r}. "
                f"Avoid: {' '.join(_ARK_FORBIDDEN_SESSION_CHARS)}"
            )
    if len(name) > 63:
        console.print(
            f"[yellow]Warning: session name is {len(name)} chars (>63); some "
            f"clients may truncate.[/yellow]"
        )
    return name


def _probe_port_collision(ports: list[tuple[str, int]]) -> None:
    """Raise typer.Exit(1) if any (proto, port) in the list is already in use. ARK-07."""
    try:
        result = subprocess.run(
            ["ss", "-tuln"], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        console.print("[yellow]Warning: `ss` not available; skipping port probe.[/yellow]")
        return
    out = result.stdout
    for proto, port in ports:
        # "udp   UNCONN  0  0  0.0.0.0:7778 0.0.0.0:*" and IPv6 variants
        pattern = rf"^{proto}\s+\S+\s+\S+\s+\S+\s+\S+:{port}\b"
        if re.search(pattern, out, re.MULTILINE):
            console.print(f"[red]Port {port}/{proto} is already in use.[/red]")
            raise typer.Exit(code=1)


def _create_settings_from_default(
    default_path: Path,
    dst_path: Path,
    section_rename: Optional[tuple[str, str]],
) -> None:
    """Create a settings file from a default template, optionally renaming a section header."""
    if not default_path.exists():
        rich.print(
            f"Default configuration file not found at {default_path}",
            file=sys.stderr,
        )
        rich.print(
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
    "ark": GameSpec(
        key="ark",
        display_name="ARK: Survival Evolved",
        app_id=376030,
        server_dir=Path("/home/steam/ARK"),
        binary_rel_path="ShooterGame/Binaries/Linux/ShooterGameServer",
        settings_path=_ARK_INSTANCE_CFG,
        default_settings_path=None,  # SET-04: install-time seed, no template
        settings_section_rename=None,  # ARK-09: no header rewrite
        service_name="arkserver",
        service_template_name="arkserver.service.template",
        settings_adapter=SettingsAdapter(
            parse=_arkmanager_parse, save=_arkmanager_save
        ),
        post_install_hooks=[],  # ARK-12: arkmanager + apt steamcmd own SDK setup
        apt_packages=[
            "steamcmd", "libc6-i386", "lib32gcc-s1", "lib32stdc++6",
            "curl", "bzip2", "tar", "rsync", "sed", "perl-modules", "lsof",
        ],
        steam_sdk_paths=[],  # ARK-12
        install_options={
            "port_default": 7778,
            "players_default": 10,
            "query_port_default": 27015,
            "rcon_port_default": 27020,
            "map_default": "TheIsland",
            "session_name_default": "logpose-ark",
            "branch_default": "preaquatica",
            "supported_maps": _ARK_SUPPORTED_MAPS,
        },
    ),
}


def _build_game_app(spec: GameSpec) -> typer.Typer:
    """Build a Typer sub-app that owns all verbs for a single GameSpec.

    Per-game verb branching: ARK delegates start/stop/... to arkmanager, while
    Palworld dispatches via systemctl. edit-settings is shared (adapter-driven).
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

    if spec.key == "ark":
        # ---- ARK: arkmanager delegation (ARK-19) + install branch (ARK-05) ----
        query_port_default = int(spec.install_options["query_port_default"])
        rcon_port_default = int(spec.install_options["rcon_port_default"])
        map_default = str(spec.install_options["map_default"])
        session_name_default = str(spec.install_options["session_name_default"])
        branch_default = str(spec.install_options["branch_default"])

        @sub.command()
        def install(
            map: str = typer.Option(
                map_default, callback=_validate_ark_map,
                help="Map (one of the 12 supported).",
            ),
            port: int = typer.Option(
                port_default, help="ark_Port raw socket (game port 7777 is implicit).",
            ),
            query_port: int = typer.Option(
                query_port_default, "--query-port", help="ark_QueryPort.",
            ),
            rcon_port: int = typer.Option(
                rcon_port_default, "--rcon-port", help="ark_RCONPort.",
            ),
            players: int = typer.Option(
                players_default, help="ark_MaxPlayers (1-70).",
            ),
            session_name: str = typer.Option(
                session_name_default, "--session-name",
                callback=_validate_ark_session_name,
                help="ark_SessionName.",
            ),
            admin_password: Optional[str] = typer.Option(
                None, "--admin-password",
                help="ark_ServerAdminPassword (prompted hidden if missing).",
            ),
            password: str = typer.Option(
                "", help="Optional ark_ServerPassword (public if empty).",
            ),
            beta: str = typer.Option(
                branch_default, help="Branch (set to empty string for stable).",
            ),
            generate_password: bool = typer.Option(
                False, "--generate-password",
                help="Generate admin password via secrets.token_urlsafe(16).",
            ),
            enable_autostart: bool = typer.Option(
                False, "--enable-autostart",
                help="Enable arkserver.service at boot.",
            ),
            start: bool = typer.Option(
                False, "--start", help="Start the server after installation.",
            ),
        ) -> None:
            """Install ARK via arkmanager (wraps docs/ark-install-reference.md §4)."""
            if Path.home() == Path("/root"):
                rich.print(
                    "This script should not be run as root. Exiting.", file=sys.stderr,
                )
                raise typer.Exit(code=1)

            # Port collision probe (ARK-07) — fail early before any apt action.
            _probe_port_collision([
                ("udp", 7777),       # implicit game port
                ("udp", port),       # ark_Port raw socket
                ("udp", query_port), # ark_QueryPort
                ("tcp", rcon_port),  # ark_RCONPort
            ])

            # Resolve admin_password: explicit value > generate > prompt.
            if admin_password is None:
                if generate_password:
                    import secrets
                    admin_password = secrets.token_urlsafe(16)
                    console.print(
                        f"[bold yellow]Generated admin password (printed "
                        f"once):[/bold yellow] {admin_password}"
                    )
                else:
                    admin_password = typer.prompt(
                        "Admin password", hide_input=True,
                        confirmation_prompt=False,
                    )

            main_cfg_values = {
                "arkserverroot": str(spec.server_dir),
                "serverMap": map,
                "ark_SessionName": session_name,
                "ark_Port": str(port),
                "ark_QueryPort": str(query_port),
                "ark_RCONEnabled": "True",
                "ark_RCONPort": str(rcon_port),
                "ark_ServerPassword": password,
                "ark_ServerAdminPassword": admin_password,
                "ark_MaxPlayers": str(players),
            }
            invoking_user = Path.home().name

            _install_ark(
                branch=beta,
                main_cfg_values=main_cfg_values,
                invoking_user=invoking_user,
            )

            # Polkit rule regeneration picks up arkserver.service automatically.
            _setup_polkit(invoking_user, GAMES.values())

            if enable_autostart:
                console.print("Enabling arkserver.service at boot...")
                service_content = _render_service_file(
                    service_name=spec.service_name,
                    template_name=spec.service_template_name,
                    user=invoking_user,
                    working_directory=spec.server_dir,
                    exec_start_path=spec.server_dir / spec.binary_rel_path,
                    port=port,
                    players=players,
                )
                _write_service_file(
                    Path(f"/etc/systemd/system/{spec.service_name}.service"),
                    service_content,
                )
                _run_command(f"sudo systemctl enable {spec.service_name}")

            console.print("Installation complete!")

            if start:
                console.print("Starting the server...")
                _run_command("sudo -u steam /usr/local/bin/arkmanager start")
                console.print(
                    "Server started. First map load takes 5-10 min — "
                    "`logpose ark status` to monitor."
                )
            else:
                console.print(
                    "You can now start the server with: logpose ark start"
                )

        @sub.command()
        def start() -> None:
            """Start the ARK server via arkmanager."""
            _run_command("sudo -u steam /usr/local/bin/arkmanager start")

        @sub.command()
        def stop() -> None:
            """Stop the ARK server via arkmanager (graceful save)."""
            _run_command("sudo -u steam /usr/local/bin/arkmanager stop")

        @sub.command()
        def restart() -> None:
            """Restart the ARK server via arkmanager."""
            _run_command("sudo -u steam /usr/local/bin/arkmanager restart")

        @sub.command()
        def status() -> None:
            """Status of the ARK server via arkmanager."""
            _run_command(
                "sudo -u steam /usr/local/bin/arkmanager status", check=False,
            )

        @sub.command()
        def saveworld() -> None:
            """Force a world save via arkmanager RCON."""
            _run_command("sudo -u steam /usr/local/bin/arkmanager saveworld")

        @sub.command()
        def backup() -> None:
            """Backup current save via arkmanager."""
            _run_command("sudo -u steam /usr/local/bin/arkmanager backup")

        @sub.command()
        def update() -> None:
            """Update ARK via arkmanager (runs twice — steamcmd self-update quirk)."""
            branch = str(spec.install_options["branch_default"])
            cmd = (
                f"sudo -u steam /usr/local/bin/arkmanager update "
                f"--validate --beta={branch}"
            )
            _run_command(cmd, check=False)  # self-update, exits 0 no payload
            _run_command(cmd)                # actual update

        @sub.command()
        def enable() -> None:
            """Enable arkserver.service at boot (requires --enable-autostart at install)."""
            _run_command(f"sudo systemctl enable {spec.service_name}")

        @sub.command()
        def disable() -> None:
            """Disable arkserver.service from starting at boot."""
            _run_command(f"sudo systemctl disable {spec.service_name}")

    else:
        # ---- Palworld: existing Phase-4 body (unchanged — PAL-09 invariant) ----
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
            _setup_polkit(Path.home().name, GAMES.values())

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

    # --- Shared: edit-settings (SettingsAdapter-driven — both games) ---------
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


def _version_cb(value: Optional[bool]) -> None:
    if value:
        import importlib.metadata

        try:
            v = importlib.metadata.version("logpose-launcher")
        except importlib.metadata.PackageNotFoundError:
            v = "unknown"
        console.print(f"logpose {v}")
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
