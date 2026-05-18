# Step 1 — Network diagram

Source DSL: `NewStructure\examples\parallel_only.dsl`

## Mermaid

```mermaid
flowchart LR
  stim["stim (input)"]
  out1((out1))
  out2((out2))
  out3((out3))
  src((src))
  stim -->|"exc w=3"| src
  src -->|"exc w=3"| out1
  src -->|"exc w=3"| out2
  src -->|"exc w=3"| out3
```

## ASCII

```
Network (ASCII summary)
=======================
Inputs (1): ['stim']
Neurons (4): ['out1', 'out2', 'out3', 'src']

Edges per destination neuron:
  out1 <- exc: [('src', 3)]    inh: []
  out2 <- exc: [('src', 3)]    inh: []
  out3 <- exc: [('src', 3)]    inh: []
  src <- exc: [('stim', 3)]    inh: []
```
