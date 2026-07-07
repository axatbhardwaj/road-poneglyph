"""Regression harness for Sons Of The Forest service/config support.

Invocation modes (both MUST exit 0 when the harness is green):
  pytest tests/test_sons_golden.py -x
  python tests/test_sons_golden.py

Locks the shape of:
  - road_poneglyph/templates/sons.service.template
  - road_poneglyph.main JSON config adapter
  - Windows-depot SteamCMD command construction
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "road_poneglyph" / "templates" / "sons.service.template"
GOLDEN = ROOT / "tests" / "golden" / "sons.service.v0_4_0"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE = {
    "user": "foo",
    "working_directory": "/home/foo/SonsOfTheForestDedicatedServer",
    "exec_start_path": "/home/foo/SonsOfTheForestDedicatedServer/SonsOfTheForestDS.exe",
    "user_data_path": "/home/foo/SonsOfTheForestDedicatedServer/userdata",
    "wine_prefix": "/home/foo/.local/share/road-poneglyph/wine/sons",
}


def _render_from_template() -> bytes:
    """Render by str.format on the on-disk template. No road_poneglyph import."""
    return TEMPLATE.read_bytes().decode("utf-8").format(**FIXTURE).encode("utf-8")


def test_sons_service_byte_identical_to_v0_4_0() -> None:
    rendered = _render_from_template()
    expected = GOLDEN.read_bytes()
    assert rendered == expected, (
        f"sons.service.template render drift vs v0.4.0 golden "
        f"(rendered={len(rendered)} bytes, golden={len(expected)} bytes)."
    )


def test_render_sons_service_byte_identical_to_golden() -> None:
    """Real code path: _render_sons_service must produce byte-identical output."""
    from road_poneglyph.main import _render_sons_service

    rendered_str = _render_sons_service(
        user=FIXTURE["user"],
        working_directory=Path(FIXTURE["working_directory"]),
        exec_start_path=Path(FIXTURE["exec_start_path"]),
        user_data_path=Path(FIXTURE["user_data_path"]),
        wine_prefix=Path(FIXTURE["wine_prefix"]),
    )
    assert rendered_str.encode("utf-8") == GOLDEN.read_bytes()


def test_sons_json_config_roundtrip_preserves_types(tmp_path: Path) -> None:
    """dedicatedserver.cfg is JSON; edit-settings string values are coerced back."""
    from road_poneglyph.main import _json_config_parse, _json_config_save

    cfg = tmp_path / "dedicatedserver.cfg"
    cfg.write_text(
        '{\n'
        '  "ServerName": "Road Poneglyph",\n'
        '  "MaxPlayers": 8,\n'
        '  "LanOnly": false,\n'
        '  "GameSettings": {"Gameplay.TreeRegrowth": true}\n'
        '}\n'
    )
    parsed = _json_config_parse(cfg)
    assert parsed["ServerName"] == "Road Poneglyph"
    assert parsed["MaxPlayers"] == "8"
    assert parsed["LanOnly"] == "false"
    assert parsed["GameSettings"] == '{"Gameplay.TreeRegrowth": true}'

    parsed["MaxPlayers"] = "6"
    parsed["LanOnly"] = "true"
    _json_config_save(cfg, parsed)
    reparsed = _json_config_parse(cfg)
    assert reparsed["MaxPlayers"] == "6"
    assert reparsed["LanOnly"] == "true"


def test_sons_steamcmd_command_uses_public_app_update() -> None:
    """Current SOTF metadata installs anonymously without platform forcing."""
    from road_poneglyph.main import _steamcmd_update_command

    command = _steamcmd_update_command(
        Path("/home/foo/SonsOfTheForestDedicatedServer"),
        2465200,
    )
    assert "+@sSteamCmdForcePlatformType" not in command
    assert "+app_update 2465200 validate" in command


if __name__ == "__main__":
    try:
        test_sons_service_byte_identical_to_v0_4_0()
        test_render_sons_service_byte_identical_to_golden()
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            test_sons_json_config_roundtrip_preserves_types(Path(td))
        test_sons_steamcmd_command_uses_public_app_update()
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    except ImportError as exc:
        print(f"FAIL: cannot import: {exc}", file=sys.stderr)
        sys.exit(1)

    print("OK: Sons Of The Forest service/config support matches v0.4.0 goldens")
    sys.exit(0)
