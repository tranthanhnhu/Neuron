"""
Step 5 helper: extract ONLY the temporal specifications for display.

Reuses :func:`snn_mc.smv.properties.build_properties_smv` so step5 contains exactly the
same text NuSMV would receive (without the MODULE main shell or neuron submodules).
"""

from __future__ import annotations

from snn_mc.ir import NetworkIR
from snn_mc.smv.prepare import SmvPrepared
from snn_mc.smv.properties import build_properties_smv


def render_step5(ir: NetworkIR, prepared: SmvPrepared, *, emit_mode: str = "lif") -> str:
    """INPUT: NetworkIR + SmvPrepared + emit_mode.  OUTPUT: text for ``step5_properties.smv``."""
    return build_properties_smv(prepared, ir, emit_mode=emit_mode)
