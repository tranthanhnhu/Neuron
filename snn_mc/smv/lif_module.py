"""
NuSMV ``MODULE lif_<paramSet>`` emitter for the discretised Leaky Integrate-and-Fire neuron.

Public API:
    validate_params(spec)       — heuristic parameter sanity checks.
    generate_lif_module(spec)   — list[str] of NuSMV lines defining MODULE lif_<spec.name>.

The emitted module follows the same scheme as the legacy ``lif_neuron_6.smv`` reference:
    VAR    P : 0..Pmax;     r_num : 0..S;
    DEFINE input_sum, leak_term, raw_next, spike
    ASSIGN init(P)=0; init(r_num)=R_init;
           next(P) := case spike : 0; clamp; raw_next; esac;
"""

from __future__ import annotations

from typing import List

from snn_mc.ir import ParamSpec


def validate_params(spec: ParamSpec) -> None:
    """
    Sufficient (not complete) checks to reject obviously broken parameter sets.

    INPUT: a ParamSpec.
    RAISES: ValueError when the LIF cannot possibly spike or the leak is unstable.
            Prints a warning when ``w_exc + w_inh >= tau`` (inhibition cannot fully suppress).
    """
    if spec.tau <= 0:
        raise ValueError(f"[{spec.name}] tau must be > 0")
    if spec.S <= 0:
        raise ValueError(f"[{spec.name}] S must be > 0")
    if not (0 <= spec.R_init <= spec.S):
        raise ValueError(
            f"[{spec.name}] R must satisfy 0 <= R <= S (got R={spec.R_init}, S={spec.S})"
        )
    if spec.R_init >= spec.S:
        raise ValueError(
            f"[{spec.name}] leak does not converge: R/S = {spec.R_init}/{spec.S} >= 1"
        )
    if spec.Pmax <= 0:
        raise ValueError(f"[{spec.name}] Pmax must be > 0")

    r_frac = spec.R_init / spec.S
    p_ss = spec.w_exc / (1.0 - r_frac) if (1.0 - r_frac) > 0 else float("inf")
    if p_ss < spec.tau:
        raise ValueError(
            f"[{spec.name}] spike likely unreachable with excitation-only: P_ss~{p_ss:.2f} < tau={spec.tau}. "
            f"Increase w_exc or decrease R/S."
        )

    net_both = spec.w_exc + spec.w_inh
    if net_both >= spec.tau:
        # Not fatal; just informative.
        print(
            f"[WARN {spec.name}] w_exc+w_inh={net_both} >= tau={spec.tau}: "
            f"inhibition cannot fully suppress excitation."
        )


def generate_lif_module(spec: ParamSpec) -> List[str]:
    """
    INPUT: ParamSpec describing one LIF parameter set.
    OUTPUT: list of NuSMV lines defining ``MODULE lif_<spec.name>(x_exc, x_inh, t)``.
    """
    mod_name = f"lif_{spec.name}"
    lines: List[str] = []
    lines.append(
        f"-- LIF module '{mod_name}': tau={spec.tau}, w_exc={spec.w_exc}, w_inh={spec.w_inh}, "
        f"S={spec.S}, R_init={spec.R_init}, Pmax={spec.Pmax}"
    )
    lines.append(f"MODULE {mod_name}(x_exc, x_inh, t)")
    lines.append("VAR")
    lines.append(f"  P     : 0..{spec.Pmax};")
    lines.append(f"  r_num : 0..{spec.S};")
    lines.append("")
    lines.append("DEFINE")
    lines.append(f"  Pmax   := {spec.Pmax};")
    lines.append(f"  tau    := {spec.tau};")
    lines.append(f"  S_leak := {spec.S};")
    lines.append(f"  w_exc  := {spec.w_exc};")
    lines.append(f"  w_inh  := {spec.w_inh};")
    lines.append("  input_sum := (x_exc ? w_exc : 0) + (x_inh ? w_inh : 0);")
    lines.append("  leak_term := (r_num * P) / S_leak;")
    lines.append("  raw_next  := leak_term + input_sum;")
    lines.append("  spike     := (P >= tau);")
    lines.append("")
    lines.append("ASSIGN")
    lines.append("  init(P) := 0;")
    lines.append(f"  init(r_num) := {spec.R_init};")
    lines.append("  next(r_num) :=")
    lines.append("    case")
    lines.append("      t < 4 : r_num;")
    lines.append(f"      TRUE  : 0..{spec.S};")
    lines.append("    esac;")
    lines.append("  next(P) :=")
    lines.append("    case")
    lines.append("      spike           : 0;")
    lines.append("      raw_next < 0    : 0;")
    lines.append("      raw_next > Pmax : Pmax;")
    lines.append("      TRUE            : raw_next;")
    lines.append("    esac;")
    lines.append("")
    return lines


def emit_bool_thr_module() -> str:
    """
    Single reusable submodule used by ``emit_mode == 'simple_boolean'``.

    OUTPUT: NuSMV text for ``MODULE bool_thr(inp_net, thr, t)`` where ``spike := active``.
    """
    lines = [
        "-- Discrete threshold neuron (simple_boolean emit_mode)",
        "MODULE bool_thr(inp_net, thr, t)",
        "VAR",
        "  active : boolean;",
        "DEFINE",
        "  spike := active;",
        "ASSIGN",
        "  init(active) := FALSE;",
        "  next(active) := (inp_net >= thr);",
        "",
    ]
    return "\n".join(lines) + "\n"
