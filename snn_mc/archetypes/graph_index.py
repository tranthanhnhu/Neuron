"""
Precomputed adjacency views over a NetworkIR graph.

Used by archetype ``detect`` methods to find patterns without re-walking ``edges`` every time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from snn_mc.ir import Edge


@dataclass
class GraphIndex:
    """
    Snapshot of the neuron-level graph plus split excitatory / inhibitory views.

    Fields are precomputed for cheap lookups during archetype detection.
    """

    neurons: Set[str]
    inputs: Set[str]
    exc: Set[Tuple[str, str]]
    inh: Set[Tuple[str, str]]
    exc_in_from_input: Dict[str, Set[str]]
    exc_out: Dict[str, Set[str]]
    exc_in: Dict[str, Set[str]]
    inh_out: Dict[str, Set[str]]
    inh_in: Dict[str, Set[str]]
    exc_adj: Dict[str, List[str]]


def build_graph_index(neurons: Set[str], inputs: Set[str], edges: List[Edge]) -> GraphIndex:
    """
    INPUT:  neurons + inputs + edge list from NetworkIR.
    OUTPUT: GraphIndex with excitatory / inhibitory adjacencies separated.
            ``exc_in_from_input[n]`` is the set of inputs that excite neuron ``n``.
    """
    exc: Set[Tuple[str, str]] = set()
    inh: Set[Tuple[str, str]] = set()
    exc_in_from_input: Dict[str, Set[str]] = {n: set() for n in neurons}
    exc_out: Dict[str, Set[str]] = {n: set() for n in neurons}
    exc_in: Dict[str, Set[str]] = {n: set() for n in neurons}
    inh_out: Dict[str, Set[str]] = {n: set() for n in neurons}
    inh_in: Dict[str, Set[str]] = {n: set() for n in neurons}

    for e in edges:
        if e.dst not in neurons:
            continue
        if e.weight >= 0:
            exc.add((e.src, e.dst))
            if e.src in neurons:
                exc_out[e.src].add(e.dst)
                exc_in[e.dst].add(e.src)
            elif e.src in inputs:
                exc_in_from_input[e.dst].add(e.src)
        else:
            inh.add((e.src, e.dst))
            if e.src in neurons:
                inh_out[e.src].add(e.dst)
                inh_in[e.dst].add(e.src)

    # Sorted adjacency list (excitatory only) — convenient for deterministic DFS.
    exc_adj: Dict[str, List[str]] = {n: [] for n in neurons}
    for e in edges:
        if e.weight >= 0 and e.src in neurons and e.dst in neurons:
            exc_adj[e.src].append(e.dst)
    for n in exc_adj:
        exc_adj[n] = sorted(exc_adj[n])

    return GraphIndex(
        neurons=neurons,
        inputs=inputs,
        exc=exc,
        inh=inh,
        exc_in_from_input=exc_in_from_input,
        exc_out=exc_out,
        exc_in=exc_in,
        inh_out=inh_out,
        inh_in=inh_in,
        exc_adj=exc_adj,
    )
