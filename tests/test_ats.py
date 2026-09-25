from pathlib import Path

from typer.testing import CliRunner

from road_poneglyph.main import app, _ats_config_parse, _ats_config_save, _render_ats_service


def test_ats_cli_is_available():
    result = CliRunner().invoke(app, ["ats", "--help"])
    assert result.exit_code == 0
    assert "install" in result.output


def test_ats_config_roundtrip_preserves_other_fields(tmp_path: Path):
    config = tmp_path / "server_config.sii"
    config.write_text('SiiNunit\n{\nserver_config : _nameless.1 {\n lobby_name: "Old"\n traffic: true\n}\n}\n')
    values = _ats_config_parse(config)
    values["lobby_name"] = "New"
    _ats_config_save(config, values)
    saved = config.read_text()
    assert 'lobby_name: "New"' in saved
    assert "traffic: true" in saved


def test_ats_service_uses_linux_launcher_and_graceful_stop():
    service = _render_ats_service("steam", Path("/home/steam/AmericanTruckSimulatorDedicatedServer"))
    assert "server_launch.sh" in service
    assert "KillSignal=SIGINT" in service
    assert "User=steam" in service
