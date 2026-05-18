"""
NuSMV log post-processing (text-only — no NuSMV API dependency).

INPUT:  the merged stdout+stderr string from a NuSMV process.
OUTPUT:
    summarize_nusmv_output(text)        -> NuSMVSummary
    extract_counterexample_block(text)  -> str | None  (best-effort excerpt for the first false spec)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class NuSMVSummary:
    """Cheap-parse aggregate over NuSMV's ``-- specification ... is true/false`` lines."""

    true_count: int
    false_count: int
    false_spec_lines: Tuple[str, ...]


def summarize_nusmv_output(output: str) -> NuSMVSummary:
    """
    INPUT: full NuSMV process output.
    OUTPUT: NuSMVSummary with counts and a bounded list of the first false-spec lines.
    """
    true_count = 0
    false_count = 0
    false_lines: List[str] = []
    for line in output.splitlines():
        s = line.strip()
        if s.startswith("-- specification") and s.endswith("is true"):
            true_count += 1
        elif s.startswith("-- specification") and s.endswith("is false"):
            false_count += 1
            if len(false_lines) < 20:
                false_lines.append(s)
    return NuSMVSummary(
        true_count=true_count,
        false_count=false_count,
        false_spec_lines=tuple(false_lines),
    )


def extract_counterexample_block(output: str) -> Optional[str]:
    """
    INPUT: full NuSMV log.
    OUTPUT: a bounded excerpt around the first false spec / trace; ``None`` when all specs pass.

    The window starts at the first ``Trace description`` / ``-> State`` line after the false spec
    (falling back to the false spec line itself) and spans at most 160 lines.
    """
    lines = output.splitlines()
    false_idx: Optional[int] = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("-- specification") and s.endswith("is false"):
            false_idx = i
            break
    if false_idx is None:
        return None
    trace_idx: Optional[int] = None
    for j in range(false_idx, min(len(lines), false_idx + 400)):
        lj = lines[j].lower()
        if "trace description" in lj or "-> state" in lj or "trace type" in lj:
            trace_idx = j
            break
    start = trace_idx if trace_idx is not None else false_idx
    end = min(len(lines), start + 160)
    return "\n".join(lines[start:end])


def all_specifications_true(summary: NuSMVSummary) -> bool:
    """OUTPUT: True iff at least one spec passed and none failed."""
    return summary.false_count == 0 and summary.true_count > 0
