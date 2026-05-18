"""
positive_loop — excitatory ring of N neurons (no inhibition).

DSL forms:
    block positive_loop input=stim neurons=a,b,c       params=default
    block positive_loop input=stim N=3 prefix=p        params=default

Wiring: stim -> n1 -> ... -> nN -> n1 (last edge closes the ring excitatorily).
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

from snn_mc.ir import ArchetypeInstance, Edge
from snn_mc.archetypes.base import ArchetypeBase, BlockApplyContext, expand_chain
from snn_mc.archetypes.graph_index import GraphIndex


class PositiveLoopArchetype(ArchetypeBase):
    kind = "positive_loop"

    @classmethod
    def apply_block(cls, kv: Dict[str, str], ctx: BlockApplyContext) -> None:
        """OUTPUT: excitatory chain edges plus one excitatory back-edge (last -> first)."""
        pset = ctx.get("params", "default")
        stim = ctx.get("input", None)
        ns_list = expand_chain(kv, ctx, what="block positive_loop")
        for n in ns_list:
            ctx.ensure_neuron(n, pset)
        ctx.edges.append(Edge(src=stim, dst=ns_list[0], weight=ctx.w_exc))
        for a, b in zip(ns_list, ns_list[1:]):
            ctx.edges.append(Edge(src=a, dst=b, weight=ctx.w_exc))
        # Closing excitatory edge — sustains activity around the ring.
        ctx.edges.append(Edge(src=ns_list[-1], dst=ns_list[0], weight=ctx.w_exc))
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
        """OUTPUT: per-neuron reachability + forward propagation around the loop."""
        ns = inst.nodes
        if len(ns) < 2:
            return []
        lines = [f"CTLSPEC EF {n}.spike" for n in ns]
        for i in range(len(ns) - 1):
            lines.append(f"CTLSPEC AG ({ns[i]}.spike -> EF {ns[i + 1]}.spike)")
        lines.append(f"CTLSPEC AG ({ns[-1]}.spike -> EF {ns[0]}.spike)")
        return lines

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        # Graph detection of positive loops is ambiguous with simple_series rings; skip.
        return []
