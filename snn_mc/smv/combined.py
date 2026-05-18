"""
Single-file NuSMV output (``combined.smv``): MODULE main + specs + neuron MODULE tail.

NuSMV accepts this file directly; ``model.smv`` and ``properties.smv`` are emitted as
companion artefacts for readability.
"""

from __future__ import annotations

from snn_mc.ir import NetworkIR
from snn_mc.smv.lif_module import emit_bool_thr_module
from snn_mc.smv.model import emit_lif_modules, emit_model_core
from snn_mc.smv.prepare import SmvPrepared
from snn_mc.smv.properties import emit_properties_block


def build_combined_smv(
    ir: NetworkIR,
    prepared: SmvPrepared,
    *,
    emit_mode: str = "lif",
) -> str:
    """
    INPUT: NetworkIR + SmvPrepared + emit_mode.
    OUTPUT: NuSMV source as a single string in the order  core -> specs -> neuron MODULE tail.
    """
    core = emit_model_core(ir, prepared, emit_mode=emit_mode)
    props = emit_properties_block(prepared, ir, emit_mode=emit_mode)
    tail = emit_lif_modules(prepared) if emit_mode == "lif" else emit_bool_thr_module()
    return core + props + tail
