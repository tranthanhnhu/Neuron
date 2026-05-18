# Parameterising the number of neurons (N)

The supervisor asked that the user be able to change the chain length without rewriting
the DSL. `snn_mc` supports this in two complementary ways.

## 1. DSL-level: `N=<int> prefix=<str>`

Every chain-like archetype (`simple_series`, `series_multiple_outputs`, `negative_loop`,
`positive_loop`, `contralateral_inhibition`) accepts either an explicit `neurons=` list
or a generative `N=/prefix=` pair. Pick whichever fits the example:

```text
# Explicit (legacy style, exact names):
block simple_series input=stim neurons=c1,c2,c3,c4 params=default

# Parameterised (new):
block simple_series input=stim N=4 prefix=c params=default
```

The second form produces neurons `c1, c2, c3, c4` (and chain edges between them).

`parallel_composition` uses `outputs=` instead of `neurons=`; it also supports
`N=/prefix=`:

```text
block parallel_composition input=stim src=src N=3 prefix=out params=default
# produces src + out1 + out2 + out3 plus the four exc edges
```

`inhibition_of_behavior` always names two neurons explicitly (`I=` and `T=`).

## 2. CLI override

For ad-hoc experiments the user can change N globally without touching the file:

```bash
python -m snn_mc run examples/series_negloop.dsl --out runs/N10 --override N=10
```

When `--override N=K` is given:

- Every `N=` field on a `block` line is rewritten to `K` before parsing.
- The legacy `chain ... count <n>` line is rewritten to `count K` as well.

## Bounds

`N` must be between `ARCHETYPE_LIST_MIN = 2` and `ARCHETYPE_LIST_MAX = 10`.
These match the thesis assumption that one block declares between two and ten neurons.
Edit `snn_mc/archetypes/base.py` if you need to relax them.
