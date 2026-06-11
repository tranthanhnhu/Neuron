# Same topology as series_negloop.dsl with heterogeneous edge weights and neuron types.
include neuron_base.dsl

horizon 24

input stim
schedule stim values TRUE TRUE FALSE TRUE TRUE FALSE

block simple_series input=stim N=4 prefix=c weights=3,2,5,4 params=intermediate
block negative_loop input=c4 A=a B=b exc_weights=4,2 inh_weight=3 params=quick
