"""
End-to-end CLI: ``python -m snn_mc run <file.dsl> --out runs/demo``.

PIPELINE (orchestrator only — every stage lives in its own module):

    1. PARSE     dsl.parser.parse_file(<dsl>) -> NetworkIR
    2. COMPOSE   composer.compose(ir)         (semantic validation)
    3. PREPARE   smv.prepare.prepare_ir(ir)   -> SmvPrepared (renamed graph + arch list)
    4. EMIT      writes model.smv / properties.smv / combined.smv to ``--out``
    5. VERIFY    runs NuSMV on combined.smv (unless ``--skip-verify``)
    6. ANALYSE   parses NuSMV log; writes counterexample excerpt on failure
    7. SIM       writes sim_stub.txt (unless ``--skip-sim`` or specs failed)
    8. REPORT    writes the six numbered step files for demo

EXIT CODES:
    0 success                4 NuSMV log contained no parsable spec lines
    1 at least one spec false
    2 missing DSL file
    3 NuSMV not on PATH
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import snn_mc.composer as composer
import snn_mc.smv as smv
from snn_mc.dsl.parser import parse_file
from snn_mc.report.steps import write_all_steps
from snn_mc.sim.stub import run_simulation_stub
from snn_mc.verify.result import (
    extract_counterexample_block,
    summarize_nusmv_output,
)
from snn_mc.verify.runner import find_nusmv, run_nusmv


def _parse_overrides(items: list[str]) -> dict[str, str]:
    """Parse zero or more ``KEY=VAL`` strings into a dict. Only ``N=<int>`` is consumed downstream."""
    out: dict[str, str] = {}
    for it in items:
        if "=" not in it:
            raise SystemExit(f"--override expects KEY=VALUE, got: {it}")
        k, v = it.split("=", 1)
        out[k] = v
    return out


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="snn_mc",
        description=(
            "Pipeline: DSL -> NetworkIR -> NuSMV -> Python stub. "
            "Always writes the six numbered demo files alongside the .smv outputs."
        ),
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="Run the full pipeline on a DSL file.")
    run.add_argument("dsl", type=Path, help="Input .dsl file")
    run.add_argument(
        "--out", type=Path, default=Path("runs/demo"),
        help="Output directory (created if missing).",
    )
    run.add_argument(
        "--nusmv", type=str, default=None,
        help="Override the NuSMV executable path (default: search PATH).",
    )
    run.add_argument("--skip-verify", action="store_true", help="Emit SMV only, do not run NuSMV.")
    run.add_argument("--skip-sim", action="store_true", help="Do not write sim_stub.txt after success.")
    run.add_argument(
        "--emit-mode",
        choices=("lif", "simple_boolean"),
        default="lif",
        help="Neuron mapping: full LIF (default) or discrete bool_thr.",
    )
    run.add_argument(
        "--override", action="append", default=[],
        metavar="KEY=VAL",
        help="Override DSL key (only ``N=<int>`` is meaningful; rewrites every block-level N=).",
    )
    return ap


def _print_section(label: str, path: Path, *, max_lines: int = 200) -> None:
    """Pretty-print a step file header + body (clamped) to stdout."""
    print()
    print("=" * 78)
    print(f"== {label}   ({path})")
    print("=" * 78)
    try:
        body = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"  (could not read: {exc})")
        return
    lines = body.splitlines()
    if len(lines) > max_lines:
        print("\n".join(lines[:max_lines]))
        print(f"... ({len(lines) - max_lines} more lines truncated; see {path})")
    else:
        print(body)


def main(argv: Optional[list[str]] = None) -> int:
    """
    INPUT: optional argv list (defaults to ``sys.argv[1:]``).
    OUTPUT: process exit code (see module docstring).
    """
    args = _build_argparser().parse_args(argv)
    if args.cmd != "run":  # pragma: no cover — argparse already enforces it
        return 2

    dsl: Path = args.dsl
    if not dsl.is_file():
        print(f"[ERR] DSL not found: {dsl}", file=sys.stderr)
        return 2

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse --override KEY=VAL pairs; only N=<int> currently has meaning.
    overrides = _parse_overrides(args.override)
    override_n: Optional[int] = None
    if "N" in overrides:
        try:
            override_n = int(overrides["N"])
        except ValueError as exc:
            print(f"[ERR] --override N=<int> requires an integer (got {overrides['N']})", file=sys.stderr)
            return 2

    # --- Stage 1+2: parse + compose ---
    dsl_text = dsl.read_text(encoding="utf-8")
    ir = parse_file(dsl, override_n=override_n)
    ir = composer.compose(ir)

    # --- Stage 3: prepare a NuSMV-safe snapshot ---
    prepared = smv.prepare_ir(ir)

    # --- Stage 4: emit SMV artefacts ---
    emit_mode = args.emit_mode
    model_path = out_dir / "model.smv"
    props_path = out_dir / "properties.smv"
    combined_path = out_dir / "combined.smv"
    log_path = out_dir / "nusmv.log"

    model_path.write_text(smv.emit_model_smv(ir, prepared, emit_mode=emit_mode), encoding="utf-8")
    props_path.write_text(smv.build_properties_smv(prepared, ir, emit_mode=emit_mode), encoding="utf-8")
    combined_path.write_text(smv.build_combined_smv(ir, prepared, emit_mode=emit_mode), encoding="utf-8")
    print(f"[OK] wrote {model_path}")
    print(f"[OK] wrote {props_path}")
    print(f"[OK] wrote {combined_path}")

    # --- Stage 5+6: optional NuSMV run + log analysis ---
    summary = None
    nusmv_rc: Optional[int] = None
    counterexample: Optional[str] = None
    verify_exit: Optional[int] = None
    if args.skip_verify:
        print("[INFO] verification skipped (--skip-verify)")
    else:
        nusmv_exe = args.nusmv or find_nusmv()
        try:
            nusmv_rc, log_text = run_nusmv(combined_path, log_path, nusmv_exe=nusmv_exe)
        except FileNotFoundError as exc:
            print(f"[ERR] {exc}", file=sys.stderr)
            verify_exit = 3
        else:
            print(f"[OK] NuSMV exit={nusmv_rc}, log={log_path}")
            summary = summarize_nusmv_output(log_text)
            print(f"[RESULT] true={summary.true_count} false={summary.false_count}")
            if summary.false_count > 0:
                counterexample = extract_counterexample_block(log_text)
                if counterexample:
                    ce_path = out_dir / "counterexample_snippet.txt"
                    ce_path.write_text(counterexample, encoding="utf-8")
                    print(f"[INFO] counterexample snippet: {ce_path}")

    # --- Stage 8: always write the six demo step files (even if NuSMV was missing) ---
    step_files = write_all_steps(
        out_dir=out_dir,
        ir=ir,
        prepared=prepared,
        dsl_text=dsl_text,
        dsl_source_path=str(dsl),
        emit_mode=emit_mode,
        summary=summary,
        nusmv_exit_code=nusmv_rc,
        counterexample=counterexample,
        skip_verify=args.skip_verify,
    )
    for label, path in step_files:
        _print_section(label, path)

    if verify_exit is not None:
        return verify_exit

    if args.skip_verify:
        return 0

    if summary is None:
        return 4
    if summary.false_count > 0:
        return 1
    if summary.true_count == 0:
        print("[WARN] NuSMV log contained no parsable 'is true' lines; check nusmv.log.", file=sys.stderr)
        return 4

    # --- Stage 7: post-verify Python stub ---
    if not args.skip_sim:
        sim_out = out_dir / "sim_stub.txt"
        bool_py = (out_dir / "sim_simple_boolean.py") if emit_mode == "simple_boolean" else None
        run_simulation_stub(
            ir, sim_out, prepared=prepared, emit_mode=emit_mode, boolean_sim_py=bool_py
        )
        print(f"[OK] sim stub written: {sim_out}")
        if bool_py is not None and bool_py.is_file():
            print(f"[OK] simple_boolean simulator: {bool_py}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
