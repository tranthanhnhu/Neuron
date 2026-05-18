# Step 1 — Network diagram

Source DSL: `NewStructure\examples\series_negloop.dsl`

## Mermaid

```mermaid
flowchart LR
  stim["stim (input)"]
  a((a))
  b((b))
  c1((c1))
  c2((c2))
  c3((c3))
  c4((c4))
  c5((c5))
  c6((c6))
  stim -->|"exc w=3"| c1
  c1 -->|"exc w=3"| c2
  c2 -->|"exc w=3"| c3
  c3 -->|"exc w=3"| c4
  c4 -->|"exc w=3"| c5
  c5 -->|"exc w=3"| c6
  c4 -->|"exc w=3"| a
  a -->|"exc w=3"| b
  b -.->|"inh w=-3"| a
```

## ASCII

```
Network (ASCII summary)
=======================
Inputs (1): ['stim']
Neurons (8): ['a', 'b', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6']

Edges per destination neuron:
  a <- exc: [('c4', 3)]    inh: [('b', -3)]
  b <- exc: [('a', 3)]    inh: []
  c1 <- exc: [('stim', 3)]    inh: []
  c2 <- exc: [('c1', 3)]    inh: []
  c3 <- exc: [('c2', 3)]    inh: []
  c4 <- exc: [('c3', 3)]    inh: []
  c5 <- exc: [('c4', 3)]    inh: []
  c6 <- exc: [('c5', 3)]    inh: []
```
