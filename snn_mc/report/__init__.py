"""
Demo / report layer: write six numbered files describing the pipeline state.

Steps:
    1. step1_diagram.md       — Mermaid + ASCII picture of the network.
    2. step2_input.dsl        — copy of the user DSL.
    3. step3_ir.json          — pretty JSON dump of NetworkIR.
    4. step4_composition.txt  — explicit / detected archetypes and their wiring.
    5. step5_properties.smv   — only the temporal-logic specs.
    6. step6_results.txt      — NuSMV summary (true/false counts + counterexample if any).

See :func:`snn_mc.report.steps.write_all_steps` for the orchestrator.
"""

from snn_mc.report.steps import write_all_steps

__all__ = ["write_all_steps"]
