"""
Helpers for ``block <kind> key=value`` lines: normalised keys, int lists, typo hints.
"""

from __future__ import annotations

import difflib
from typing import Dict, List, Optional

from snn_mc.ir import ParamSpec, clone_param_with_tau

_BLOCK_KEY_ALIASES: Dict[str, str] = {
    "input": "input",
    "weights": "weights",
    "weight": "weight",
    "exc_weights": "exc_weights",
    "inh_weight": "inh_weight",
    "threshold": "threshold",
    "tau": "threshold",
    "n": "N",
    "prefix": "prefix",
    "params": "params",
    "neurons": "neurons",
    "roles": "roles",
    "a": "A",
    "b": "B",
    "i": "I",
    "t": "T",
    "src": "src",
    "outputs": "outputs",
}


def normalize_block_kv(kv: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in kv.items():
        canon = _BLOCK_KEY_ALIASES.get(k.lower(), k)
        out[canon] = v
    return out


def parse_int_list(val: str, *, line_no: int, what: str) -> List[int]:
    s = val.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    if not s:
        raise ValueError(f"line {line_no}: {what}: expected non-empty integer list")
    parts = [p.strip() for p in s.split(",") if p.strip()]
    try:
        return [int(p) for p in parts]
    except ValueError as exc:
        raise ValueError(f"line {line_no}: {what}: invalid integer in list {val!r}") from exc


def suggest_block_kind(kind: str, valid_kinds: List[str]) -> str:
    close = difflib.get_close_matches(kind, valid_kinds, n=3, cutoff=0.5)
    if not close:
        return f"Valid block kinds: {', '.join(sorted(valid_kinds))}"
    best = close[0]
    msg = f"Did you mean '{best}'?"
    if len(close) > 1:
        msg += f" (also similar: {', '.join(close[1:])})"
    return msg


def exc_weights_for_chain(
    kv: Dict[str, str],
    ctx_line_no: int,
    num_edges: int,
    default_w: int,
    *,
    what: str,
) -> List[int]:
    key = "weights" if "weights" in kv else ("exc_weights" if "exc_weights" in kv else None)
    if key is None:
        return [default_w] * num_edges
    ws = parse_int_list(kv[key], line_no=ctx_line_no, what=f"{what} {key}")
    if len(ws) != num_edges:
        raise ValueError(
            f"line {ctx_line_no}: {what}: {key} needs {num_edges} values, got {len(ws)}"
        )
    for w in ws:
        if w < 0:
            raise ValueError(f"line {ctx_line_no}: {what}: excitatory weights must be >= 0")
    return ws


def inh_weight_from_kv(kv: Dict[str, str], default_w_inh: int) -> int:
    if "inh_weight" not in kv:
        return default_w_inh
    mag = int(kv["inh_weight"])
    if mag < 0:
        mag = abs(mag)
    return -mag


def apply_threshold_to_neurons(
    params: Dict[str, ParamSpec],
    neuron_params: Dict[str, str],
    neuron_names: List[str],
    pset: str,
    threshold: Optional[int],
) -> None:
    if threshold is None:
        for n in neuron_names:
            neuron_params[n] = pset
        return
    key = clone_param_with_tau(params, pset, threshold)
    for n in neuron_names:
        neuron_params[n] = key
