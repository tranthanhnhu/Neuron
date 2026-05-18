"""
negative_loop — N neurons chained excitatorily with an inhibitory back-edge that closes the loop.

DSL forms:
    block negative_loop input=stim A=a B=b                params=default        # 2-neuron loop
    block negative_loop input=stim neurons=a,b,c          params=default        # N-neuron loop
    block negative_loop input=stim N=3 prefix=r           params=default        # generated names

Wiring: stim -> n1 -> n2 -> ... -> nN  and  nN -|inh|- n1.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from snn_mc.ir import ArchetypeInstance, Edge
from snn_mc.archetypes.base import (
    ArchetypeBase,
    BlockApplyContext,
    expand_chain,
    stim_token,
    validate_archetype_list_size,
)
from snn_mc.archetypes.graph_index import GraphIndex


def _longest_simple_exc_path(
    start: str,
    goal: str,
    exc_adj: Dict[str, List[str]],
    max_vertices: int,
) -> Optional[Tuple[str, ...]]:
    """DFS that returns the longest simple excitatory path from ``start`` to ``goal``."""
    best: Optional[Tuple[str, ...]] = None

    def dfs(cur: str, visited: Set[str], path: List[str]) -> None:
        nonlocal best
        if cur == goal and len(path) >= 2:
            cand = tuple(path)
            if best is None or len(cand) > len(best):
                best = cand
            return
        if len(path) >= max_vertices:
            return
        for nxt in exc_adj.get(cur, []):
            if nxt not in visited:
                dfs(nxt, visited | {nxt}, path + [nxt])

    dfs(start, {start}, [start])
    return best


class NegativeLoopArchetype(ArchetypeBase):
    kind = "negative_loop"

    @classmethod
    def apply_block(cls, kv: Dict[str, str], ctx: BlockApplyContext) -> None:
        """
        Accept three equivalent forms:
          1. ``A=<x> B=<y>`` (two-neuron loop — legacy convenience).
          2. ``neurons=n1,n2,...``.
          3. ``N=<int> prefix=<str>`` (parameterized).
        OUTPUT: excitatory chain edges + one inhibitory back-edge from last to first.
        """
        pset = ctx.get("params", "default")
        stim = ctx.get("input", None)
        has_ab = "A" in kv or "B" in kv
        has_chain = "neurons" in kv or "N" in kv or "prefix" in kv

        if has_ab and has_chain:
            raise ValueError(
                f"line {ctx.line_no}: negative_loop: use either A=/B= OR neurons= / N= (not mixed)"
            )

        if has_ab:
            if "A" not in kv or "B" not in kv:
                raise ValueError(f"line {ctx.line_no}: negative_loop: A= and B= required together")
            ns_list = [kv["A"], kv["B"]]
            validate_archetype_list_size(ctx.line_no, ns_list, what="block negative_loop A/B")
        else:
            ns_list = expand_chain(kv, ctx, what="block negative_loop")

        for n in ns_list:
            ctx.ensure_neuron(n, pset)
        ctx.edges.append(Edge(src=stim, dst=ns_list[0], weight=ctx.w_exc))
        for a, b in zip(ns_list, ns_list[1:]):
            ctx.edges.append(Edge(src=a, dst=b, weight=ctx.w_exc))
        # Closing inhibitory edge — the feedback that gives the loop its negative-loop name.
        ctx.edges.append(Edge(src=ns_list[-1], dst=ns_list[0], weight=ctx.w_inh))
        ctx.archetypes.append(
            ArchetypeInstance(
                kind=cls.kind,
                nodes=tuple(ns_list),
                inputs={"stim": stim},
                meta={},
                explicit=True,
            )
        )

    @classmethod
    def specs(
        cls,
        inst: ArchetypeInstance,
        *,
        neurons: Optional[FrozenSet[str]] = None,
    ) -> List[str]:
        """
        OUTPUT: mutual exclusion of first/last, forward reachability, per-neuron liveness,
                and optional oscillation candidates that depend on schedule tuning.
        """
        ns = inst.nodes
        if len(ns) < 2:
            return []
        n_first, n_last = ns[0], ns[-1]
        specs: List[str] = [
            f"CTLSPEC AG !({n_first}.spike & {n_last}.spike)",
        ]
        for i in range(len(ns) - 1):
            specs.append(f"CTLSPEC AG ({ns[i]}.spike -> EF {ns[i + 1]}.spike)")
        for n in ns:
            specs.append(f"CTLSPEC EF {n}.spike")
        stim = stim_token(inst.inputs.get("stim"), neurons)
        if stim:
            # NuSMV's parser dislikes the glued ``GF`` token in front of a dotted name
            # (e.g. ``GF c4.spike``); use the spelled-out ``G F (...)`` form everywhere
            # so the same template renders for both inputs and submodule references.
            specs.append(
                "-- Oscillation candidates (may fail without tuning schedule or LIF params)"
            )
            specs.append(
                f"LTLSPEC (G F ({stim})) -> ((G F ({n_last}.spike)) & (G F (!({n_last}.spike))))"
            )
            if len(ns) == 2:
                specs.append(
                    f"LTLSPEC (G F ({stim})) -> ((G F ({n_first}.spike & !{n_last}.spike)) "
                    f"& (G F (!{n_first}.spike & {n_last}.spike)))"
                )
        return specs

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        """Find chains whose end inhibits the start (and whose start is excited from an input)."""
        insts: List[ArchetypeInstance] = []
        for b_inhib, a_target in idx.inh:
            if b_inhib not in idx.neurons or a_target not in idx.neurons:
                continue
            if not idx.exc_in_from_input.get(a_target):
                continue
            path = _longest_simple_exc_path(
                a_target, b_inhib, idx.exc_adj, len(idx.neurons)
            )
            if path is None:
                continue
            insts.append(
                ArchetypeInstance(
                    kind=cls.kind,
                    nodes=path,
                    inputs={},
                    meta={},
                    explicit=False,
                )
            )
        return insts
