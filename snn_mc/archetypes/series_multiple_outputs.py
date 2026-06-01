"""
series_multiple_outputs — same wiring as simple_series, but every neuron is an observed output.

DSL forms:
    block series_multiple_outputs input=stim neurons=n1,n2,n3 params=default
    block series_multiple_outputs input=stim N=3 prefix=n      params=default
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

from snn_mc.archetypes.block_helpers import exc_weights_for_chain
from snn_mc.ir import ArchetypeInstance, Composition, Edge
from snn_mc.archetypes.base import ArchetypeBase, BlockApplyContext, expand_chain, stim_token
from snn_mc.archetypes.graph_index import GraphIndex


class SeriesMultipleOutputsArchetype(ArchetypeBase):
    kind = "series_multiple_outputs"

    @classmethod
    def apply_block(cls, kv: Dict[str, str], ctx: BlockApplyContext) -> None:
        """OUTPUT: same edges + sequential composition as simple_series; specs differ."""
        pset = ctx.get("params", "default")
        stim = ctx.get("input", None)
        ns = expand_chain(kv, ctx, what="block series_multiple_outputs")
        threshold = int(kv["threshold"]) if "threshold" in kv else None
        ctx.apply_threshold(ns, pset, threshold)
        edge_pairs = [(stim, ns[0])] + list(zip(ns, ns[1:]))
        weights = exc_weights_for_chain(
            kv, ctx.line_no, len(edge_pairs), ctx.w_exc, what="block series_multiple_outputs"
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
                meta={"output": ",".join(ns)},
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
        """OUTPUT: per-neuron reachability + global silence when stim is off."""
        ns = inst.nodes
        stim = stim_token(inst.inputs.get("stim"), neurons)
        lines = [f"CTLSPEC EF {n}.spike" for n in ns]
        if stim and ns:
            silent = " & ".join([f"!{n}.spike" for n in ns])
            lines.append(f"LTLSPEC (G !{stim}) -> (G ({silent}))")
        return lines

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        # Graph-based detection is ambiguous (simple_series covers the same pattern), skip.
        return []
