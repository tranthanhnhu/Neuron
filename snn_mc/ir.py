"""
Intermediate Representation (IR) for the DSL pipeline.

The IR is the SINGLE source of truth shared by every later stage:
    parser -> NetworkIR -> composer -> smv emitter -> property generator.

DATA CLASSES:
    Edge                — directed synapse (src -> dst) with signed integer weight.
    ParamSpec           — LIF parameter bundle (tau, w_exc, w_inh, S, R_init, Pmax).
    Composition         — sequential or parallel composition declared by the user.
    ArchetypeInstance   — an archetype matched (explicit ``block`` or graph-detected).
    NetworkIR           — full network description used downstream.

HELPERS:
    merge_network_ir(base, extra)        -> NetworkIR
    apply_prefix_to_ir(ir, prefix)       -> (NetworkIR, rename_map)
    parse_kv_pairs(tokens)               -> dict[str, str]
    parse_roles_csv(s)                   -> dict[str, str]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from snn_mc.identifiers import rename_in_spec_text


@dataclass(frozen=True)
class Edge:
    """A weighted directed synapse. ``weight >= 0`` is excitatory, ``weight < 0`` is inhibitory."""

    src: str
    dst: str
    weight: int


@dataclass(frozen=True)
class ParamSpec:
    """
    LIF parameter set. The same bundle is reused by every neuron declared with ``params=<name>``.

    Fields (all integers — NuSMV needs finite domains):
      - ``tau``     firing threshold.
      - ``w_exc``   weight of every excitatory edge entering the neuron (>= 0).
      - ``w_inh``   weight of every inhibitory edge entering the neuron (<= 0).
      - ``S``       leak denominator. Effective leak rate is ``R_init / S`` in [0, 1].
      - ``R_init``  initial numerator of the leak; non-deterministic later.
      - ``Pmax``    upper clamp on the membrane potential.
    """

    name: str
    tau: int
    w_exc: int
    w_inh: int
    S: int
    R_init: int
    Pmax: int


@dataclass(frozen=True)
class Composition:
    """
    Declared composition between neurons. Kind is ``"sequential"`` or ``"parallel"``.

    ``inferred=True`` means the composition was deduced from edges (legacy behaviour)
    rather than declared by the user via ``compose`` lines.
    """

    kind: str
    neurons: Tuple[str, ...]
    inferred: bool = False


@dataclass(frozen=True)
class ArchetypeInstance:
    """
    A recognised archetype occurrence in the network.

    ``kind`` is one of: ``simple_series``, ``series_multiple_outputs``,
    ``parallel_composition``, ``negative_loop``, ``positive_loop``,
    ``contralateral_inhibition``, ``inhibition_of_behavior``.

    ``nodes``    — neurons participating in the instance.
    ``inputs``   — mapping of semantic input names (e.g. ``"stim"``) to DSL input names.
    ``meta``     — extra key-values (e.g. ``src`` for parallel_composition, ``roles=...``).
    ``explicit`` — True if the user wrote ``block <kind> ...``; False if graph-detected.
    """

    kind: str
    nodes: Tuple[str, ...]
    inputs: Dict[str, str]
    meta: Dict[str, str]
    explicit: bool = False


@dataclass(frozen=True)
class InstanceImport:
    """``instance <Id> = <path>`` declaration — a sub-DSL pulled into the parent network."""

    inst_id: str
    path: str
    prefix: str


@dataclass(frozen=True)
class InstanceWire:
    """``wire <Inst>.<port> -> <Inst>.<port> weight <w>`` (resolved to a neuron-level Edge later)."""

    src_inst: str
    src_port: str
    dst_inst: str
    dst_port: str
    weight: int


@dataclass(frozen=True)
class NetworkIR:
    """
    Full network description after parsing.

    Drives:
      - ``smv.model`` (neurons + inputs + edges -> MODULE main wiring),
      - ``smv.properties`` (compositions + archetypes + user_specs -> CTL/LTL),
      - ``smv.lif_module`` (params -> MODULE lif_<name>).
    """

    neurons: Set[str]
    inputs: Set[str]
    consts: Dict[str, bool]
    edges: List[Edge]
    params: Dict[str, ParamSpec]
    neuron_params: Dict[str, str]
    compositions: List[Composition]
    schedules: Dict[str, List[bool]]
    user_specs: List[str]
    archetypes: List[ArchetypeInstance]
    prototype_name: Optional[str] = None
    strict_two_port: bool = False
    neuron_roles: Dict[str, str] = field(default_factory=dict)
    # logical_port -> ("neuron" | "input", internal_name)
    prototype_ports: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    instance_imports: Tuple[InstanceImport, ...] = ()
    instance_wires: Tuple[InstanceWire, ...] = ()
    # Resolved neuron-level wires from ``wire`` lines, used for comments / boundary specs.
    instance_wire_edges: Tuple[Edge, ...] = ()
    # Slave input -> master input. Emitter writes slave as a DEFINE alias instead of a VAR.
    input_ties: Dict[str, str] = field(default_factory=dict)
    # Discrete simulation horizon: global clock ``t`` ranges ``0..horizon`` in NuSMV.
    horizon: int = 20
    # Declared network-level output neurons (observation / composition ports).
    network_outputs: Tuple[str, ...] = ()


def clone_param_with_tau(
    params: Dict[str, ParamSpec],
    base_name: str,
    tau: int,
) -> str:
    """
    Ensure a ParamSpec named ``{base_name}_tau{tau}`` exists (copy of ``base_name`` with new tau).
    OUTPUT: param-set name to attach to neurons.
    """
    key = f"{base_name}_tau{tau}"
    if key in params:
        return key
    if base_name not in params:
        raise ValueError(f"Unknown param-set '{base_name}'")
    b = params[base_name]
    params[key] = ParamSpec(
        name=key,
        tau=tau,
        w_exc=b.w_exc,
        w_inh=b.w_inh,
        S=b.S,
        R_init=b.R_init,
        Pmax=b.Pmax,
    )
    return key


def parse_kv_pairs(tokens: List[str]) -> Dict[str, str]:
    """
    INPUT: list of tokens like ``["input=stim", "N=4", "prefix=c"]``.
    OUTPUT: dict ``{"input": "stim", "N": "4", "prefix": "c"}``.
    RAISES: ValueError if any token lacks ``=``.
    """
    out: Dict[str, str] = {}
    for tok in tokens:
        if "=" not in tok:
            raise ValueError(f"Expected key=value, got: {tok}")
        k, v = tok.split("=", 1)
        out[k] = v
    return out


def parse_roles_csv(s: str) -> Dict[str, str]:
    """
    INPUT: a CSV like ``"n1=driver,n2=relay"``.
    OUTPUT: ``{"n1": "driver", "n2": "relay"}``.
    """
    out: Dict[str, str] = {}
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"roles entry must be name=role, got: {part}")
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if not k or not v:
            raise ValueError(f"roles entry must be name=role, got: {part}")
        out[k] = v
    return out


def merge_network_ir(base: NetworkIR, extra: NetworkIR) -> NetworkIR:
    """
    Disjoint union of two IRs.

    INPUT: two IR objects (caller must guarantee disjoint neuron / input / const names).
    OUTPUT: combined IR. Parameters are merged via dict update; ``strict_two_port`` of
            the base wins (only the enclosing DSL controls final validation).
    """
    return NetworkIR(
        neurons=set(base.neurons) | set(extra.neurons),
        inputs=set(base.inputs) | set(extra.inputs),
        consts={**base.consts, **extra.consts},
        edges=list(base.edges) + list(extra.edges),
        params={**base.params, **extra.params},
        neuron_params={**base.neuron_params, **extra.neuron_params},
        compositions=list(base.compositions) + list(extra.compositions),
        schedules={**base.schedules, **extra.schedules},
        user_specs=list(base.user_specs) + list(extra.user_specs),
        archetypes=list(base.archetypes) + list(extra.archetypes),
        prototype_name=base.prototype_name or extra.prototype_name,
        strict_two_port=base.strict_two_port,
        neuron_roles={**base.neuron_roles, **extra.neuron_roles},
        prototype_ports={**base.prototype_ports, **extra.prototype_ports},
        instance_imports=tuple(base.instance_imports) + tuple(extra.instance_imports),
        instance_wires=tuple(base.instance_wires) + tuple(extra.instance_wires),
        instance_wire_edges=tuple(base.instance_wire_edges) + tuple(extra.instance_wire_edges),
        input_ties={**base.input_ties, **extra.input_ties},
        horizon=extra.horizon if extra.horizon != 20 else base.horizon,
        network_outputs=tuple(dict.fromkeys((*base.network_outputs, *extra.network_outputs))),
    )


def apply_prefix_to_ir(ir: NetworkIR, prefix: str) -> Tuple[NetworkIR, Dict[str, str]]:
    """
    Rename every neuron / input / const in ``ir`` with the given prefix.

    Used for ``instance`` declarations: a sub-DSL is parsed, then its identifiers are
    prefixed so they cannot collide with the parent network.

    OUTPUT: ``(new_ir, mapping)`` where ``mapping`` maps old -> new for renamed names.
    """
    mapping: Dict[str, str] = {}
    for n in ir.neurons:
        mapping[n] = f"{prefix}{n}"
    for i in ir.inputs:
        mapping[i] = f"{prefix}{i}"
    for c in ir.consts:
        mapping[c] = f"{prefix}{c}"

    def rn(x: str) -> str:
        return mapping.get(x, x)

    new_neurons = {rn(n) for n in ir.neurons}
    new_inputs = {rn(i) for i in ir.inputs}
    new_consts = {rn(k): v for k, v in ir.consts.items()}
    new_edges = [Edge(src=rn(e.src), dst=rn(e.dst), weight=e.weight) for e in ir.edges]
    new_neuron_params = {rn(k): v for k, v in ir.neuron_params.items()}
    new_compositions = [
        Composition(kind=c.kind, neurons=tuple(rn(n) for n in c.neurons), inferred=c.inferred)
        for c in ir.compositions
    ]
    new_schedules = {rn(k): v for k, v in ir.schedules.items()}
    renames = {k: v for k, v in mapping.items() if k != v}
    new_specs = [rename_in_spec_text(s, renames) for s in ir.user_specs]
    new_archetypes = [
        ArchetypeInstance(
            kind=a.kind,
            nodes=tuple(rn(n) for n in a.nodes),
            inputs={ik: rn(iv) for ik, iv in a.inputs.items()},
            meta={mk: rn(mv) if mv in mapping else mv for mk, mv in a.meta.items()},
            explicit=a.explicit,
        )
        for a in ir.archetypes
    ]
    new_roles = {rn(k): v for k, v in ir.neuron_roles.items()}
    new_ports: Dict[str, Tuple[str, str]] = {}
    for logical, (kind_hint, internal) in ir.prototype_ports.items():
        new_ports[logical] = (kind_hint, rn(internal))

    return (
        NetworkIR(
            neurons=new_neurons,
            inputs=new_inputs,
            consts=new_consts,
            edges=new_edges,
            params=dict(ir.params),
            neuron_params=new_neuron_params,
            compositions=new_compositions,
            schedules=new_schedules,
            user_specs=new_specs,
            archetypes=new_archetypes,
            prototype_name=ir.prototype_name,
            strict_two_port=ir.strict_two_port,
            neuron_roles=new_roles,
            prototype_ports=new_ports,
            instance_imports=(),
            instance_wires=(),
            instance_wire_edges=(),
            input_ties=dict(ir.input_ties),
            horizon=ir.horizon,
            network_outputs=tuple(rn(n) for n in ir.network_outputs),
        ),
        mapping,
    )
