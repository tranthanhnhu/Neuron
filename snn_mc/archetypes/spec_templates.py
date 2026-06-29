"""
Reusable NuSMV spec line builders for archetype ``specs()`` methods.

Each helper returns one or more lines (including optional ``-- [Category]`` headers).
"""

from __future__ import annotations

from typing import List, Sequence


def section(title: str) -> str:
    return f"-- [{title}]"


def ef_each(nodes: Sequence[str]) -> List[str]:
    lines: List[str] = [section("Reachability")]
    for n in nodes:
        lines.append(f"CTLSPEC EF {n}.spike")
    return lines


def ctl_propagate_chain(nodes: Sequence[str]) -> List[str]:
    if len(nodes) < 2:
        return []
    lines: List[str] = [section("Propagation")]
    for a, b in zip(nodes, nodes[1:]):
        lines.append(f"CTLSPEC AG ({a}.spike -> EF {b}.spike)")
    return lines


def mutual_exclusion(a: str, b: str) -> str:
    return f"CTLSPEC AG !({a}.spike & {b}.spike)"


def ctl_recurrent_oscillation(node: str) -> str:
    """Recurrent firing: spike eventually clears; silence eventually spikes again."""
    return (
        f"CTLSPEC AG (({node}.spike -> AF !{node}.spike) & "
        f"(!{node}.spike -> AF {node}.spike))"
    )


def oscillation_section(nodes: Sequence[str]) -> List[str]:
    lines: List[str] = [section("Oscillation")]
    for n in nodes:
        lines.append(ctl_recurrent_oscillation(n))
    return lines


def ring_engagement(a: str, b: str) -> str:
    return f"CTLSPEC EF ({a}.spike & EF {b}.spike)"


def stim_implies_f(stim: str, formula: str) -> str:
    return f"LTLSPEC (G {stim}) -> (F {formula})"


def silence_without_stim(stim: str, nodes: Sequence[str]) -> str:
    silent = " & ".join([f"!{n}.spike" for n in nodes])
    return f"LTLSPEC (G !{stim}) -> (G ({silent}))"
