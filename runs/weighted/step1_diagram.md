# Step 1 — Network diagram

Source DSL: `examples\series_negloop_weighted.dsl`

## Mermaid

```mermaid
flowchart LR
  stim["stim (input)"]
  a((a))
  b["b (output)"]
  c1((c1))
  c2((c2))
  c3((c3))
  c4["c4 (output)"]
  stim -->|"exc w=3"| c1
  c1 -->|"exc w=2"| c2
  c2 -->|"exc w=5"| c3
  c3 -->|"exc w=4"| c4
  c4 -->|"exc w=4"| a
  a -->|"exc w=2"| b
  b -.->|"inh w=-3"| a
```

## ASCII

```
Network (ASCII summary)
=======================
Inputs (1): ['stim']
Neurons (6): ['a', 'b', 'c1', 'c2', 'c3', 'c4']

Edges per destination neuron:
  a <- exc: [('c4', 4)]    inh: [('b', -3)]
  b <- exc: [('a', 2)]    inh: []
  c1 <- exc: [('stim', 3)]    inh: []
  c2 <- exc: [('c1', 2)]    inh: []
  c3 <- exc: [('c2', 5)]    inh: []
  c4 <- exc: [('c3', 4)]    inh: []
```
