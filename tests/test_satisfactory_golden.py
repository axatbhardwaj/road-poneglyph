"""Byte-diff regression harness -- satisfactory.service render vs v0.3.0 golden.

Invocation modes (both MUST exit 0 when the harness is green):
  pytest tests/test_satisfactory_golden.py -x
  python tests/test_satisfactory_golden.py

Locks the shape of:
  - road_poneglyph/templates/satisfactory.service.template (SAT-02; SIGINT + Type=simple)

Companion to tests/test_palworld_golden.py and tests/test_ark_golden.py.
Keep side-effect-free.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "road_poneglyph" / "templates" / "satisfactory.service.template"
GOLDEN = ROOT / "tests" / "golden" / "satisfactory.service.v0_3_0"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE = {
    "user": "foo",
    "port": 7777,
    "reliable_port": 8888,
    "exec_start_path": "/home/foo/SatisfactoryDedicatedServer/FactoryServer.sh",
    "working_directory": "/home/foo/SatisfactoryDedicatedServer",
    "auto_update_line": "",
    "token_path": "/home/foo/.config/road-poneglyph/satisfactory-api-token",
}


def _render_from_template() -> bytes:
    """Render by str.format on the on-disk template. No road_poneglyph import."""
    return TEMPLATE.read_bytes().decode("utf-8").format(**FIXTURE).encode("utf-8")


def test_satisfactory_service_byte_identical_to_v0_3_0() -> None:
    rendered = _render_from_template()
    expected = GOLDEN.read_bytes()
    assert rendered == expected, (
        f"satisfactory.service.template render drift vs v0.3.0 golden "
        f"(rendered={len(rendered)} bytes, golden={len(expected)} bytes)."
    )


def test_render_satisfactory_service_byte_identical_to_golden() -> None:
    """Real code path: _render_satisfactory_service must produce byte-identical output to the golden."""
    from road_poneglyph.main import _render_satisfactory_service

    rendered_str = _render_satisfactory_service(
        user=FIXTURE["user"],
        working_directory=Path(FIXTURE["working_directory"]),
        exec_start_path=Path(FIXTURE["exec_start_path"]),
        port=FIXTURE["port"],
        reliable_port=FIXTURE["reliable_port"],
        auto_update=False,
    )
    rendered_bytes = rendered_str.encode("utf-8")
    expected = GOLDEN.read_bytes()
    assert rendered_bytes == expected, (
        f"_render_satisfactory_service drift vs v0.3.0 golden "
        f"(rendered={len(rendered_bytes)} bytes, golden={len(expected)} bytes)."
    )


if __name__ == "__main__":
    try:
        test_satisfactory_service_byte_identical_to_v0_3_0()
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        test_render_satisfactory_service_byte_identical_to_golden()
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    except ImportError as exc:
        print(f"FAIL: cannot import: {exc}", file=sys.stderr)
        sys.exit(1)

    print("OK: satisfactory.service.template matches v0.3.0 golden")
    sys.exit(0)
