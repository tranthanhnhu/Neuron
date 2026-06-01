#!/usr/bin/env python3
"""Quick NuSMV scalability check: chain length vs wall time."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "series_negloop.dsl"


def main() -> int:
    sys.path.insert(0, str(REPO))
    from snn_mc.cli import main as cli_main  # noqa: WPS433

    for n in (4, 12, 24):
        out = REPO / "runs" / f"bench_N{n}"
        t0 = time.perf_counter()
        rc = cli_main([
            "run", str(EXAMPLE), "--out", str(out), "--override", f"N={n}",
        ])
        elapsed = time.perf_counter() - t0
        log = out / "nusmv.log"
        log_size = log.stat().st_size if log.is_file() else 0
        print(f"N={n}  exit={rc}  time={elapsed:.2f}s  log_bytes={log_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
