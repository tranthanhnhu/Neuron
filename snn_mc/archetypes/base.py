"""
Abstract base for archetype block handlers (used by ``block <kind> ...`` lines in DSL).

Each subclass implements:
    apply_block(kv, ctx)  — mutate the parse-time context (edges, compositions, archetypes).
    specs(inst)           — produce CTLSPEC/LTLSPEC lines for an ArchetypeInstance.
    detect(idx)           — recover archetypes from an already-built graph (optional).

PARAMETERIZED N:
    Most chain-like archetypes accept either an explicit list (``neurons=a,b,c``) or
    a generative form (``N=<int> prefix=<str>``).  ``expand_chain`` centralises this
    so each subclass simply calls it and gets back a neuron list of length N.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, List, Optional

from snn_mc.ir import ArchetypeInstance, Composition, Edge, ParamSpec
from snn_mc.archetypes.graph_index import GraphIndex


def stim_token(name: Optional[str], neurons: Optional[FrozenSet[str]]) -> Optional[str]:
    """
    Render a ``stim`` port for use inside a NuSMV spec.

    The DSL allows a block's ``input=`` to refer to either a true input (``stim``) or to
    another neuron's output (``c4``). In the latter case NuSMV needs ``c4.spike`` instead
    of the bare ``c4`` (a neuron is a submodule, not a boolean variable).

    INPUT:
        name     — value attached to ``inst.inputs["stim"]`` (may be ``None``).
        neurons  — set of neuron names (typically ``prepared.neurons``); may be ``None``.
    OUTPUT: same string when the source is an input, or ``"<name>.spike"`` when it is a neuron.
    """
    if name is None:
        return None
    if neurons and name in neurons:
        return f"{name}.spike"
    return name

# Explicit list bounds for the ``neurons=`` and ``outputs=`` arguments (thesis assumption: 2..10).
ARCHETYPE_LIST_MIN = 2
ARCHETYPE_LIST_MAX = 10


def validate_archetype_list_size(line_no: int, names: List[str], *, what: str) -> None:
    """
    INPUT: list of neuron / output names from a ``block`` macro.
    OUTPUT: None on success.
    RAISES: ValueError when the list is outside [ARCHETYPE_LIST_MIN, ARCHETYPE_LIST_MAX].
    """
    n = len(names)
    if n < ARCHETYPE_LIST_MIN or n > ARCHETYPE_LIST_MAX:
        raise ValueError(
            f"line {line_no}: {what} must list between {ARCHETYPE_LIST_MIN} and {ARCHETYPE_LIST_MAX} "
            f"names (comma-separated, no spaces inside the list); got {n}"
        )


@dataclass
class BlockApplyContext:
    """
    Mutable context handed to each ``ArchetypeBase.apply_block`` call by the parser.

    The block handler is expected to APPEND to ``edges``, ``compositions`` and
    ``archetypes`` (no replacement). ``ensure_neuron`` registers a neuron name
    and assigns it the requested parameter set.
    """

    line_no: int
    edges: List[Edge]
    compositions: List[Composition]
    archetypes: List[ArchetypeInstance]
    w_exc: int
    w_inh: int
    ensure_neuron: Callable[[str, str], None]
    get: Callable[[str, Optional[str]], str]
    get_int: Callable[[str, int], int]
    parse_csv_list: Callable[[str], List[str]]
    params: Dict[str, "ParamSpec"]  # noqa: F821 — forward ref
    neuron_params: Dict[str, str]
    apply_threshold: Callable[[List[str], str, Optional[int]], None]


def expand_chain(
    kv: Dict[str, str],
    ctx: BlockApplyContext,
    *,
    what: str,
) -> List[str]:
    """
    Resolve the neuron list for a chain-like archetype.

    INPUT (one of the two forms must be present in ``kv``):
      - ``neurons=n1,n2,...``                   — explicit list.
      - ``N=<int> prefix=<str>``                — generate ``<prefix>1`` .. ``<prefix>N``.
    OUTPUT: list of neuron names in chain order.
    RAISES: ValueError if both / neither form is given, or if N is out of bounds.

    ``what`` is a short label (e.g. ``"block simple_series"``) used in error messages.
    """
    has_list = "neurons" in kv
    has_n = "N" in kv or "prefix" in kv
    if has_list and has_n:
        raise ValueError(
            f"line {ctx.line_no}: {what}: use either neurons=... OR N=<int> prefix=<str>, not both"
        )
    if has_list:
        names = ctx.parse_csv_list(kv["neurons"])
        validate_archetype_list_size(ctx.line_no, names, what=f"{what} neurons=")
        return names
    if has_n:
        if "N" not in kv or "prefix" not in kv:
            raise ValueError(
                f"line {ctx.line_no}: {what}: N=<int> requires prefix=<str> (and vice versa)"
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
        prefix = kv["prefix"]
        if not prefix:
            raise ValueError(f"line {ctx.line_no}: {what}: prefix must be non-empty")
        return [f"{prefix}{i}" for i in range(1, n + 1)]
    raise ValueError(
        f"line {ctx.line_no}: {what}: missing both 'neurons=' and 'N=/prefix='"
    )


class ArchetypeBase(ABC):
    """Common contract for every archetype kind."""

    kind: str

    @classmethod
    @abstractmethod
    def apply_block(cls, kv: Dict[str, str], ctx: BlockApplyContext) -> None:
        """
        INPUT: parsed ``key=value`` pairs of the ``block`` line and the mutable parse context.
        OUTPUT: None. Side effects: append to ``ctx.edges`` / ``ctx.compositions`` / ``ctx.archetypes``.
        """

    @classmethod
    def specs(
        cls,
        inst: ArchetypeInstance,
        *,
        neurons: Optional[FrozenSet[str]] = None,
        horizon: int = 20,
    ) -> List[str]:
        """
        INPUT: matched archetype instance and (optionally) the set of neuron names so that
               ``stim`` references can be disambiguated from neurons (see ``stim_token``).
        OUTPUT: CTLSPEC / LTLSPEC spec lines for NuSMV.
        """
        return []

    @classmethod
    def detect(cls, idx: GraphIndex) -> List[ArchetypeInstance]:
        """INPUT: precomputed graph index. OUTPUT: instances inferred without DSL macros."""
        return []
