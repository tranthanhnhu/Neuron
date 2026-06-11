# Reference example: parallel composition (one source neuron drives N outputs).
include neuron_base.dsl

input stim
schedule stim values TRUE TRUE TRUE FALSE

block parallel_composition input=stim src=src N=3 prefix=out params=intermediate
