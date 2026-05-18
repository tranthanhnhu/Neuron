# Demo network: Simple Series feeds into a Negative Loop oscillator.
#
# Topology (N=4 by default; use --override N=K to change the chain length):
#
#     stim --> c1 --> c2 --> c3 --> c4 --> a
#                                            |
#                                            v   exc
#                                            b
#                                            |   inh
#                                            +-----> back to a
#
# c_N is the last neuron of the chain and acts as the excitatory input to the
# negative-loop's first neuron (a).
include neuron_base.dsl

input stim

# A deterministic schedule for the first few steps makes oscillation
# observable in NuSMV traces; remaining steps are non-deterministic.
schedule stim values TRUE TRUE FALSE TRUE TRUE FALSE

# Chain of N neurons named c1..cN.  Change N here, or pass --override N=10 on the CLI.
block simple_series  input=stim N=4 prefix=c params=default

# Two-neuron negative loop driven by the chain output (c4).
block negative_loop  input=c4   A=a B=b      params=default
