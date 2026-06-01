"""
negative_loop — N neurons chained excitatorily with an inhibitory back-edge that closes the loop.

DSL forms:
    block negative_loop input=c4 output=b A=a B=b exc_weights=3,3 inh_weight=3 threshold=4
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from snn_mc.archetypes.block_helpers import (
    exc_weights_for_chain,
    inh_weight_from_kv,
    resolve_block_output,
)
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

        threshold: Optional[int] = int(kv["threshold"]) if "threshold" in kv else None
        ctx.apply_threshold(ns_list, pset, threshold)
        out_port = resolve_block_output(
            kv, ns_list, line_no=ctx.line_no, what="block negative_loop"
        )

        exc_edges: List[tuple[str, str]] = [(stim, ns_list[0])]
        exc_edges.extend(zip(ns_list, ns_list[1:]))
        exc_ws = exc_weights_for_chain(
            kv, ctx.line_no, len(exc_edges), ctx.w_exc, what="block negative_loop"
        )
        for (src, dst), w in zip(exc_edges, exc_ws):
            ctx.edges.append(Edge(src=src, dst=dst, weight=w))
        ctx.edges.append(
            Edge(
                src=ns_list[-1],
                dst=ns_list[0],
                weight=inh_weight_from_kv(kv, ctx.w_inh),
            )
        )
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
        ns = inst.nodes
        if len(ns) < 2:
            return []
        n_first, n_last = ns[0], ns[-1]
        h = horizon
        specs: List[str] = [
            f"CTLSPEC AG !({n_first}.spike & {n_last}.spike)",
        ]
        for i in range(len(ns) - 1):
            specs.append(
                f"LTLSPEC G (({ns[i]}.spike & t < {h}) -> (F (t <= {h} & {ns[i + 1]}.spike)))"
            )
        for n in ns:
            specs.append(f"CTLSPEC EF {n}.spike")
        stim = stim_token(inst.inputs.get("stim"), neurons)
        if stim and len(ns) == 2:
            specs.append(
                "-- Bounded alternation (optional; tune schedule / LIF if this fails)"
            )
            specs.append(
                f"LTLSPEC G (({stim} & t < {h}) -> F (t <= {h} & {n_last}.spike & !{n_first}.spike))"
            )
        return specs

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
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
                    meta={"output": path[-1]},
                    explicit=False,
                )
            )
        return insts
