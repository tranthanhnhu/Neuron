"""
parallel_composition — one source neuron fans out to N output neurons in parallel.

DSL forms:
    block parallel_composition input=stim src=src outputs=a,b,c     params=default
    block parallel_composition input=stim src=src N=3 prefix=out    params=default
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

from snn_mc.ir import ArchetypeInstance, Composition, Edge
from snn_mc.archetypes.base import (
    ArchetypeBase,
    BlockApplyContext,
    stim_token,
    validate_archetype_list_size,
    ARCHETYPE_LIST_MIN,
    ARCHETYPE_LIST_MAX,
)
from snn_mc.archetypes.graph_index import GraphIndex


def _expand_outputs(kv: Dict[str, str], ctx: BlockApplyContext) -> List[str]:
    """Same logic as expand_chain but reads ``outputs=`` instead of ``neurons=``."""
    has_list = "outputs" in kv
    has_n = "N" in kv or "prefix" in kv
    what = "block parallel_composition"
    if has_list and has_n:
        raise ValueError(
            f"line {ctx.line_no}: {what}: use either outputs=... OR N=/prefix=, not both"
        )
    if has_list:
        names = ctx.parse_csv_list(kv["outputs"])
        validate_archetype_list_size(ctx.line_no, names, what=f"{what} outputs=")
        return names
    if has_n:
        if "N" not in kv or "prefix" not in kv:
            raise ValueError(
                f"line {ctx.line_no}: {what}: N=<int> requires prefix=<str>"
            )
        try:
            n = int(kv["N"])
        except ValueError as exc:
            raise ValueError(f"line {ctx.line_no}: {what}: N must be an integer") from exc
        if n < ARCHETYPE_LIST_MIN or n > ARCHETYPE_LIST_MAX:
            raise ValueError(
                f"line {ctx.line_no}: {what}: N={n} out of range "
                f"[{ARCHETYPE_LIST_MIN}, {ARCHETYPE_LIST_MAX}]"
            )
        return [f"{kv['prefix']}{i}" for i in range(1, n + 1)]
    raise ValueError(f"line {ctx.line_no}: {what}: missing both 'outputs=' and 'N=/prefix='")


class ParallelCompositionArchetype(ArchetypeBase):
    kind = "parallel_composition"

    @classmethod
    def apply_block(cls, kv: Dict[str, str], ctx: BlockApplyContext) -> None:
        """OUTPUT: edges ``stim->src`` and ``src->oi`` for every output, plus a parallel composition."""
        pset = ctx.get("params", "default")
        stim = ctx.get("input", None)
        src = ctx.get("src", None)
        outs = _expand_outputs(kv, ctx)
        ctx.ensure_neuron(src, pset)
        for o in outs:
            ctx.ensure_neuron(o, pset)
        ctx.edges.append(Edge(src=stim, dst=src, weight=ctx.w_exc))
        for o in outs:
            ctx.edges.append(Edge(src=src, dst=o, weight=ctx.w_exc))
        if len(outs) >= 2:
            ctx.compositions.append(
                Composition(kind="parallel", neurons=tuple(outs), inferred=False)
            )
        ctx.archetypes.append(
            ArchetypeInstance(
                kind=cls.kind,
                nodes=tuple([src] + outs),
                inputs={"stim": stim},
                meta={"src": src, "outputs": list(outs)},
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
        """OUTPUT: per-output reachability + liveness when the source spikes."""
        ns = inst.nodes
        stim = stim_token(inst.inputs.get("stim"), neurons)
        src = inst.meta.get("src") or (ns[0] if ns else None)
        outs = [n for n in ns if n != src]
        lines = [f"CTLSPEC EF {n}.spike" for n in ns]
        if stim and src and outs:
            or_out = " | ".join([f"{o}.spike" for o in outs])
            lines.append(f"LTLSPEC (G {stim}) -> (F ({or_out}))")
        return lines

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        """OUTPUT: any neuron with >= 2 excitatory fan-outs is a parallel hub."""
        insts: List[ArchetypeInstance] = []
        for src in idx.neurons:
            outs = sorted(idx.exc_out.get(src, set()))
            if len(outs) >= 2:
                insts.append(
                    ArchetypeInstance(
                        kind=cls.kind,
                        nodes=tuple([src] + outs),
                        inputs={},
                        meta={"src": src, "outputs": list(outs)},
                        explicit=False,
                    )
                )
        return insts
