"""
Temporal-logic specification emitter (CTL / LTL).

INPUT:  SmvPrepared (renamed graph + arch list + compositions) + NetworkIR (metadata).
OUTPUT:
    emit_properties_block(...)  -> spec text intended INSIDE ``MODULE main`` (after ASSIGN).
    build_properties_smv(...)   -> full ``properties.smv`` body (header + specs).

Block order inside the returned text (stable for diffing / teaching):
    (1) Baseline per-neuron LIF invariants (skipped in ``simple_boolean`` mode).
    (2) Composition properties from explicit / inferred ``compose`` lines.
    (3) Archetype macros (explicit ``block`` + graph-detected).
    (4) Verbatim user ``spec`` lines.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from snn_mc.archetypes import archetype_specs, dedup_archetype_instances
from snn_mc.ir import Composition, Edge, NetworkIR
from snn_mc.smv.prepare import SmvPrepared


def _edge_exists(edges: List[Edge], src: str, dst: str) -> bool:
    return any(e.src == src and e.dst == dst for e in edges)


def generate_composition_properties(comp: Composition, edges: List[Edge]) -> List[str]:
    """OUTPUT: spec lines obligated by one ``compose sequential|parallel ...`` declaration."""
    lines: List[str] = []
    if comp.kind == "sequential":
        ns = comp.neurons
        if len(ns) < 2:
            raise ValueError("compose sequential requires at least 2 neurons")
        for a, b in zip(ns, ns[1:]):
            if not _edge_exists(edges, a, b):
                raise ValueError(f"compose sequential requires an edge {a} -> {b}")
        suffix = " (inferred)" if comp.inferred else ""
        lines.append(f"-- Composition: sequential {' -> '.join(ns)}{suffix}")
        for a, b in zip(ns, ns[1:]):
            lines.append(f"CTLSPEC AG ({a}.spike -> EF {b}.spike)")
    elif comp.kind == "parallel":
        ns = comp.neurons
        lines.append(f"-- Composition: parallel {' '.join(ns)}")
        lines.append("CTLSPEC " + " & ".join([f"EF {n}.spike" for n in ns]))
        lines.append("CTLSPEC EF (" + " & ".join([f"{n}.spike" for n in ns]) + ")")
    return lines


def emit_properties_block(
    prepared: SmvPrepared,
    ir: NetworkIR,
    *,
    emit_mode: str = "lif",
) -> str:
    """
    INPUT:  prepared (renamed network), ir (un-sanitised metadata), emit_mode.
    OUTPUT: text with all temporal specifications, ready to be appended after ASSIGN.
    """
    lines: List[str] = []
    edges = list(prepared.edges)
    neuron_list = prepared.neuron_list
    comps = prepared.compositions
    arch_list = list(prepared.arch_list)
    user_specs = list(prepared.user_specs)

    lines.append("")
    lines.append("-- Baseline properties (generated)")
    if emit_mode == "lif":
        neuron_params = prepared.neuron_params
        param_specs = prepared.param_specs
        for n in neuron_list:
            pset_name = neuron_params.get(n, "default")
            pspec = param_specs.get(pset_name)
            r_init = pspec.R_init if pspec is not None else 0
            lines.append(f"-- [{n}] [Safety-Reset]")
            lines.append(f"CTLSPEC AG ({n}.spike -> AX ({n}.P = 0))")
            lines.append(f"-- [{n}] [Safety-Bound]")
            lines.append(f"CTLSPEC AG (({n}.P >= 0) & ({n}.P <= {n}.Pmax))")
            lines.append(f"-- [{n}] [Semantic]")
            lines.append(f"CTLSPEC AG ({n}.spike <-> ({n}.P >= {n}.tau))")
            lines.append(f"-- [{n}] [Structural]")
            lines.append(f"CTLSPEC AG ({n}.r_num = {r_init})")
    elif emit_mode == "simple_boolean":
        lines.append("-- (simple_boolean) No LIF P/tau baseline; submodule exposes spike := active only.")
    else:
        raise ValueError(f"Unknown emit_mode for properties: {emit_mode!r}")

    if comps:
        lines.append("")
        lines.append("-- Composition properties (generated)")
        for comp in comps:
            lines.extend(generate_composition_properties(comp, edges))

    auto: List[str] = []
    for it in dedup_archetype_instances(arch_list):
        # Pass the neuron set so each archetype can rewrite ``stim`` -> ``c4.spike`` when
        # an archetype's ``input=`` actually refers to a neuron (e.g. chain output) rather
        # than a true DSL input.
        block = archetype_specs(it, neurons=prepared.neurons, horizon=ir.horizon)
        if block:
            auto.append(f"-- From {it.kind} on nodes {list(it.nodes)}")
            auto.extend(block)
    if auto:
        lines.append("")
        lines.append("-- Archetype properties (auto-generated)")
        lines.extend(auto)

    if user_specs:
        lines.append("")
        lines.append("-- User-provided specs (from DSL)")
        lines.extend(user_specs)

    return "\n".join(lines) + "\n"


def build_properties_smv(
    prepared: SmvPrepared,
    ir: NetworkIR,
    *,
    emit_mode: str = "lif",
) -> str:
    """
    INPUT: same as ``emit_properties_block``.
    OUTPUT: standalone ``properties.smv`` body (file header + spec lines).
    """
    header = (
        "-- Auto-generated properties (snn_mc.smv.properties)\n"
        "-- Splice after MODULE main ASSIGN block, before neuron submodule tail (lif_* or bool_thr).\n\n"
    )
    return header + emit_properties_block(prepared, ir, emit_mode=emit_mode).lstrip("\n")
