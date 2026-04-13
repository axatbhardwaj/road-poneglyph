"""Byte-diff regression harness — palserver.service render vs v0.1.19 golden.

Invocation modes (both MUST exit 0 when the harness is green):
  pytest tests/test_palworld_golden.py -x
  python tests/test_palworld_golden.py

Drops dependency on road_poneglyph.main on purpose in Task 3 — Phase 2 Plan 05 adds
a second test that exercises the real _render_service_file code path once
Plan 03 extracts it. Keep this file minimal and side-effect-free.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "road_poneglyph" / "templates" / "palserver.service.template"
GOLDEN = ROOT / "tests" / "golden" / "palserver.service.v0_1_19"

# Ensure `road_poneglyph` is importable whether this file is run via pytest or
# `python tests/test_palworld_golden.py`. Pytest injects rootdir automatically;
# script mode only adds the script's own directory to sys.path. Plan 05's new
# test imports `road_poneglyph.main`, so the repo root must be on sys.path in both modes.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE = {
    "user": "foo",
    "port": 8211,
    "players": 32,
    "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
    "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
}


def _render_from_template() -> bytes:
    """Render by str.format on the on-disk template. No road_poneglyph import."""
    return TEMPLATE.read_bytes().decode("utf-8").format(**FIXTURE).encode("utf-8")


def test_palserver_service_byte_identical_to_v0_1_19() -> None:
    rendered = _render_from_template()
    expected = GOLDEN.read_bytes()
    assert rendered == expected, (
        f"palserver.service render drift vs v0.1.19 golden "
        f"(rendered={len(rendered)} bytes, golden={len(expected)} bytes). "
        f"Run: diff <(python scripts/capture_golden.py && cat {GOLDEN}) - "
        f"to inspect, then decide whether template change was intentional."
    )


def test_golden_matches_v0_1_19_tag() -> None:
    """Paranoia: verify template on disk equals v0.1.19 tag byte-for-byte."""
    try:
        v019_bytes = subprocess.check_output(
            [
                "git",
                "show",
                "v0.1.19:palworld_server_launcher/templates/palserver.service.template",
            ],
            cwd=str(ROOT),
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        import pytest

        pytest.skip(f"git or tag v0.1.19 unavailable: {exc}")
        return  # unreachable under pytest; placates type-checkers under plain python
    current_bytes = TEMPLATE.read_bytes()
    assert v019_bytes == current_bytes, (
        f"palserver.service.template drifted vs v0.1.19 tag "
        f"(current={len(current_bytes)} bytes, v0.1.19={len(v019_bytes)} bytes). "
        f"Golden was captured from current template — if template drifted, golden is invalid."
    )


def test_render_service_file_byte_identical_to_golden() -> None:
    """Real code path: _render_service_file must produce byte-identical output to the golden."""
    from road_poneglyph.main import _render_service_file

    rendered_str = _render_service_file(
        service_name="palserver",
        template_name="palserver.service.template",
        user=FIXTURE["user"],
        working_directory=Path(FIXTURE["working_directory"]),
        exec_start_path=Path(FIXTURE["exec_start_path"]),
        port=FIXTURE["port"],
        players=FIXTURE["players"],
    )
    rendered_bytes = rendered_str.encode("utf-8")
    expected = GOLDEN.read_bytes()
    assert rendered_bytes == expected, (
        f"_render_service_file drift vs v0.1.19 golden "
        f"(rendered={len(rendered_bytes)} bytes, golden={len(expected)} bytes)."
    )


def test_polkit_rule_byte_identical_to_v0_2_0_golden() -> None:
    """Merged polkit rule render must match the committed golden byte-for-byte."""
    from road_poneglyph.main import GAMES

    template = (ROOT / "road_poneglyph" / "templates" / "40-road-poneglyph.rules.template").read_text()
    units = ", ".join(f'"{spec.service_name}.service"' for spec in GAMES.values())
    rendered = template.format(units=units, user="foo").encode("utf-8")
    expected = (ROOT / "tests" / "golden" / "40-road-poneglyph.rules.v0_2_0").read_bytes()
    assert rendered == expected, (
        f"40-road-poneglyph.rules render drift vs v0.2.0 golden "
        f"(rendered={len(rendered)} bytes, golden={len(expected)} bytes)."
    )


if __name__ == "__main__":
    try:
        test_palserver_service_byte_identical_to_v0_1_19()
    except AssertionError as exc:
        print(f"FAIL: test_palserver_service_byte_identical_to_v0_1_19: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        import pytest as _pytest

        try:
            test_golden_matches_v0_1_19_tag()
        except _pytest.skip.Exception as skip_exc:
            print(f"SKIP: test_golden_matches_v0_1_19_tag: {skip_exc}", file=sys.stderr)
    except ImportError:
        try:
            v019_bytes = subprocess.check_output(
                [
                    "git",
                    "show",
                    "v0.1.19:palworld_server_launcher/templates/palserver.service.template",
                ],
                cwd=str(ROOT),
            )
            assert v019_bytes == TEMPLATE.read_bytes()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    try:
        test_render_service_file_byte_identical_to_golden()
    except AssertionError as exc:
        print(f"FAIL: test_render_service_file_byte_identical_to_golden: {exc}", file=sys.stderr)
        sys.exit(1)
    except ImportError as exc:
        print(f"FAIL: cannot import _render_service_file: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        test_polkit_rule_byte_identical_to_v0_2_0_golden()
    except AssertionError as exc:
        print(f"FAIL: test_polkit_rule_byte_identical_to_v0_2_0_golden: {exc}", file=sys.stderr)
        sys.exit(1)
    except ImportError as exc:
        print(f"FAIL: cannot import road_poneglyph.main: {exc}", file=sys.stderr)
        sys.exit(1)

    print("OK: palserver.service + 40-road-poneglyph.rules match goldens")
    sys.exit(0)
