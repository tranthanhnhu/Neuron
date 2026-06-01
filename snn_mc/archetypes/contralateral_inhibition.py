"""
contralateral_inhibition — N neurons all driven by one input, every pair inhibits each other.

DSL forms:
    block contralateral_inhibition input=stim L=l R=r            params=default
    block contralateral_inhibition input=stim neurons=l,r,m      params=default
    block contralateral_inhibition input=stim N=3 prefix=c       params=default
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from snn_mc.ir import ArchetypeInstance, Edge
from snn_mc.archetypes.base import (
    ArchetypeBase,
    BlockApplyContext,
    expand_chain,
    validate_archetype_list_size,
)
from snn_mc.archetypes.graph_index import GraphIndex


def _is_full_inh_digraph(nodes: Tuple[str, ...], inh: Set[Tuple[str, str]]) -> bool:
    for i in nodes:
        for j in nodes:
            if i != j and (i, j) not in inh:
                return False
    return True


class ContralateralInhibitionArchetype(ArchetypeBase):
    kind = "contralateral_inhibition"

    @classmethod
    def apply_block(cls, kv: Dict[str, str], ctx: BlockApplyContext) -> None:
        """OUTPUT: stim->ni excitatory edges + pairwise inhibitory edges (winner-takes-all)."""
        pset = ctx.get("params", "default")
        stim = ctx.get("input", None)
        has_lr = "L" in kv or "R" in kv
        has_chain = "neurons" in kv or "N" in kv or "prefix" in kv
        if has_lr and has_chain:
            raise ValueError(
                f"line {ctx.line_no}: contralateral_inhibition: use either L=/R= OR neurons=/N= (not mixed)"
            )
        if has_lr:
            if "L" not in kv or "R" not in kv:
                raise ValueError(
                    f"line {ctx.line_no}: contralateral_inhibition: L= and R= required together"
                )
            ns_list = [kv["L"], kv["R"]]
            validate_archetype_list_size(ctx.line_no, ns_list, what="block contralateral_inhibition L/R")
        else:
            ns_list = expand_chain(kv, ctx, what="block contralateral_inhibition")

        for n in ns_list:
            ctx.ensure_neuron(n, pset)
        for n in ns_list:
            ctx.edges.append(Edge(src=stim, dst=n, weight=ctx.w_exc))
        for i in range(len(ns_list)):
            for j in range(len(ns_list)):
                if i != j:
                    ctx.edges.append(Edge(src=ns_list[i], dst=ns_list[j], weight=ctx.w_inh))
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
        horizon: int = 20,
    ) -> List[str]:
        """OUTPUT: pairwise mutual exclusion + a steady-winner reachability for each neuron."""
        ns = list(inst.nodes)
        if len(ns) < 2:
            return []
        lines: List[str] = []
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                lines.append(f"CTLSPEC AG !({ns[i]}.spike & {ns[j]}.spike)")
        for ni in ns:
            others = " & ".join([f"!{nj}.spike" for nj in ns if nj != ni])
            lines.append(f"CTLSPEC EF (EG ({ni}.spike & {others}))")
        return lines

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        """Find maximal sets sharing an input and forming a full pairwise inhibitory digraph."""
        insts: List[ArchetypeInstance] = []
        for stim in idx.inputs:
            candidates = sorted(
                n for n in idx.neurons if stim in idx.exc_in_from_input.get(n, set())
            )
            if len(candidates) < 2:
                continue
            qual: List[frozenset[str]] = []
            for r in range(2, len(candidates) + 1):
                for comb in combinations(candidates, r):
                    if _is_full_inh_digraph(comb, idx.inh):
                        qual.append(frozenset(comb))
            for q in qual:
                if any(q < s for s in qual):
                    continue
                insts.append(
                    ArchetypeInstance(
                        kind=cls.kind,
                        nodes=tuple(sorted(q)),
                        inputs={"stim": stim},
                        meta={},
                        explicit=False,
                    )
                )
        return insts
