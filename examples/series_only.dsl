# Reference example: a single Simple Series chain of N neurons.
# Run with:  python -m snn_mc run examples/series_only.dsl --out runs/series
include neuron_base.dsl

input stim
schedule stim values TRUE TRUE FALSE TRUE

block simple_series input=stim N=5 prefix=n params=quick
