# Shared LIF parameter base for every example DSL in this folder.
# All 'default' values were fixed with the supervisor (see project doc.txt).
neuron_params default tau=4 w_exc=3 w_inh=-3 S=4 R=2 Pmax=10

# Three built-in neuron "types" are ALWAYS available (no need to redeclare them):
# a type = (threshold tau, leak factor R/S). Leak is FIXED per type (r_num stays = R).
#
#   type          tau   leak (R/S)   w_exc   meaning
#   ----          ---   ----------   -----   -------------------------------
#   quick          2      3/4=0.75     3      low threshold + high leak  -> fires fast
#   intermediate   4      2/4=0.50     3      balanced (same as 'default')
#   slow           6      1/4=0.25     5      high threshold + low leak  -> fires late
#
# Use them on any block with  params=quick | params=intermediate | params=slow.
