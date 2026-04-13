"""Byte-diff regression harness — ARK template files vs v0.2.0 goldens.

Invocation modes (both MUST exit 0 when the harness is green):
  pytest tests/test_ark_golden.py -x
  python tests/test_ark_golden.py

Locks the shape of:
  - road_poneglyph/templates/arkserver.service.template (ARK-02; static — no placeholders)
  - road_poneglyph/templates/road-poneglyph-ark.sudoers.template (ARK-18; one {user} placeholder)

Companion to tests/test_palworld_golden.py. Keep side-effect-free.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARKSERVER_TEMPLATE = ROOT / "road_poneglyph" / "templates" / "arkserver.service.template"
ARKSERVER_GOLDEN = ROOT / "tests" / "golden" / "arkserver.service.v0_2_0"
SUDOERS_TEMPLATE = ROOT / "road_poneglyph" / "templates" / "road-poneglyph-ark.sudoers.template"
SUDOERS_GOLDEN = ROOT / "tests" / "golden" / "road-poneglyph-ark.sudoers.v0_2_0"


def test_arkserver_service_template_static() -> None:
    """arkserver.service.template is a static file (no placeholders). Byte-exact vs golden."""
    rendered = ARKSERVER_TEMPLATE.read_bytes()
    expected = ARKSERVER_GOLDEN.read_bytes()
    assert rendered == expected, (
        f"arkserver.service.template drift vs v0.2.0 golden "
        f"(current={len(rendered)} bytes, golden={len(expected)} bytes)."
    )


def test_road_poneglyph_ark_sudoers_template_renders_correctly() -> None:
    """road-poneglyph-ark.sudoers.template rendered with user='foo' must match golden byte-for-byte."""
    template = SUDOERS_TEMPLATE.read_text()
    rendered = template.format(user="foo").encode("utf-8")
    expected = SUDOERS_GOLDEN.read_bytes()
    assert rendered == expected, (
        f"road-poneglyph-ark.sudoers.template render drift vs v0.2.0 golden "
        f"(rendered={len(rendered)} bytes, golden={len(expected)} bytes)."
    )


if __name__ == "__main__":
    try:
        test_arkserver_service_template_static()
    except AssertionError as exc:
        print(f"FAIL: test_arkserver_service_template_static: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        test_road_poneglyph_ark_sudoers_template_renders_correctly()
    except AssertionError as exc:
        print(
            f"FAIL: test_road_poneglyph_ark_sudoers_template_renders_correctly: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("OK: arkserver.service.template + road-poneglyph-ark.sudoers.template match v0.2.0 goldens")
    sys.exit(0)
