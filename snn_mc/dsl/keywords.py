"""
Reserved DSL keywords (first token of each line). Lookups in :mod:`snn_mc.dsl.parser`.
"""

from __future__ import annotations

from typing import FrozenSet

KW_INCLUDE: str = "include"
KW_INPUT: str = "input"
KW_CONST: str = "const"
KW_NEURON: str = "neuron"
KW_NEURON_PARAMS: str = "neuron_params"
KW_EDGE: str = "edge"
KW_EXC: str = "exc"
KW_INH: str = "inh"
KW_SCHEDULE: str = "schedule"
KW_SPEC: str = "spec"
KW_BLOCK: str = "block"
KW_COMPOSE: str = "compose"
KW_CHAIN: str = "chain"
KW_TIE: str = "tie"
KW_ROLES: str = "roles"
KW_STRICT_PORTS: str = "strict_ports"

ALL_KEYWORDS: FrozenSet[str] = frozenset({
    KW_INCLUDE, KW_INPUT, KW_CONST, KW_NEURON, KW_NEURON_PARAMS,
    KW_EDGE, KW_EXC, KW_INH, KW_SCHEDULE, KW_SPEC,
    KW_BLOCK, KW_COMPOSE, KW_CHAIN, KW_TIE, KW_ROLES, KW_STRICT_PORTS,
})
