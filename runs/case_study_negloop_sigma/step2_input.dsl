# Reference example: a single Negative Loop driven directly by an input.
# Run with:  python -m snn_mc run examples/negloop_only.dsl --out runs/negloop
include neuron_base.dsl

input stim
schedule stim values TRUE FALSE TRUE TRUE FALSE

block negative_loop input=stim A=a B=b params=quick
