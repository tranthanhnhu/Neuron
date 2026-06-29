"""
inhibition_of_behavior — neuron I gates neuron T (when I spikes, T cannot).

DSL form:
    block inhibition_of_behavior stimI=sI stimT=sT I=i T=t params=default
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

from snn_mc.ir import ArchetypeInstance, Edge
from snn_mc.archetypes.base import ArchetypeBase, BlockApplyContext, stim_token
from snn_mc.archetypes.graph_index import GraphIndex
from snn_mc.archetypes.spec_templates import ef_each, section


class InhibitionOfBehaviorArchetype(ArchetypeBase):
    kind = "inhibition_of_behavior"

    @classmethod
    def apply_block(cls, kv: Dict[str, str], ctx: BlockApplyContext) -> None:
        """
        INPUT: ``stimI=`` (input that drives I), ``stimT=`` (input for T), ``I=`` (inhibitor), ``T=`` (target).
        OUTPUT: two excitatory edges (stim*->I, stim*->T) and one inhibitory edge (I -> T).
        """
        pset = ctx.get("params", "default")
        stim_i = ctx.get("stimI", None)
        stim_t = ctx.get("stimT", None)
        i = ctx.get("I", None)
        t_ = ctx.get("T", None)
        ctx.ensure_neuron(i, pset)
        ctx.ensure_neuron(t_, pset)
        ctx.edges.append(Edge(src=stim_i, dst=i, weight=ctx.w_exc))
        ctx.edges.append(Edge(src=stim_t, dst=t_, weight=ctx.w_exc))
        ctx.edges.append(Edge(src=i, dst=t_, weight=ctx.w_inh))
        ctx.archetypes.append(
            ArchetypeInstance(
                kind=cls.kind,
                nodes=(i, t_),
                inputs={"stimI": stim_i, "stimT": stim_t},
                meta={"outputs": [i, t_]},
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
        """OUTPUT: inhibition gating, release under stimT, and per-neuron reachability."""
        ns = inst.nodes
        if len(ns) < 2:
            return []
        i, t = ns[0], ns[1]
        stim_t = stim_token(inst.inputs.get("stimT"), neurons)
        lines: List[str] = []
        lines.extend(ef_each([i, t]))
        lines.append(section("Inhibition-gating"))
        lines.append(f"LTLSPEC (G {i}.spike) -> (G !{t}.spike)")
        lines.append(f"CTLSPEC AG ({i}.spike -> AG !{t}.spike)")
        if stim_t:
            lines.append(section("Release"))
            lines.append(
                f"LTLSPEC (G ({stim_t} & !{i}.spike)) -> (F {t}.spike)"
            )
        return lines

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        """Find pairs (I, T) where I inhibits T (but T does not inhibit I) and both receive inputs."""
        insts: List[ArchetypeInstance] = []
        for i in idx.neurons:
            for t in idx.inh_out.get(i, set()):
                if t not in idx.neurons:
                    continue
                if i in idx.inh_out.get(t, set()):
                    continue
                if idx.exc_in_from_input.get(i, set()) and idx.exc_in_from_input.get(t, set()):
                    insts.append(
                        ArchetypeInstance(
                            kind=cls.kind,
                            nodes=(i, t),
                            inputs={
                                "stimI": sorted(idx.exc_in_from_input[i])[0],
                                "stimT": sorted(idx.exc_in_from_input[t])[0],
                            },
                            meta={"outputs": [i, t]},
                            explicit=False,
                        )
                    )
        return insts
