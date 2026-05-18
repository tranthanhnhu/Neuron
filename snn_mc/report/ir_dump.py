"""
Serialise a NetworkIR to readable JSON for ``step3_ir.json``.

Only IR fields that survive the round trip are emitted: enough to reconstruct the
network logically without leaking generator internals (e.g. SmvPrepared).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List

from snn_mc.ir import NetworkIR


def ir_to_dict(ir: NetworkIR) -> Dict[str, Any]:
    """
    INPUT: NetworkIR.
    OUTPUT: dict with lists / dicts only (JSON-serialisable). Sets are sorted; edges become tuples.
    """
    return {
        "neurons": sorted(ir.neurons),
        "inputs": sorted(ir.inputs),
        "consts": {k: bool(v) for k, v in sorted(ir.consts.items())},
        "edges": [{"src": e.src, "dst": e.dst, "weight": e.weight} for e in ir.edges],
        "params": {
            name: {
                "tau": p.tau,
                "w_exc": p.w_exc,
                "w_inh": p.w_inh,
                "S": p.S,
                "R_init": p.R_init,
                "Pmax": p.Pmax,
            }
            for name, p in sorted(ir.params.items())
        },
        "neuron_params": dict(sorted(ir.neuron_params.items())),
        "compositions": [
            {"kind": c.kind, "neurons": list(c.neurons), "inferred": c.inferred}
            for c in ir.compositions
        ],
        "schedules": {k: list(v) for k, v in sorted(ir.schedules.items())},
        "user_specs": list(ir.user_specs),
        "archetypes": [
            {
                "kind": a.kind,
                "nodes": list(a.nodes),
                "inputs": dict(a.inputs),
                "meta": dict(a.meta),
                "explicit": a.explicit,
            }
            for a in ir.archetypes
        ],
        "neuron_roles": dict(sorted(ir.neuron_roles.items())),
        "input_ties": dict(sorted(ir.input_ties.items())),
    }


def render_step3(ir: NetworkIR) -> str:
    """OUTPUT: pretty-printed JSON suitable for writing to ``step3_ir.json``."""
    return json.dumps(ir_to_dict(ir), indent=2, ensure_ascii=False) + "\n"
