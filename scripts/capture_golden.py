"""One-shot capture: render palserver.service from the current template
against the locked Phase 2 fixture and write bytes to tests/golden/.

Re-runnable. Idempotent. Exits 1 if the resulting render is not 323 bytes
(the v0.1.19 size — any drift signals template corruption).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "road_poneglyph" / "templates" / "palserver.service.template"
GOLDEN = ROOT / "tests" / "golden" / "palserver.service.v0_1_19"

FIXTURE = {
    "user": "foo",
    "port": 8211,
    "players": 32,
    "working_directory": "/home/foo/.steam/steam/steamapps/common/PalServer",
    "exec_start_path": "/home/foo/.steam/steam/steamapps/common/PalServer/PalServer.sh",
}


def main() -> int:
    template_bytes = TEMPLATE.read_bytes()
    rendered = template_bytes.decode("utf-8").format(**FIXTURE).encode("utf-8")
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_bytes(rendered)
    print(f"wrote {len(rendered)} bytes to {GOLDEN.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
