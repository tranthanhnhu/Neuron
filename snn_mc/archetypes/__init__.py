"""
Archetype registry and graph-based detection.

INPUTS:
    BLOCK_REGISTRY[kind]   -> ArchetypeBase subclass (used by the DSL parser for ``block <kind>``).
    detect_archetypes(...) -> list[ArchetypeInstance] inferred from the graph alone.
    archetype_specs(inst)  -> list[str] of NuSMV CTL/LTL spec lines for one instance.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple, Type

from snn_mc.ir import ArchetypeInstance, Edge

from snn_mc.archetypes.base import ArchetypeBase
from snn_mc.archetypes.contralateral_inhibition import ContralateralInhibitionArchetype
from snn_mc.archetypes.graph_index import build_graph_index
from snn_mc.archetypes.inhibition_of_behavior import InhibitionOfBehaviorArchetype
from snn_mc.archetypes.negative_loop import NegativeLoopArchetype
from snn_mc.archetypes.parallel_composition import ParallelCompositionArchetype
from snn_mc.archetypes.positive_loop import PositiveLoopArchetype
from snn_mc.archetypes.series_multiple_outputs import SeriesMultipleOutputsArchetype
from snn_mc.archetypes.simple_series import SimpleSeriesArchetype

BLOCK_REGISTRY: Dict[str, Type[ArchetypeBase]] = {
    SimpleSeriesArchetype.kind: SimpleSeriesArchetype,
    SeriesMultipleOutputsArchetype.kind: SeriesMultipleOutputsArchetype,
    ParallelCompositionArchetype.kind: ParallelCompositionArchetype,
    NegativeLoopArchetype.kind: NegativeLoopArchetype,
    PositiveLoopArchetype.kind: PositiveLoopArchetype,
    ContralateralInhibitionArchetype.kind: ContralateralInhibitionArchetype,
    InhibitionOfBehaviorArchetype.kind: InhibitionOfBehaviorArchetype,
}

# Detection order: more specific patterns before generic ones (so a negative_loop
# is not also reported as a parallel_composition with the same neurons).
DETECTION_ORDER: Tuple[Type[ArchetypeBase], ...] = (
    NegativeLoopArchetype,
    ContralateralInhibitionArchetype,
    InhibitionOfBehaviorArchetype,
    ParallelCompositionArchetype,
    SimpleSeriesArchetype,
)


def _dedup(insts: List[ArchetypeInstance]) -> List[ArchetypeInstance]:
    seen: Set[Tuple[str, Tuple[str, ...], Tuple[Tuple[str, str], ...]]] = set()
    out: List[ArchetypeInstance] = []
    for it in insts:
        key = (it.kind, tuple(it.nodes), tuple(sorted(it.inputs.items())))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def dedup_archetype_instances(insts: List[ArchetypeInstance]) -> List[ArchetypeInstance]:
    """Stable removal of duplicate archetype instances by (kind, nodes, inputs)."""
    return _dedup(insts)


def archetype_specs(
    inst: ArchetypeInstance,
    *,
    neurons: Optional[FrozenSet[str]] = None,
) -> List[str]:
    """
    INPUT: an ArchetypeInstance and (optionally) the neuron name set used by ``stim_token``.
    OUTPUT: spec lines from the instance's registered class (empty if unknown kind).
    """
    cls = BLOCK_REGISTRY.get(inst.kind)
    if cls is None:
        return []
    return cls.specs(inst, neurons=neurons)


def detect_archetypes(
    neurons: Set[str], inputs: Set[str], edges: List[Edge]
) -> List[ArchetypeInstance]:
    """
    INPUT: full graph (neurons, inputs, edges).
    OUTPUT: list of archetype instances inferred from topology in DETECTION_ORDER.
    """
    idx = build_graph_index(neurons, inputs, edges)
    insts: List[ArchetypeInstance] = []
    for cls in DETECTION_ORDER:
        insts.extend(cls.detect(idx))
    return _dedup(insts)


def get_block_class(kind: str) -> Type[ArchetypeBase]:
    """INPUT: archetype kind string. OUTPUT: ArchetypeBase subclass. RAISES KeyError if unknown."""
    if kind not in BLOCK_REGISTRY:
        raise KeyError(kind)
    return BLOCK_REGISTRY[kind]
