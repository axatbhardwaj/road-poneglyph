"""Byte-diff regression harness — palserver.service render vs v0.1.19 golden.

Invocation modes (both MUST exit 0 when the harness is green):
  pytest tests/test_palworld_golden.py -x
  python tests/test_palworld_golden.py

Drops dependency on logpose.main on purpose in Task 3 — Phase 2 Plan 05 adds
a second test that exercises the real _render_service_file code path once
Plan 03 extracts it. Keep this file minimal and side-effect-free.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "logpose" / "templates" / "palserver.service.template"
GOLDEN = ROOT / "tests" / "golden" / "palserver.service.v0_1_19"

FIXTURE = {
    "user": "foo",
    "port": 8211,
    "players": 32,
    "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
    "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
}


def _render_from_template() -> bytes:
    """Render by str.format on the on-disk template. No logpose import."""
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


if __name__ == "__main__":
    # Script-mode entrypoint (phase success criterion #3: "script exits 0").
    # Runs both tests; the v0.1.19-tag test degrades to a skip-but-pass if git unavailable.
    try:
        test_palserver_service_byte_identical_to_v0_1_19()
    except AssertionError as exc:
        print(f"FAIL: test_palserver_service_byte_identical_to_v0_1_19: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        # In script mode, a pytest.skip call raises — catch it and treat as pass.
        import pytest as _pytest

        try:
            test_golden_matches_v0_1_19_tag()
        except _pytest.skip.Exception as skip_exc:
            print(f"SKIP: test_golden_matches_v0_1_19_tag: {skip_exc}", file=sys.stderr)
    except ImportError:
        # pytest not importable in script mode — run the raw check and let it skip silently
        try:
            v019_bytes = subprocess.check_output(
                [
                    "git",
                    "show",
                    "v0.1.19:palworld_server_launcher/templates/palserver.service.template",
                ],
                cwd=str(ROOT),
            )
            assert v019_bytes == TEMPLATE.read_bytes(), (
                "palserver.service.template drifted vs v0.1.19 tag"
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # git/tag unavailable — mirror the pytest skip behavior

    print("OK: palserver.service matches v0.1.19 golden")
    sys.exit(0)
