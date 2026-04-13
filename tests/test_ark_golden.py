"""Byte-diff regression harness — ARK template files vs v0.2.0 goldens.

Invocation modes (both MUST exit 0 when the harness is green):
  pytest tests/test_ark_golden.py -x
  python tests/test_ark_golden.py

Locks the shape of:
  - logpose/templates/arkserver.service.template (ARK-02; static — no placeholders)
  - logpose/templates/logpose-ark.sudoers.template (ARK-18; one {user} placeholder)

Companion to tests/test_palworld_golden.py. Keep side-effect-free.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARKSERVER_TEMPLATE = ROOT / "logpose" / "templates" / "arkserver.service.template"
ARKSERVER_GOLDEN = ROOT / "tests" / "golden" / "arkserver.service.v0_2_0"
SUDOERS_TEMPLATE = ROOT / "logpose" / "templates" / "logpose-ark.sudoers.template"
SUDOERS_GOLDEN = ROOT / "tests" / "golden" / "logpose-ark.sudoers.v0_2_0"


def test_arkserver_service_template_static() -> None:
    """arkserver.service.template is a static file (no placeholders). Byte-exact vs golden."""
    rendered = ARKSERVER_TEMPLATE.read_bytes()
    expected = ARKSERVER_GOLDEN.read_bytes()
    assert rendered == expected, (
        f"arkserver.service.template drift vs v0.2.0 golden "
        f"(current={len(rendered)} bytes, golden={len(expected)} bytes). "
        f"If the template change was intentional, re-capture via: "
        f"cp {ARKSERVER_TEMPLATE} {ARKSERVER_GOLDEN}"
    )


def test_logpose_ark_sudoers_template_renders_correctly() -> None:
    """logpose-ark.sudoers.template rendered with user='foo' must match golden byte-for-byte."""
    template = SUDOERS_TEMPLATE.read_text()
    rendered = template.format(user="foo").encode("utf-8")
    expected = SUDOERS_GOLDEN.read_bytes()
    assert rendered == expected, (
        f"logpose-ark.sudoers.template render drift vs v0.2.0 golden "
        f"(rendered={len(rendered)} bytes, golden={len(expected)} bytes). "
        f"If the placeholder set or template shape changed intentionally, "
        f"re-capture via: python -c \"from pathlib import Path; "
        f"p = Path('{SUDOERS_TEMPLATE}').read_text(); "
        f"Path('{SUDOERS_GOLDEN}').write_bytes(p.format(user='foo').encode('utf-8'))\""
    )


if __name__ == "__main__":
    try:
        test_arkserver_service_template_static()
    except AssertionError as exc:
        print(f"FAIL: test_arkserver_service_template_static: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        test_logpose_ark_sudoers_template_renders_correctly()
    except AssertionError as exc:
        print(
            f"FAIL: test_logpose_ark_sudoers_template_renders_correctly: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("OK: arkserver.service.template + logpose-ark.sudoers.template match v0.2.0 goldens")
    sys.exit(0)
