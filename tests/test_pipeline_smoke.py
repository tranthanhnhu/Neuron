"""
Smoke test for the new pipeline. Does NOT require NuSMV.

Strategy:
    Run ``python -m snn_mc run examples/series_negloop.dsl --out <tmp> --skip-verify``
    and confirm:
      - the 6 numbered step files are written,
      - the 3 SMV artefacts are written,
      - step 3 (IR JSON) contains the expected neuron names.

Also runs the in-process pipeline (without a subprocess) to verify the same conditions
via the public API. This catches breakage in modules quickly without depending on Python
being launchable from a child process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "series_negloop.dsl"


def _expected_step_files(out: Path) -> list[Path]:
    return [
        out / "step1_diagram.md",
        out / "step2_input.dsl",
        out / "step3_ir.json",
        out / "step4_composition.txt",
        out / "step5_properties.smv",
        out / "step6_results.txt",
    ]


def _expected_smv_files(out: Path) -> list[Path]:
    return [out / "model.smv", out / "properties.smv", out / "combined.smv"]


def test_in_process_pipeline(tmp_path: Path) -> None:
    """Run the pipeline directly via the public API (no subprocess)."""
    import sys as _sys

    _sys.path.insert(0, str(REPO))
    try:
        from snn_mc.cli import main as cli_main  # noqa: WPS433 (local import is intentional)
    finally:
        # Leave the path in place so subsequent in-process imports work for other tests.
        pass

    out = tmp_path / "run"
    rc = cli_main(["run", str(EXAMPLE), "--out", str(out), "--skip-verify"])
    assert rc == 0
    for p in _expected_step_files(out):
        assert p.is_file(), f"missing {p}"
    for p in _expected_smv_files(out):
        assert p.is_file(), f"missing {p}"

    ir = json.loads((out / "step3_ir.json").read_text(encoding="utf-8"))
    assert set(ir["neurons"]) >= {"c1", "c2", "c3", "c4", "a", "b"}
    assert "stim" in set(ir["inputs"])
    assert {a["kind"] for a in ir["archetypes"]} >= {"simple_series", "negative_loop"}


def test_subprocess_pipeline(tmp_path: Path) -> None:
    """Run the same scenario as a child Python process (closer to user-facing CLI)."""
    out = tmp_path / "run_sub"
    env = {**_env_with_repo()}
    rc = subprocess.run(
        [
            sys.executable, "-m", "snn_mc", "run",
            str(EXAMPLE), "--out", str(out), "--skip-verify",
        ],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    for p in _expected_step_files(out):
        assert p.is_file(), f"missing {p}"


def test_override_n(tmp_path: Path) -> None:
    """``--override N=6`` should rewrite the chain to six neurons (c1..c6)."""
    import sys as _sys
    _sys.path.insert(0, str(REPO))
    from snn_mc.cli import main as cli_main  # noqa: WPS433

    out = tmp_path / "n6"
    rc = cli_main([
        "run", str(EXAMPLE), "--out", str(out),
        "--skip-verify", "--override", "N=6",
    ])
    assert rc == 0
    ir = json.loads((out / "step3_ir.json").read_text(encoding="utf-8"))
    assert {"c1", "c2", "c3", "c4", "c5", "c6"} <= set(ir["neurons"])


def _env_with_repo() -> dict[str, str]:
    """Return a process environment that puts ``NewStructure`` on PYTHONPATH."""
    import os

    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(REPO) + (";" + existing if existing else "")
    return env
