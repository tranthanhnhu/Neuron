# Demo: the three built-in neuron types side by side.
# Three independent simple_series chains share one stimulus; each chain uses a
# different neuron type so their spiking behaviour (fast vs slow) can be compared.
#
#   stim --> q1 --> q2     (quick:        tau=2, leak 0.75)
#   stim --> i1 --> i2     (intermediate: tau=4, leak 0.50)
#   stim --> s1 --> s2     (slow:         tau=6, leak 0.25)
#
# Outputs are automatic (last neuron of each chain): q2, i2, s2.
# Run with:  python -m snn_mc run examples/neuron_types_demo.dsl --out runs/types
include neuron_base.dsl

horizon 20

input stim
schedule stim values TRUE TRUE TRUE TRUE TRUE

block simple_series input=stim N=2 prefix=q params=quick
block simple_series input=stim N=2 prefix=i params=intermediate
block simple_series input=stim N=2 prefix=s params=slow
