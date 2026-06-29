# Step 1 — Network diagram

Source DSL: `examples\negloop_only.dsl`

## Mermaid

```mermaid
flowchart LR
  stim["stim (input)"]
  a["a (output)"]
  b["b (output)"]
  stim -->|"exc w=3"| a
  a -->|"exc w=3"| b
  b -.->|"inh w=-3"| a
```

## ASCII

```
Network (ASCII summary)
=======================
Inputs (1): ['stim']
Neurons (2): ['a', 'b']

Edges per destination neuron:
  a <- exc: [('stim', 3)]    inh: [('b', -3)]
  b <- exc: [('a', 3)]    inh: []
```
