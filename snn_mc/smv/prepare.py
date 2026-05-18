"""
SmvPrepared: a derived, NuSMV-safe snapshot of NetworkIR.

INPUT (to ``prepare_ir``):  NetworkIR straight from the parser/composer.
OUTPUT (``SmvPrepared``):
    - Every identifier renamed for NuSMV (e.g. ``A`` -> ``n_A``).
    - Edges grouped per destination into excitatory and inhibitory source lists (LIF wiring).
    - Archetype list = explicit instances + graph-detected ones (deduplicated).
    - Composition list = explicit ``compose`` lines + optional inferred linear chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from snn_mc.archetypes import detect_archetypes
from snn_mc.identifiers import rename_in_spec_text, sanitize_identifier
from snn_mc.ir import (
    ArchetypeInstance,
    Composition,
    Edge,
    NetworkIR,
    ParamSpec,
)


@dataclass(frozen=True)
class SmvPrepared:
    """
    Renamed graph + helper tables consumed by every later SMV stage.

    Important fields (for tracing):
      - ``mapping`` / ``renames`` — DSL name -> NuSMV-safe name.
      - ``exc_srcs[n]`` / ``inh_srcs[n]`` — Boolean source expressions feeding neuron n.
      - ``arch_list`` — explicit + detected archetype instances (deduplicated).
      - ``compositions`` — explicit ``compose`` lines + optional inferred linear chain.
    """

    neurons: frozenset[str]
    inputs: frozenset[str]
    consts: Dict[str, bool]
    edges: Tuple[Edge, ...]
    neuron_params: Dict[str, str]
    schedules: Dict[str, List[bool]]
    compositions: Tuple[Composition, ...]
    arch_list: Tuple[ArchetypeInstance, ...]
    user_specs: Tuple[str, ...]
    neuron_roles: Dict[str, str]
    tie_s: Dict[str, str]
    var_inputs: Tuple[str, ...]
    neuron_list: Tuple[str, ...]
    exc_srcs: Dict[str, Tuple[str, ...]]
    inh_srcs: Dict[str, Tuple[str, ...]]
    param_specs: Dict[str, ParamSpec]
    mapping: Dict[str, str]
    renames: Dict[str, str]

    def rename(self, name: str) -> str:
        return self.mapping.get(name, name)


def or_of_sources(sources: List[str]) -> str:
    """
    INPUT: list of Boolean NuSMV expressions.
    OUTPUT: a single OR expression (``FALSE`` when empty, the expression itself when length 1).

    Used to feed ``x_exc`` / ``x_inh`` of every LIF instance: any excitatory source firing
    activates ``x_exc`` (and similarly for inhibition).
    """
    if not sources:
        return "FALSE"
    if len(sources) == 1:
        return sources[0]
    return "(" + " | ".join(sources) + ")"


def _infer_linear_chain(neurons: Set[str], edges: List[Edge]) -> Tuple[str, ...] | None:
    """OUTPUT: tuple ``(n1, n2, ..., nN)`` if the neuron-to-neuron graph is a single chain; else None."""
    if not neurons:
        return None
    nn_edges = [(e.src, e.dst) for e in edges if e.src in neurons and e.dst in neurons]
    if len(nn_edges) != len(neurons) - 1:
        return None
    out_map: Dict[str, str] = {}
    indeg: Dict[str, int] = {n: 0 for n in neurons}
    outdeg: Dict[str, int] = {n: 0 for n in neurons}
    for src, dst in nn_edges:
        if src in out_map and out_map[src] != dst:
            return None
        out_map[src] = dst
        indeg[dst] += 1
        outdeg[src] += 1
        if indeg[dst] > 1 or outdeg[src] > 1:
            return None
    starts = [n for n in neurons if indeg[n] == 0]
    ends = [n for n in neurons if outdeg[n] == 0]
    if len(starts) != 1 or len(ends) != 1:
        return None
    order: List[str] = []
    cur = starts[0]
    seen: Set[str] = set()
    while True:
        if cur in seen:
            return None
        seen.add(cur)
        order.append(cur)
        if cur not in out_map:
            break
        cur = out_map[cur]
    if len(order) != len(neurons):
        return None
    return tuple(order)


def _compositions_for_ir(
    neurons: Set[str],
    edges: List[Edge],
    compositions: List[Composition],
) -> List[Composition]:
    """If no explicit sequential composition is declared, append an inferred one when possible."""
    comps = list(compositions)
    if not any(c.kind == "sequential" for c in comps):
        chain = _infer_linear_chain(neurons, edges)
        if chain is not None and len(chain) >= 2:
            comps.append(Composition(kind="sequential", neurons=chain, inferred=True))
    return comps


def _build_arch_list(
    explicit: List[ArchetypeInstance],
    neurons: Set[str],
    inputs: Set[str],
    edges: List[Edge],
) -> List[ArchetypeInstance]:
    """
    INPUT: archetypes from the DSL ``block`` macros + the full graph.
    OUTPUT: explicit instances followed by any extra graph-detected instances not already covered.
    """
    out = list(explicit)
    explicit_keys = {(a.kind, a.nodes) for a in out if a.explicit}
    for it in detect_archetypes(neurons, inputs, edges):
        if (it.kind, it.nodes) not in explicit_keys:
            out.append(it)
    return out


def prepare_ir(ir: NetworkIR) -> SmvPrepared:
    """
    INPUT:  NetworkIR (DSL identifiers).
    OUTPUT: SmvPrepared with sanitized names, computed exc/inh wiring, and archetype list.
    RAISES: RuntimeError on tie cycles that escaped earlier validation.
    """
    neurons = set(ir.neurons)
    inputs = set(ir.inputs)
    consts = dict(ir.consts)
    edges = list(ir.edges)
    params_specs: Dict[str, ParamSpec] = dict(ir.params)
    neuron_params = dict(ir.neuron_params)
    compositions = list(ir.compositions)
    schedules = dict(ir.schedules)
    user_specs = list(ir.user_specs)
    archetypes = list(ir.archetypes)

    # Single sanitization pass for every name in the network.
    all_names: Set[str] = set(neurons) | set(inputs) | set(consts.keys())
    mapping: Dict[str, str] = {n: sanitize_identifier(n) for n in all_names}
    renames = {k: v for k, v in mapping.items() if k != v}

    def rn(name: str) -> str:
        return mapping.get(name, name)

    neurons = {rn(n) for n in neurons}
    inputs = {rn(i) for i in inputs}
    consts = {rn(k): v for k, v in consts.items()}
    edges = [Edge(src=rn(e.src), dst=rn(e.dst), weight=e.weight) for e in edges]
    neuron_params = {rn(k): v for k, v in neuron_params.items()}
    compositions = [
        Composition(kind=c.kind, neurons=tuple(rn(n) for n in c.neurons), inferred=c.inferred)
        for c in compositions
    ]
    schedules = {rn(k): v for k, v in schedules.items()}
    user_specs = [rename_in_spec_text(s, renames) for s in user_specs]
    neuron_roles = {rn(k): v for k, v in ir.neuron_roles.items()}
    tie_s: Dict[str, str] = {rn(k): rn(v) for k, v in ir.input_ties.items()}

    def root_inp(x: str) -> str:
        seen: Set[str] = set()
        cur = x
        while cur in tie_s:
            if cur in seen:
                raise RuntimeError("tie cycle slipped through validation")
            seen.add(cur)
            cur = tie_s[cur]
        return cur

    var_inputs = tuple(sorted(i for i in inputs if i not in tie_s))
    arch_list_s = [
        ArchetypeInstance(
            kind=a.kind,
            nodes=tuple(rn(n) for n in a.nodes),
            inputs={ik: rn(iv) for ik, iv in a.inputs.items()},
            meta={mk: (rn(mv) if mv in mapping else mv) for mk, mv in a.meta.items()},
            explicit=a.explicit,
        )
        for a in archetypes
    ]
    arch_list = _build_arch_list(arch_list_s, neurons, inputs, edges)
    comps = _compositions_for_ir(neurons, edges, compositions)

    # Group edges by destination into excitatory vs inhibitory Boolean sources.
    exc_srcs: Dict[str, List[str]] = {n: [] for n in neurons}
    inh_srcs: Dict[str, List[str]] = {n: [] for n in neurons}

    def src_expr(name: str) -> str:
        if name in inputs:
            return root_inp(name)
        if name in consts:
            return "TRUE" if consts[name] else "FALSE"
        return f"{name}.spike"

    for e in edges:
        if e.weight >= 0:
            exc_srcs[e.dst].append(src_expr(e.src))
        else:
            inh_srcs[e.dst].append(src_expr(e.src))

    neuron_list = tuple(sorted(neurons))
    exc_t = {n: tuple(exc_srcs[n]) for n in neurons}
    inh_t = {n: tuple(inh_srcs[n]) for n in neurons}

    return SmvPrepared(
        neurons=frozenset(neurons),
        inputs=frozenset(inputs),
        consts=consts,
        edges=tuple(edges),
        neuron_params=neuron_params,
        schedules=schedules,
        compositions=tuple(comps),
        arch_list=tuple(arch_list),
        user_specs=tuple(user_specs),
        neuron_roles=neuron_roles,
        tie_s=tie_s,
        var_inputs=var_inputs,
        neuron_list=neuron_list,
        exc_srcs=exc_t,
        inh_srcs=inh_t,
        param_specs=params_specs,
        mapping=mapping,
        renames=renames,
    )
