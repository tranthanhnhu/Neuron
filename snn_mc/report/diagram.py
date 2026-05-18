"""
Render a NetworkIR as a Mermaid flowchart and a plain-ASCII summary (no graphics deps).

Used for ``step1_diagram.md``: the file the professor sees first.
"""

from __future__ import annotations

from typing import List

from snn_mc.ir import NetworkIR


def _safe_id(name: str) -> str:
    """Mermaid node IDs must not contain spaces or punctuation that confuses the parser."""
    return name.replace("-", "_").replace(".", "_")


def render_mermaid(ir: NetworkIR) -> str:
    """
    INPUT: NetworkIR.
    OUTPUT: a Mermaid ``flowchart LR`` block. Excitatory edges use ``-->``, inhibitory use ``-.->``.
    """
    lines: List[str] = ["```mermaid", "flowchart LR"]
    # Declare nodes first (inputs as rectangles, neurons as circles).
    for inp in sorted(ir.inputs):
        lines.append(f"  {_safe_id(inp)}[\"{inp} (input)\"]")
    for n in sorted(ir.neurons):
        lines.append(f"  {_safe_id(n)}(({n}))")
    # Then declare edges.
    for e in ir.edges:
        if e.weight >= 0:
            lines.append(f"  {_safe_id(e.src)} -->|\"exc w={e.weight}\"| {_safe_id(e.dst)}")
        else:
            lines.append(f"  {_safe_id(e.src)} -.->|\"inh w={e.weight}\"| {_safe_id(e.dst)}")
    lines.append("```")
    return "\n".join(lines)


def render_ascii(ir: NetworkIR) -> str:
    """
    INPUT: NetworkIR.
    OUTPUT: human-readable ASCII summary listing inputs, neurons, and grouped edges per neuron.
    """
    lines: List[str] = []
    lines.append("Network (ASCII summary)")
    lines.append("=======================")
    lines.append(f"Inputs ({len(ir.inputs)}): {sorted(ir.inputs)}")
    lines.append(f"Neurons ({len(ir.neurons)}): {sorted(ir.neurons)}")
    lines.append("")
    lines.append("Edges per destination neuron:")
    for n in sorted(ir.neurons):
        exc = [(e.src, e.weight) for e in ir.edges if e.dst == n and e.weight >= 0]
        inh = [(e.src, e.weight) for e in ir.edges if e.dst == n and e.weight < 0]
        line = f"  {n} <- exc: {exc}    inh: {inh}"
        lines.append(line)
    return "\n".join(lines)


def render_step1(ir: NetworkIR, *, source_path: str) -> str:
    """
    INPUT: NetworkIR + the absolute / relative path of the user's DSL.
    OUTPUT: markdown for ``step1_diagram.md`` containing the Mermaid + ASCII renderings.
    """
    parts = [
        "# Step 1 — Network diagram",
        "",
        f"Source DSL: `{source_path}`",
        "",
        "## Mermaid",
        "",
        render_mermaid(ir),
        "",
        "## ASCII",
        "",
        "```",
        render_ascii(ir),
        "```",
        "",
    ]
    return "\n".join(parts)
