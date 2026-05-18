# Reference SMV files

These hand-written NuSMV files served as the original specifications before the DSL
existed.  They live here as a "golden" reference: every file in this folder is meant
to be opened directly with NuSMV and compared against the output the new pipeline
emits for the equivalent DSL.

| File | Equivalent DSL example |
| --- | --- |
| `lif_neuron_6.smv` | (single neuron — no DSL example, baseline only) |
| `golden_archetypes/archetype_simple_series.smv` | `examples/series_only.dsl` |
| `golden_archetypes/archetype_series_multiple_outputs.smv` | (use `block series_multiple_outputs` in any DSL) |
| `golden_archetypes/archetype_parallel_composition.smv` | `examples/parallel_only.dsl` |
| `golden_archetypes/archetype_negative_loop.smv` | `examples/negloop_only.dsl` |
| `golden_archetypes/archetype_contralateral_inhibition.smv` | (use `block contralateral_inhibition`) |
| `golden_archetypes/archetype_inhibition_of_behavior.smv` | (use `block inhibition_of_behavior`) |

> Note: `positive_loop` does not have a hand-written reference — it was added later by us.
