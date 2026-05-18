"""
simple_series — linear chain of N neurons fed by one input.

DSL forms (interchangeable):
    block simple_series input=stim neurons=n1,n2,n3        params=default
    block simple_series input=stim N=3   prefix=n          params=default

Auto-properties:
    LTLSPEC (G (stim & (first.r_num >= 2))) -> (F last.spike)
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

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
        """
        INPUT: ``kv`` with ``input=`` (required) and either ``neurons=`` or ``N=/prefix=``.
        OUTPUT: appends edges (stim->n1, n1->n2, ..., nN-1->nN), one sequential composition,
                and one explicit ArchetypeInstance to ``ctx``.
        """
        pset = ctx.get("params", "default")
        stim = ctx.get("input", None)
        ns = expand_chain(kv, ctx, what="block simple_series")
        for n in ns:
            ctx.ensure_neuron(n, pset)
        ctx.edges.append(Edge(src=stim, dst=ns[0], weight=ctx.w_exc))
        for a, b in zip(ns, ns[1:]):
            ctx.edges.append(Edge(src=a, dst=b, weight=ctx.w_exc))
        if len(ns) >= 2:
            ctx.compositions.append(
                Composition(kind="sequential", neurons=tuple(ns), inferred=False)
            )
        ctx.archetypes.append(
            ArchetypeInstance(
                kind=cls.kind,
                nodes=tuple(ns),
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
        """OUTPUT: liveness — sustained input eventually drives the last neuron to spike."""
        ns = inst.nodes
        stim = stim_token(inst.inputs.get("stim"), neurons)
        if stim and len(ns) >= 2:
            first, last = ns[0], ns[-1]
            return [f"LTLSPEC (G ({stim} & ({first}.r_num >= 2))) -> (F {last}.spike)"]
        return []

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        """OUTPUT: every maximal indeg=1/outdeg=1 excitatory chain (length >= 2)."""
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
                        meta={},
                        explicit=False,
                    )
                )
        return insts
