# Demo network: Simple Series feeds into a Negative Loop oscillator.
#
#     stim --> c1 --> c2 --> c3 --> c4 --> a --> b
#                                            ^    |
#                                            +----+
include neuron_base.dsl

horizon 20

input stim
schedule stim values TRUE TRUE FALSE TRUE TRUE FALSE

block simple_series  input=stim N=4 prefix=c params=intermediate
block negative_loop  input=c4   A=a B=b     params=quick
