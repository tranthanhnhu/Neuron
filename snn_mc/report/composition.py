"""
Human-readable summary of how the user's archetypes compose into one network.

Used for ``step4_composition.txt``.
"""

from __future__ import annotations

from typing import List

from snn_mc.ir import NetworkIR
from snn_mc.smv.prepare import SmvPrepared


def render_step4(ir: NetworkIR, prepared: SmvPrepared) -> str:
    """
    INPUT: NetworkIR (DSL view) + SmvPrepared (deduped + detected archetype list).
    OUTPUT: text listing every archetype instance, its participants, inputs, and meta.
            Includes both explicit (``block ...``) and graph-detected instances.
    """
    lines: List[str] = []
    lines.append("Step 4 - Composition")
    lines.append("====================")
    lines.append("")
    if not prepared.arch_list and not prepared.compositions:
        lines.append("(no archetypes or compositions detected)")
        return "\n".join(lines) + "\n"

    if prepared.compositions:
        lines.append("Compositions:")
        for c in prepared.compositions:
            tag = "(inferred)" if c.inferred else ""
            lines.append(f"  - {c.kind} {tag} : {' -> '.join(c.neurons) if c.kind == 'sequential' else ', '.join(c.neurons)}")
        lines.append("")

    lines.append("Archetype instances:")
    for i, inst in enumerate(prepared.arch_list, start=1):
        origin = "explicit (block ...)" if inst.explicit else "graph-detected"
        lines.append(f"  [{i}] kind={inst.kind}  ({origin})")
        lines.append(f"        nodes = {list(inst.nodes)}")
        if inst.inputs:
            lines.append(f"        inputs = {dict(inst.inputs)}")
        if inst.meta.get("outputs"):
            lines.append(f"        outputs = {list(inst.meta['outputs'])}")
        if inst.meta:
            extra = {k: v for k, v in inst.meta.items() if k != "outputs"}
            if extra:
                lines.append(f"        meta = {extra}")

    if ir.neuron_roles:
        lines.append("")
        lines.append("Neuron roles:")
        for n, r in sorted(ir.neuron_roles.items()):
            lines.append(f"  {n} = {r}")

    return "\n".join(lines) + "\n"
