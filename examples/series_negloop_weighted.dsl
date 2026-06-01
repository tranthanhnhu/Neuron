# Same topology as series_negloop.dsl with heterogeneous edge weights and threshold.
include neuron_base.dsl

horizon 24

input stim
schedule stim values TRUE TRUE FALSE TRUE TRUE FALSE

block simple_series input=stim output=c4 N=4 prefix=c weights=3,2,5,4 threshold=4 params=default
block negative_loop input=c4 output=b A=a B=b exc_weights=4,2 inh_weight=3 threshold=4 params=default

network_output c4
