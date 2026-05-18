"""
Step 6 helper: human-readable summary of the NuSMV run.

INPUT: the NuSMV log string + the parsed :class:`NuSMVSummary` + optional counterexample.
OUTPUT: text for ``step6_results.txt``.
"""

from __future__ import annotations

from typing import Optional

from snn_mc.verify.result import NuSMVSummary


def render_step6(
    summary: NuSMVSummary,
    *,
    nusmv_exit_code: int,
    counterexample: Optional[str] = None,
    skipped: bool = False,
    skip_reason: str = "",
) -> str:
    """
    INPUT:
        summary       — counts of true/false specs.
        nusmv_exit_code  — return code of the NuSMV subprocess.
        counterexample  — first CE excerpt (None when all specs pass).
        skipped         — True when verification was skipped (``--skip-verify``).
        skip_reason     — short reason string when ``skipped`` is True.
    OUTPUT: a text block written to ``step6_results.txt``.
    """
    lines = ["Step 6 - Verification results", "============================", ""]
    if skipped:
        lines.append(f"Verification skipped: {skip_reason}")
        return "\n".join(lines) + "\n"

    lines.append(f"NuSMV exit code     : {nusmv_exit_code}")
    lines.append(f"Specifications true : {summary.true_count}")
    lines.append(f"Specifications false: {summary.false_count}")
    if summary.false_spec_lines:
        lines.append("")
        lines.append("First false specs (NuSMV output):")
        for ln in summary.false_spec_lines[:10]:
            lines.append(f"  {ln}")
    if counterexample:
        lines.append("")
        lines.append("Counterexample excerpt:")
        lines.append("-----------------------")
        lines.append(counterexample)
    return "\n".join(lines) + "\n"
