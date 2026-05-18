"""
NuSMV emission layer.

PUBLIC API:
    prepare_ir(ir)                -> SmvPrepared       (renamed graph + helper tables).
    emit_model_smv(ir, prepared)  -> str               (MODULE main + neuron submodule tail).
    build_properties_smv(...)     -> str               (standalone properties.smv body).
    build_combined_smv(...)       -> str               (model + properties + tail in one file).
"""

from snn_mc.smv.prepare import SmvPrepared, prepare_ir
from snn_mc.smv.model import emit_model_smv, emit_model_core
from snn_mc.smv.properties import build_properties_smv, emit_properties_block
from snn_mc.smv.combined import build_combined_smv

__all__ = [
    "SmvPrepared",
    "prepare_ir",
    "emit_model_smv",
    "emit_model_core",
    "emit_properties_block",
    "build_properties_smv",
    "build_combined_smv",
]
