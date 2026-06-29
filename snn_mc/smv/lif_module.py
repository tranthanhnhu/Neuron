"""
NuSMV ``MODULE lif_<paramSet>`` emitter for the discretised Leaky Integrate-and-Fire neuron.

Public API:
    compute_sigma(...)        — De Maria integration-window length from R/S and epsilon.
    validate_params(spec)     — heuristic parameter sanity checks.
    generate_lif_module(spec) — list[str] of NuSMV lines defining MODULE lif_<spec.name>.

The emitted module implements the bounded σ-window LI&F update of De Maria et al.:
    p(t) = sum_{e=0}^{sigma} (R/S)^e * input_sum(t-e)
with a shift register on ``input_sum`` and fixed leak ratio ``R_init / S``.
"""

from __future__ import annotations

import math
from typing import List

from snn_mc.ir import ParamSpec


def compute_sigma(
    R_init: int,
    S: int,
    *,
    epsilon: float = 0.01,
    cap: int = 8,
) -> int:
    """
    Integration window σ from De Maria et al.: floor(ln(ε) / ln(R/S)).

    INPUT: leak numerator/denominator (0 < R < S), approximation ε, optional cap for MC tractability.
    OUTPUT: integer σ >= 1.
    """
    if S <= 0 or R_init <= 0 or R_init >= S:
        return 1
    r = R_init / S
    raw = math.floor(math.log(epsilon) / math.log(r))
    return max(1, min(int(raw), cap))


def _hist_bound(spec: ParamSpec) -> int:
    """Conservative integer bound for each input-history register."""
    return spec.Pmax


def _window_sum_expr(sigma: int) -> str:
    terms: List[str] = ["input_sum"]
    for e in range(1, sigma + 1):
        r_pow = " * ".join(["r_num"] * e)
        s_pow = " * ".join(["S_leak"] * e)
        terms.append(f"(({r_pow}) * in_hist_{e}) / ({s_pow})")
    return " + ".join(terms)


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
    if spec.sigma < 1:
        raise ValueError(f"[{spec.name}] sigma must be >= 1")

    r_frac = spec.R_init / spec.S
    p_ss = spec.w_exc / (1.0 - r_frac) if (1.0 - r_frac) > 0 else float("inf")
    if p_ss < spec.tau:
        raise ValueError(
            f"[{spec.name}] spike likely unreachable with excitation-only: P_ss~{p_ss:.2f} < tau={spec.tau}. "
            f"Increase w_exc or decrease R/S."
        )

    net_both = spec.w_exc + spec.w_inh
    if net_both >= spec.tau:
        print(
            f"[WARN {spec.name}] w_exc+w_inh={net_both} >= tau={spec.tau}: "
            f"inhibition cannot fully suppress excitation."
        )


def generate_lif_module(spec: ParamSpec) -> List[str]:
    """
    INPUT: ParamSpec describing one LIF parameter set.
    OUTPUT: list of NuSMV lines defining ``MODULE lif_<spec.name>(net_exc, net_inh, t)``.
    """
    mod_name = f"lif_{spec.name}"
    sigma = spec.sigma
    hbound = _hist_bound(spec)
    lines: List[str] = []
    lines.append(
        f"-- LIF module '{mod_name}': tau={spec.tau}, sigma={sigma}, "
        f"default w_exc={spec.w_exc}, w_inh={spec.w_inh}, "
        f"S={spec.S}, R_init={spec.R_init}, Pmax={spec.Pmax}"
    )
    lines.append(
        "-- net_exc / net_inh are weighted sums of the incoming edges (per-edge weights from the DSL)."
    )
    lines.append(
        f"-- σ-window update: p = sum_{{e=0}}^{{{sigma}}} (R/S)^e * input_sum(t-e); spike := (P >= tau)."
    )
    lines.append(f"MODULE {mod_name}(net_exc, net_inh, t)")
    lines.append("VAR")
    lines.append(f"  P     : 0..{spec.Pmax};")
    lines.append(f"  r_num : 0..{spec.S};")
    for e in range(1, sigma + 1):
        lines.append(f"  in_hist_{e} : -{hbound}..{hbound};")
    lines.append("")
    lines.append("DEFINE")
    lines.append(f"  Pmax   := {spec.Pmax};")
    lines.append(f"  tau    := {spec.tau};")
    lines.append(f"  S_leak := {spec.S};")
    lines.append("  input_sum := net_exc + net_inh;")
    lines.append(f"  window_sum := {_window_sum_expr(sigma)};")
    lines.append("  spike     := (P >= tau);")
    lines.append("")
    lines.append("ASSIGN")
    lines.append("  init(P) := 0;")
    lines.append(f"  init(r_num) := {spec.R_init};")
    for e in range(1, sigma + 1):
        lines.append(f"  init(in_hist_{e}) := 0;")
    lines.append("  -- Leak factor is FIXED per neuron type: r_num stays at R_init (R/S constant).")
    lines.append("  next(r_num) := r_num;")
    if sigma >= 1:
        lines.append(f"  next(in_hist_1) := spike ? 0 : input_sum;")
        for e in range(2, sigma + 1):
            lines.append(f"  next(in_hist_{e}) := spike ? 0 : in_hist_{e - 1};")
    lines.append("  next(P) :=")
    lines.append("    case")
    lines.append("      spike              : 0;")
    lines.append("      window_sum < 0     : 0;")
    lines.append("      window_sum > Pmax  : Pmax;")
    lines.append("      TRUE               : window_sum;")
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
