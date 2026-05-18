"""
Orchestrator that writes the six numbered step files for the demo.

INPUT:  NetworkIR, SmvPrepared, the original DSL text, plus verification artefacts (optional).
OUTPUT: writes six files inside ``out_dir`` and returns the list of (label, path) pairs.

The list is convenient for printing a structured ``=== Step N: <label> ===`` summary in stdout.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from snn_mc.ir import NetworkIR
from snn_mc.report.composition import render_step4
from snn_mc.report.diagram import render_step1
from snn_mc.report.ir_dump import render_step3
from snn_mc.report.properties_view import render_step5
from snn_mc.report.results_view import render_step6
from snn_mc.smv.prepare import SmvPrepared
from snn_mc.verify.result import NuSMVSummary


def write_all_steps(
    *,
    out_dir: Path,
    ir: NetworkIR,
    prepared: SmvPrepared,
    dsl_text: str,
    dsl_source_path: str,
    emit_mode: str = "lif",
    summary: Optional[NuSMVSummary] = None,
    nusmv_exit_code: Optional[int] = None,
    counterexample: Optional[str] = None,
    skip_verify: bool = False,
) -> List[Tuple[str, Path]]:
    """
    INPUT:
        out_dir          — directory to receive the six files (created if missing).
        ir               — NetworkIR after parse + compose.
        prepared         — SmvPrepared (renamed graph + arch list).
        dsl_text         — original DSL contents (used verbatim for step 2).
        dsl_source_path  — display path to embed in step 1.
        emit_mode        — passed through to property rendering.
        summary          — optional NuSMVSummary (step 6 reflects it; None means not verified).
        nusmv_exit_code  — required when ``summary`` is provided.
        counterexample   — optional CE excerpt for step 6.
        skip_verify      — True when the user passed ``--skip-verify``.
    OUTPUT: list of (label, path) pairs in step order.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    step1 = out_dir / "step1_diagram.md"
    step2 = out_dir / "step2_input.dsl"
    step3 = out_dir / "step3_ir.json"
    step4 = out_dir / "step4_composition.txt"
    step5 = out_dir / "step5_properties.smv"
    step6 = out_dir / "step6_results.txt"

    step1.write_text(render_step1(ir, source_path=dsl_source_path), encoding="utf-8")
    step2.write_text(dsl_text, encoding="utf-8")
    step3.write_text(render_step3(ir), encoding="utf-8")
    step4.write_text(render_step4(ir, prepared), encoding="utf-8")
    step5.write_text(render_step5(ir, prepared, emit_mode=emit_mode), encoding="utf-8")

    if skip_verify:
        step6.write_text(
            render_step6(
                NuSMVSummary(true_count=0, false_count=0, false_spec_lines=()),
                nusmv_exit_code=-1,
                counterexample=None,
                skipped=True,
                skip_reason="user passed --skip-verify",
            ),
            encoding="utf-8",
        )
    elif summary is not None and nusmv_exit_code is not None:
        step6.write_text(
            render_step6(
                summary,
                nusmv_exit_code=nusmv_exit_code,
                counterexample=counterexample,
            ),
            encoding="utf-8",
        )
    else:
        step6.write_text(
            "Step 6 - Verification results\n"
            "============================\n\n"
            "(verification was not executed for this run)\n",
            encoding="utf-8",
        )

    return [
        ("Step 1: Network diagram", step1),
        ("Step 2: DSL source",       step2),
        ("Step 3: NetworkIR (JSON)", step3),
        ("Step 4: Composition",      step4),
        ("Step 5: Properties",       step5),
        ("Step 6: Results",          step6),
    ]
