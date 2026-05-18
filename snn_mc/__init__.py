"""
snn_mc package — Spiking Neural Network Model Checker pipeline.

Pipeline stages (one module per stage):
    .dsl  ->  dsl.parser  ->  ir.NetworkIR  ->  composer  ->  smv.{model, properties, combined}
                                                              -> verify.runner (NuSMV subprocess)
                                                              -> verify.result (log parser)
                                                              -> sim.stub  (post-verify artefact)

The orchestrator that wires everything together lives in cli.py.
"""

__version__ = "0.1.0"
