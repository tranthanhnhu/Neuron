"""
DSL parser: line-based text -> :class:`snn_mc.ir.NetworkIR`.

Supported lines (one per line, ``#`` starts a comment):

    include <path>                                   # inline another DSL file
    neuron_params <name> tau=<int> w_exc=<int> w_inh=<int> S=<int> R=<int> Pmax=<int>
    input <Name>                                     # boolean stimulus
    const <Name> = TRUE|FALSE                        # constant signal
    neuron <Name> [params=<paramSet>]                # explicit neuron declaration
    edge <Src> -> <Dst> weight <int>                 # signed weight edge
    exc  <Src> -> <Dst> [weight <int>]               # positive edge (default weight=1)
    inh  <Src> -> <Dst> [weight <int>]               # negative edge (magnitude>=0)
    schedule <input> values TRUE|FALSE ...           # forced trace prefix
    spec <CTLSPEC|LTLSPEC|INVARSPEC> <formula...>    # raw temporal-logic spec
    compose <sequential|parallel> n1 n2 [n3 ...]     # explicit composition
    horizon <int>                                      # simulation steps (NuSMV clock 0..horizon)
    network_output <neuron>                            # OPTIONAL manual override; blocks set outputs automatically
    block <kind> key=value ...                       # input weights threshold N prefix ... (output is automatic)
    chain from <input> prefix <p> count <n> [weight <int>] [params <set>]

The parser also supports an optional CLI-time override for ``N`` inside ``block`` lines:
    parse_text(..., override_n=10)
This lets the user change every block's ``N=`` from the command line without editing the DSL.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from snn_mc.archetypes import BLOCK_REGISTRY
from snn_mc.archetypes.base import BlockApplyContext
from snn_mc.archetypes.block_helpers import (
    apply_threshold_to_neurons,
    normalize_block_kv,
    suggest_block_kind,
)
from snn_mc.ir import (
    ArchetypeInstance,
    Composition,
    Edge,
    NetworkIR,
    ParamSpec,
    parse_kv_pairs,
    parse_roles_csv,
)

_MAX_INCLUDE_DEPTH = 32


def expand_includes(
    text: str,
    source_path: Optional[Path] = None,
    expanding: Optional[Set[Path]] = None,
    depth: int = 0,
) -> str:
    """
    Inline ``include <path>`` lines recursively.

    INPUT: DSL ``text``; ``source_path`` (used to resolve relative includes).
    OUTPUT: flattened text without any remaining ``include`` lines.
    RAISES: ValueError on missing files, depth overflow, or include cycles.
    """
    if depth > _MAX_INCLUDE_DEPTH:
        raise ValueError(f"include: exceeded max nesting depth ({_MAX_INCLUDE_DEPTH})")
    if expanding is None:
        expanding = set()
    base_dir = source_path.parent if source_path is not None else Path.cwd()
    sp_resolved: Optional[Path] = None
    if source_path is not None:
        sp_resolved = source_path.resolve()
        if sp_resolved in expanding:
            raise ValueError(f"include: cycle detected at {sp_resolved}")
        expanding.add(sp_resolved)
    out_lines: List[str] = []
    try:
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                out_lines.append(raw)
                continue
            toks = line.split()
            if toks[0] == "include":
                if len(toks) != 2:
                    raise ValueError(f"include syntax: include <path> (got: {line})")
                inc_path = (base_dir / toks[1]).resolve()
                if not inc_path.is_file():
                    raise ValueError(f"include: file not found: {inc_path}")
                sub = inc_path.read_text(encoding="utf-8")
                nested = expand_includes(sub, inc_path, expanding, depth + 1)
                out_lines.extend(nested.splitlines())
            else:
                out_lines.append(raw)
    finally:
        if sp_resolved is not None:
            expanding.discard(sp_resolved)
    return "\n".join(out_lines)


def parse_file(path: Path, *, override_n: Optional[int] = None) -> NetworkIR:
    """
    INPUT: filesystem ``path`` to a DSL file.
    OUTPUT: parsed :class:`NetworkIR`. ``override_n`` (if given) replaces every block-level ``N=``.
    """
    text = path.read_text(encoding="utf-8")
    return parse_text(text, source_path=path.resolve(), override_n=override_n)


def parse_text(
    text: str,
    *,
    source_path: Optional[Path] = None,
    override_n: Optional[int] = None,
) -> NetworkIR:
    """
    INPUT: DSL ``text``; optional ``source_path`` (for ``include`` resolution and errors).
    OUTPUT: :class:`NetworkIR`. ``override_n`` is passed down to ``block`` lines as the ``N=`` value.
    """
    resolved = source_path.resolve() if source_path is not None else None
    text = expand_includes(text, resolved, None, 0)
    return _parse_body(text, override_n=override_n)


def _parse_body(text: str, *, override_n: Optional[int]) -> NetworkIR:
    neurons: Set[str] = set()
    inputs: Set[str] = set()
    consts: Dict[str, bool] = {}
    edges: List[Edge] = []
    params: Dict[str, ParamSpec] = {}
    neuron_params: Dict[str, str] = {}
    compositions: List[Composition] = []
    schedules: Dict[str, List[bool]] = {}
    specs: List[str] = []
    archetypes: List[ArchetypeInstance] = []
    strict_two_port = False
    neuron_roles: Dict[str, str] = {}
    input_ties: Dict[str, str] = {}
    horizon = 20
    network_outputs: List[str] = []

    # The default LIF parameter set matches the values fixed with the supervisor.
    params["default"] = ParamSpec(
        name="default",
        tau=4,
        w_exc=3,
        w_inh=-3,
        S=4,
        R_init=2,
        Pmax=10,
    )
    # Built-in neuron "types" (supervisor's Quick / Intermediate / Slow taxonomy).
    # A type is the pair (threshold tau, leak factor R/S); leak is FIXED per type
    # (see lif_module: next(r_num) := r_num). 'slow' needs a larger w_exc so that a
    # high-threshold/low-leak neuron can still reach tau (P_ss = w_exc/(1-R/S) >= tau).
    for _spec in (
        ParamSpec(name="quick", tau=2, w_exc=3, w_inh=-3, S=4, R_init=3, Pmax=10),
        ParamSpec(name="intermediate", tau=4, w_exc=3, w_inh=-3, S=4, R_init=2, Pmax=10),
        ParamSpec(name="slow", tau=6, w_exc=5, w_inh=-5, S=4, R_init=1, Pmax=10),
    ):
        params[_spec.name] = _spec

    def parse_csv_list(val: str, line_no: int) -> List[str]:
        items = [x.strip() for x in val.split(",") if x.strip()]
        if not items:
            raise ValueError(f"line {line_no}: expected non-empty comma-separated list (got {val})")
        return items

    def ensure_neuron(name: str, pset: str = "default") -> None:
        neurons.add(name)
        neuron_params.setdefault(name, pset)

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        toks = line.split()
        head = toks[0]

        if head == "tie":
            if len(toks) != 3:
                raise ValueError(f"line {line_no}: tie syntax: tie <slaveInput> <masterInput>")
            input_ties[toks[1]] = toks[2]
            continue

        if head == "strict_ports":
            strict_two_port = True
            continue

        if head == "roles" and len(toks) >= 2:
            rest = line.split(None, 1)[1].strip()
            for k, v in parse_roles_csv(rest).items():
                neuron_roles[k] = v
            continue

        if head == "neuron_params":
            if len(toks) < 2:
                raise ValueError(f"line {line_no}: neuron_params requires a name")
            name = toks[1]
            kv = parse_kv_pairs(toks[2:])

            def get_int(key: str, default: Optional[int] = None) -> int:
                if key not in kv:
                    if default is None:
                        raise ValueError(f"line {line_no}: missing {key} for neuron_params {name}")
                    return default
                return int(kv[key])

            spec = ParamSpec(
                name=name,
                tau=get_int("tau", params["default"].tau),
                w_exc=get_int("w_exc", params["default"].w_exc),
                w_inh=get_int("w_inh", params["default"].w_inh),
                S=get_int("S", params["default"].S),
                R_init=get_int("R", params["default"].R_init),
                Pmax=get_int("Pmax", params["default"].Pmax),
            )
            params[name] = spec
            continue

        if head == "neuron":
            if len(toks) not in (2, 3):
                raise ValueError(f"line {line_no}: neuron syntax: neuron <Name> [params=<paramName>]")
            n = toks[1]
            neurons.add(n)
            pset = "default"
            if len(toks) == 3:
                kv = parse_kv_pairs([toks[2]])
                if "params" not in kv:
                    raise ValueError(f"line {line_no}: neuron optional arg must be params=<name>")
                pset = kv["params"]
            neuron_params[n] = pset
            continue

        if head == "horizon" and len(toks) == 2:
            horizon = int(toks[1])
            if horizon < 1:
                raise ValueError(f"line {line_no}: horizon must be >= 1")
            continue

        if head == "network_output" and len(toks) >= 2:
            network_outputs.extend(toks[1:])
            continue

        if head == "input" and len(toks) == 2:
            inputs.add(toks[1])
            continue

        if head == "const" and len(toks) == 4 and toks[2] == "=":
            name = toks[1]
            val = toks[3]
            if val not in ("TRUE", "FALSE"):
                raise ValueError(f"line {line_no}: const must be TRUE/FALSE: {line}")
            consts[name] = val == "TRUE"
            continue

        if head == "edge":
            if len(toks) != 6 or toks[2] != "->" or toks[4] != "weight":
                raise ValueError(f"line {line_no}: bad edge syntax: {line}")
            src, dst, w = toks[1], toks[3], int(toks[5])
            edges.append(Edge(src=src, dst=dst, weight=w))
            continue

        if head in ("exc", "inh"):
            if len(toks) not in (4, 6) or toks[2] != "->":
                raise ValueError(f"line {line_no}: bad {head} syntax: {line}")
            src, dst = toks[1], toks[3]
            if len(toks) == 6:
                if toks[4] != "weight":
                    raise ValueError(f"line {line_no}: bad {head} syntax (expected 'weight'): {line}")
                mag = int(toks[5])
            else:
                mag = 1
            if mag < 0:
                raise ValueError(f"line {line_no}: weight magnitude must be >= 0: {line}")
            w = mag if head == "exc" else -mag
            edges.append(Edge(src=src, dst=dst, weight=w))
            continue

        if head == "schedule":
            if len(toks) < 4 or toks[2] != "values":
                raise ValueError(f"line {line_no}: schedule syntax: schedule <input> values <TRUE/FALSE>...")
            inp = toks[1]
            if inp not in inputs:
                raise ValueError(f"line {line_no}: schedule input must be declared with 'input': {inp}")
            vals: List[bool] = []
            for v in toks[3:]:
                if v not in ("TRUE", "FALSE"):
                    raise ValueError(f"line {line_no}: schedule values must be TRUE/FALSE: {line}")
                vals.append(v == "TRUE")
            schedules[inp] = vals
            continue

        if head == "spec":
            if len(toks) < 3:
                raise ValueError(f"line {line_no}: spec syntax: spec <CTLSPEC|LTLSPEC|INVARSPEC> <formula...>")
            kind = toks[1]
            if kind not in ("CTLSPEC", "LTLSPEC", "INVARSPEC"):
                raise ValueError(f"line {line_no}: spec kind must be CTLSPEC|LTLSPEC|INVARSPEC: {line}")
            formula = " ".join(toks[2:])
            specs.append(f"{kind} {formula}")
            continue

        if head == "compose":
            if len(toks) < 4:
                raise ValueError(f"line {line_no}: compose syntax: compose <sequential|parallel> N1 N2 [N3...]")
            kind = toks[1]
            if kind not in ("sequential", "parallel"):
                raise ValueError(f"line {line_no}: compose kind must be sequential|parallel")
            comps = tuple(toks[2:])
            if kind == "sequential" and len(comps) < 2:
                raise ValueError(f"line {line_no}: compose sequential requires at least 2 neurons")
            compositions.append(Composition(kind=kind, neurons=comps, inferred=False))
            continue

        if head == "chain":
            # chain from <input> prefix <p> count <n> [weight <int>] [params <set>]
            if len(toks) < 7 or toks[1] != "from" or toks[3] != "prefix" or toks[5] != "count":
                raise ValueError(
                    f"line {line_no}: chain syntax: chain from <input> prefix <p> count <n> [weight <Int>] [params <paramSet>]"
                )
            inp = toks[2]
            if inp not in inputs:
                raise ValueError(f"line {line_no}: chain input must be declared with 'input': {inp}")
            prefix = toks[4]
            count = override_n if override_n is not None else int(toks[6])
            if count <= 0:
                raise ValueError(f"line {line_no}: chain count must be > 0: {line}")
            weight = 1
            pset = "default"
            rest = toks[7:]
            if rest:
                if len(rest) % 2 != 0:
                    raise ValueError(f"line {line_no}: chain optional args must be key value pairs: {line}")
                it = iter(rest)
                for k, v in zip(it, it):
                    if k == "weight":
                        weight = int(v)
                    elif k == "params":
                        pset = v
                    else:
                        raise ValueError(f"line {line_no}: unknown chain option '{k}': {line}")
            ns: List[str] = []
            for i in range(1, count + 1):
                name = f"{prefix}{i}"
                neurons.add(name)
                neuron_params[name] = pset
                ns.append(name)
            edges.append(Edge(src=inp, dst=ns[0], weight=weight))
            for a, b in zip(ns, ns[1:]):
                edges.append(Edge(src=a, dst=b, weight=weight))
            if len(ns) >= 2:
                compositions.append(Composition(kind="sequential", neurons=tuple(ns), inferred=False))
            continue

        if head == "block":
            if len(toks) < 2:
                raise ValueError(f"line {line_no}: block requires a kind")
            kind = toks[1]
            kv = normalize_block_kv(parse_kv_pairs(toks[2:]) if len(toks) > 2 else {})
            if override_n is not None and "N" in kv:
                # CLI ``--override N=10`` rewrites the in-DSL N for every block that uses it.
                kv["N"] = str(override_n)
            if kind not in BLOCK_REGISTRY:
                hint = suggest_block_kind(kind, list(BLOCK_REGISTRY.keys()))
                raise ValueError(f"line {line_no}: unknown block kind '{kind}'. {hint}")
            block_cls = BLOCK_REGISTRY[kind]

            def get(name: str, default: Optional[str] = None) -> str:
                if name in kv:
                    return kv[name]
                if default is None:
                    raise ValueError(f"line {line_no}: block {kind} missing '{name}'")
                return default

            def get_int(name: str, default: int) -> int:
                return int(kv[name]) if name in kv else default

            pset = get("params", "default")
            # Default edge weights follow the SELECTED param set, not always 'default',
            # so that e.g. params=slow (w_exc=5) yields edges strong enough to reach tau.
            base_pset = params.get(pset, params["default"])
            w_exc = get_int("weight", base_pset.w_exc)
            w_inh = -abs(get_int("inh_weight", abs(base_pset.w_inh)))

            def apply_threshold(neuron_names: List[str], param_set: str, threshold: Optional[int]) -> None:
                for n in neuron_names:
                    neurons.add(n)
                apply_threshold_to_neurons(params, neuron_params, neuron_names, param_set, threshold)

            ctx = BlockApplyContext(
                line_no=line_no,
                edges=edges,
                compositions=compositions,
                archetypes=archetypes,
                w_exc=w_exc,
                w_inh=w_inh,
                ensure_neuron=ensure_neuron,
                get=get,
                get_int=get_int,
                parse_csv_list=lambda val, ln=line_no: parse_csv_list(val, ln),
                params=params,
                neuron_params=neuron_params,
                apply_threshold=apply_threshold,
            )
            block_cls.apply_block(kv, ctx)
            if archetypes and archetypes[-1].explicit:
                # Outputs are decided by the archetype itself (meta["outputs"]); the user
                # does not declare output= / network_output for blocks.
                network_outputs.extend(archetypes[-1].meta.get("outputs", []))
            if "roles" in kv and archetypes:
                last = archetypes[-1]
                if last.explicit:
                    meta = dict(last.meta)
                    meta["roles"] = kv["roles"]
                    archetypes[-1] = ArchetypeInstance(
                        kind=last.kind,
                        nodes=last.nodes,
                        inputs=last.inputs,
                        meta=meta,
                        explicit=last.explicit,
                    )
            continue

        raise ValueError(f"line {line_no}: unknown DSL line: {line}")

    # Post-parse sanity checks: every edge endpoint must refer to a declared name.
    names = neurons | inputs | set(consts.keys())
    for e in edges:
        if e.src not in names:
            raise ValueError(f"Unknown edge src: {e.src}")
        if e.dst not in neurons:
            raise ValueError(f"Edge dst must be a neuron: {e.dst}")

    for n, pset in neuron_params.items():
        if pset not in params:
            raise ValueError(f"Unknown param-set '{pset}' for neuron '{n}'")

    _validate_input_ties(input_ties, inputs, schedules)

    if not network_outputs:
        for a in archetypes:
            if a.explicit:
                network_outputs.extend(a.meta.get("outputs", []))

    return NetworkIR(
        neurons=neurons,
        inputs=inputs,
        consts=consts,
        edges=edges,
        params=params,
        neuron_params=neuron_params,
        compositions=compositions,
        schedules=schedules,
        user_specs=specs,
        archetypes=archetypes,
        prototype_name=None,
        strict_two_port=strict_two_port,
        neuron_roles=neuron_roles,
        prototype_ports={},
        instance_imports=(),
        instance_wires=(),
        instance_wire_edges=(),
        input_ties=dict(input_ties),
        horizon=horizon,
        network_outputs=tuple(dict.fromkeys(network_outputs)),
    )


def _validate_input_ties(
    ties: Dict[str, str],
    inputs: Set[str],
    schedules: Dict[str, List[bool]],
) -> None:
    for slave, master in ties.items():
        if slave not in inputs or master not in inputs:
            raise ValueError(f"tie: '{slave}' and '{master}' must be declared inputs")
        if slave == master:
            raise ValueError(f"tie: cannot tie input to itself ({slave})")
        if slave in schedules:
            raise ValueError(f"tie: cannot schedule tied slave input '{slave}'")
    for s in ties:
        seen: Set[str] = set()
        cur = s
        while cur in ties:
            if cur in seen:
                raise ValueError("tie: cycle detected")
            seen.add(cur)
            cur = ties[cur]
