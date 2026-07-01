# snn_mc — A verification pipeline for neuronal archetypes

Artifact repository for **snn_mc**, a tool that compiles **NASL** (Neuronal Archetype Specification Language) descriptions of spiking neural archetypes into discrete-time **NuSMV** models and checks CTL/LTL properties automatically.

**Paper:** *A verification pipeline for neuronal archetypes* — ICTCS 2026 (27th Italian Conference on Theoretical Computer Science, September 07–09, 2026, Udine, Italy). LaTeX source: [`docs/old.tex`](docs/old.tex).

## Overview

```
.dsl (NASL)  →  Parser  →  NetworkIR  →  Composer  →  SMV emitter
                                                          |
                                    model.smv + properties.smv + combined.smv
                                                          |
                                                   NuSMV model checker
                                                          |
                                              results + counterexample traces
```

The pipeline supports seven neuronal archetype kinds (negative loop, positive loop, simple series, parallel composition, and others), three LIF neuron presets (`slow`, `intermediate`, `quick`), automatic archetype detection, and archetype-driven property generation.

## Requirements

| Component | Version / notes |
| --- | --- |
| Python | ≥ 3.10 |
| NuSMV | 2.7.x on `PATH` ([download](https://nusmv.fbk.eu/downloads.html)); optional local install via [`tools/README.md`](tools/README.md) |
| pytest | ≥ 7 (optional, for tests only) |

No third-party Python packages are required at runtime (`requirements.txt` documents this).

## Quickstart

Reproduce the **negative feedback loop** case study from Section 4 of the paper:

```bash
python -m snn_mc run examples/negloop_only.dsl --out runs/case_study_negloop_sigma
```

Expected outputs under `runs/case_study_negloop_sigma/`:

| File | Description |
| --- | --- |
| `combined.smv` | NuSMV model + properties (input to the checker) |
| `model.smv`, `properties.smv` | Separated model and specification files |
| `nusmv.log` | Full NuSMV stdout/stderr |
| `step1_diagram.md` … `step6_results.txt` | Numbered report artefacts |
| `sim_stub.txt` | Post-verification wiring summary (if specs pass and `--skip-sim` is not set) |

**Exit codes:** `0` success · `1` at least one property false · `2` DSL not found · `3` NuSMV unavailable · `4` unparsable NuSMV log

### Other examples

```bash
# Simple series chained into a negative loop (4 + 2 neurons)
python -m snn_mc run examples/series_negloop.dsl --out runs/demo

# Emit SMV only (no NuSMV required)
python -m snn_mc run examples/series_negloop.dsl --out runs/demo --skip-verify
```

See [`examples/`](examples/) for additional DSL files. Shared LIF parameters are defined in [`examples/neuron_base.dsl`](examples/neuron_base.dsl).

### CLI options

```bash
python -m snn_mc run <file.dsl> --out <dir> \
  [--nusmv PATH] [--skip-verify] [--skip-sim] \
  [--emit-mode lif|simple_boolean] \
  [--override N=4]
```

## Project layout

| Path | Role |
| --- | --- |
| [`snn_mc/cli.py`](snn_mc/cli.py) | CLI entry point (`python -m snn_mc run …`) |
| [`snn_mc/dsl/`](snn_mc/dsl/) | NASL parser |
| [`snn_mc/archetypes/`](snn_mc/archetypes/) | Archetype blocks, detection, property templates |
| [`snn_mc/smv/`](snn_mc/smv/) | NuSMV model and property emission |
| [`snn_mc/verify/`](snn_mc/verify/) | NuSMV subprocess and log parsing |
| [`snn_mc/report/`](snn_mc/report/) | Step-by-step report files |
| [`examples/`](examples/) | Reference NASL specifications |
| [`reference/`](reference/) | Hand-written golden SMV references |
| [`docs/`](docs/) | Paper (`old.tex`), pipeline diagram, supplementary notes |
| [`tests/`](tests/) | Smoke and parser tests |

## Tests

```bash
pip install pytest
pytest tests/ -q
```

The smoke test runs with `--skip-verify` and does not require NuSMV.

## Citation

If you use this artifact, please cite the ICTCS 2026 paper (*A verification pipeline for neuronal archetypes*).

## Authors

Thi-Thuy-Duong Pham, Elisabetta De Maria, Robert De Simone — I3S / Université Côte d'Azur; Inria Université Côte d'Azur.

## License

Source code and examples are provided for research and reproducibility purposes in connection with the ICTCS 2026 submission.
