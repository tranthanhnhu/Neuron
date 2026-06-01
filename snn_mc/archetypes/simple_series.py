"""
simple_series — linear chain of N neurons fed by one input.

DSL forms (interchangeable):
    block simple_series input=stim output=c4 neurons=n1,n2,n3        params=default
    block simple_series input=stim N=3   prefix=n  weights=3,2,5    threshold=4

Auto-properties:
    LTLSPEC (G (stim & (first.r_num >= 2))) -> (F last.spike)
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

from snn_mc.archetypes.block_helpers import exc_weights_for_chain, resolve_block_output
from snn_mc.ir import ArchetypeInstance, Composition, Edge
from snn_mc.archetypes.base import (
    ArchetypeBase,
    BlockApplyContext,
    expand_chain,
    stim_token,
)
from snn_mc.archetypes.graph_index import GraphIndex


class SimpleSeriesArchetype(ArchetypeBase):
    kind = "simple_series"

    @classmethod
    def apply_block(cls, kv: Dict[str, str], ctx: BlockApplyContext) -> None:
        pset = ctx.get("params", "default")
        stim = ctx.get("input", None)
        ns = expand_chain(kv, ctx, what="block simple_series")
        threshold: Optional[int] = None
        if "threshold" in kv:
            threshold = int(kv["threshold"])
        ctx.apply_threshold(ns, pset, threshold)
        out_port = resolve_block_output(kv, ns, line_no=ctx.line_no, what="block simple_series")

        edge_pairs: List[tuple[str, str]] = [(stim, ns[0])]
        edge_pairs.extend(zip(ns, ns[1:]))
        weights = exc_weights_for_chain(
            kv, ctx.line_no, len(edge_pairs), ctx.w_exc, what="block simple_series"
        )
        for (src, dst), w in zip(edge_pairs, weights):
            ctx.edges.append(Edge(src=src, dst=dst, weight=w))

        if len(ns) >= 2:
            ctx.compositions.append(
                Composition(kind="sequential", neurons=tuple(ns), inferred=False)
            )
        ctx.archetypes.append(
            ArchetypeInstance(
                kind=cls.kind,
                nodes=tuple(ns),
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
        ns = inst.nodes
        stim = stim_token(inst.inputs.get("stim"), neurons)
        if stim and len(ns) >= 2:
            first, last = ns[0], ns[-1]
            return [f"LTLSPEC (G ({stim} & ({first}.r_num >= 2))) -> (F {last}.spike)"]
        return []

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        insts: List[ArchetypeInstance] = []
        indeg = {n: 0 for n in idx.neurons}
        outdeg = {n: 0 for n in idx.neurons}
        next_map: Dict[str, str] = {}
        for (s, d) in idx.exc:
            if s in idx.neurons and d in idx.neurons:
                outdeg[s] += 1
                indeg[d] += 1
                if s not in next_map:
                    next_map[s] = d
        starts = [n for n in idx.neurons if indeg[n] == 0 and outdeg[n] == 1]
        for st in starts:
            chain: List[str] = [st]
            cur = st
            while cur in next_map and outdeg[cur] == 1:
                nxt = next_map[cur]
                if indeg[nxt] != 1:
                    break
                chain.append(nxt)
                cur = nxt
            if len(chain) >= 2:
                insts.append(
                    ArchetypeInstance(
                        kind=cls.kind,
                        nodes=tuple(chain),
                        inputs={},
                        meta={"output": chain[-1]},
                        explicit=False,
                    )
                )
        return insts
