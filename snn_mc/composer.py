"""
Composer: semantic checks performed AFTER parsing and BEFORE SMV emission.

INPUT:  NetworkIR straight from the parser.
OUTPUT: NetworkIR ready for emission (same object on success; ValueError on violation).

CHECKS:
    1. Every ``block`` ``input=`` argument refers to a declared input OR an already-declared
       neuron (this enables ``block negative_loop input=c4 ...`` where ``c4`` came from a
       previous ``block simple_series``).
    2. Optional ``roles`` keys (``LEAD`` / ``FOLLOWER`` / ``FOLLOWERS``) match the archetype's
       wiring (e.g. chain head is the LEAD; parallel hub is the LEAD; others are FOLLOWERS).
"""

from __future__ import annotations

from typing import FrozenSet

from snn_mc.ir import NetworkIR

# Archetypes that have a single "head" neuron driving the rest of the chain.
_CHAIN_ARCH_KINDS: FrozenSet[str] = frozenset(
    {"simple_series", "series_multiple_outputs", "negative_loop", "positive_loop"}
)


def compose(ir: NetworkIR) -> NetworkIR:
    """
    INPUT: NetworkIR from the parser.
    OUTPUT: same NetworkIR after semantic validation.
    RAISES: ValueError if a block references an unknown name, or roles disagree with wiring.
    """
    _validate_block_inputs(ir)
    _validate_outputs(ir)
    _validate_roles_vs_archetypes(ir)
    return ir


def _validate_outputs(ir: NetworkIR) -> None:
    """Every declared network or block output must name a known neuron."""
    valid = set(ir.neurons) | set(ir.inputs) | set(ir.consts.keys())
    for out in ir.network_outputs:
        if out not in valid:
            raise ValueError(
                f"compose: network output '{out}' is unknown; declare it as a neuron first."
            )
    for inst in ir.archetypes:
        out = inst.meta.get("output")
        if out and out not in valid:
            raise ValueError(
                f"compose: archetype '{inst.kind}' output '{out}' is not a declared neuron."
            )


def _validate_block_inputs(ir: NetworkIR) -> None:
    """
    Each archetype carries ``inputs={..., "stim": <name>}``. The referenced name must be
    either a declared DSL input OR a neuron that was previously declared. The latter case
    is what lets the user feed one archetype's output into another's input:

        block simple_series  input=stim N=4 prefix=c
        block negative_loop  input=c4 A=a B=b
    """
    valid_names = set(ir.inputs) | set(ir.neurons) | set(ir.consts.keys())
    for inst in ir.archetypes:
        for port_name, ref in inst.inputs.items():
            if ref is None:
                continue
            if ref not in valid_names:
                raise ValueError(
                    f"compose: archetype '{inst.kind}' references unknown {port_name}='{ref}'. "
                    f"Declare it with 'input' or as a neuron before the block uses it."
                )


def _role_upper(ir: NetworkIR, neuron: str) -> str:
    return (ir.neuron_roles.get(neuron) or "").strip().upper()


def _validate_roles_vs_archetypes(ir: NetworkIR) -> None:
    """
    Validate role labels declared via ``roles n1=LEAD,n2=FOLLOWER,...`` against archetype wiring.

    A neuron labelled ``LEAD`` in a chain archetype must be the chain head; everyone else must
    be ``FOLLOWER`` / ``FOLLOWERS``. A ``parallel_composition`` hub must be the only ``LEAD``.
    """
    for inst in ir.archetypes:
        if inst.kind in _CHAIN_ARCH_KINDS:
            if not inst.nodes:
                continue
            head = inst.nodes[0]
            for i, n in enumerate(inst.nodes):
                role = _role_upper(ir, n)
                if not role:
                    continue
                if i == 0 and role not in ("LEAD",):
                    raise ValueError(
                        f"compose: in {inst.kind}, head neuron '{n}' has role={role!r} but expected LEAD"
                    )
                if i > 0 and role not in ("FOLLOWER", "FOLLOWERS"):
                    raise ValueError(
                        f"compose: in {inst.kind}, non-head neuron '{n}' has role={role!r} "
                        f"but expected FOLLOWER/FOLLOWERS"
                    )
                _ = head  # variable kept for readability; explicit head reference.

        elif inst.kind == "parallel_composition":
            src = inst.meta.get("src") or (inst.nodes[0] if inst.nodes else None)
            if src is None:
                continue
            for n in inst.nodes:
                role = _role_upper(ir, n)
                if not role:
                    continue
                if n == src and role != "LEAD":
                    raise ValueError(
                        f"compose: in parallel_composition, hub '{n}' has role={role!r} but expected LEAD"
                    )
                if n != src and role not in ("FOLLOWER", "FOLLOWERS"):
                    raise ValueError(
                        f"compose: in parallel_composition, output '{n}' has role={role!r} "
                        f"but expected FOLLOWER/FOLLOWERS"
                    )
