"""
positive_loop — excitatory ring of N neurons (no inhibition).

DSL forms:
    block positive_loop input=stim neurons=a,b,c       params=default
    block positive_loop input=stim N=3 prefix=p        params=default

Wiring: stim -> n1 -> ... -> nN -> n1 (last edge closes the ring excitatorily).
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

from snn_mc.archetypes.block_helpers import exc_weights_for_chain, resolve_block_output
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
        threshold = int(kv["threshold"]) if "threshold" in kv else None
        ctx.apply_threshold(ns_list, pset, threshold)
        out_port = resolve_block_output(
            kv, ns_list, line_no=ctx.line_no, what="block positive_loop"
        )
        exc_edges = [(stim, ns_list[0])] + list(zip(ns_list, ns_list[1:])) + [
            (ns_list[-1], ns_list[0])
        ]
        weights = exc_weights_for_chain(
            kv, ctx.line_no, len(exc_edges), ctx.w_exc, what="block positive_loop"
        )
        for (src, dst), w in zip(exc_edges, weights):
            ctx.edges.append(Edge(src=src, dst=dst, weight=w))
        ctx.archetypes.append(
            ArchetypeInstance(
                kind=cls.kind,
                nodes=tuple(ns_list),
                inputs={"stim": stim},
                meta={"output": out_port},
                explicit=True,
            )
        )

    @classmethod
    def specs(
        cls,
        inst: ArchetypeInstance,
        *,
        neurons: Optional[FrozenSet[str]] = None,
        horizon: int = 20,
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
