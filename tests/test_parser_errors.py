"""Parser error messages and new DSL fields."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from snn_mc.dsl.parser import parse_text  # noqa: E402


def test_unknown_block_kind_suggestion() -> None:
    dsl = """
input stim
block sample_series input=stim N=2 prefix=c params=default
"""
    with pytest.raises(ValueError, match="Did you mean 'simple_series'"):
        parse_text(dsl, source_path=REPO / "examples" / "series_negloop.dsl")


def test_weights_and_auto_output_in_ir() -> None:
    # No output= / network_output anymore: simple_series auto-exposes its last neuron.
    dsl = """
horizon 30
input stim
block simple_series input=stim N=2 prefix=c weights=3,5 params=default
"""
    ir = parse_text(dsl, source_path=REPO / "examples" / "series_negloop.dsl")
    assert ir.horizon == 30
    assert "c2" in ir.network_outputs
    assert "c1" not in ir.network_outputs
    weights = [e.weight for e in ir.edges]
    assert 3 in weights and 5 in weights
    assert ir.neuron_params.get("c1") == "default"


def test_threshold_override_clones_only_when_different() -> None:
    dsl = """
input stim
block simple_series input=stim N=2 prefix=c threshold=6 params=default
"""
    ir = parse_text(dsl, source_path=REPO / "examples" / "series_negloop.dsl")
    # threshold differs from default tau => a dedicated param set with tau=6 is created.
    assert ir.neuron_params.get("c1") == "default_tau6"
    assert ir.params["default_tau6"].tau == 6


def test_builtin_neuron_types_available() -> None:
    dsl = """
input stim
block simple_series input=stim N=2 prefix=c params=slow
"""
    ir = parse_text(dsl, source_path=REPO / "examples" / "series_negloop.dsl")
    # The three built-in types exist with the documented (tau, leak) values.
    assert ir.params["quick"].tau == 2 and ir.params["quick"].R_init == 3
    assert ir.params["intermediate"].tau == 4 and ir.params["intermediate"].R_init == 2
    assert ir.params["slow"].tau == 6 and ir.params["slow"].R_init == 1
    # Edge weights follow the selected type (slow => w_exc=5), not always 'default'.
    assert all(e.weight == 5 for e in ir.edges if e.weight > 0)
    assert ir.neuron_params.get("c1") == "slow"


def test_negative_loop_exposes_all_loop_neurons() -> None:
    dsl = """
input stim
block negative_loop input=stim A=a B=b params=quick
"""
    ir = parse_text(dsl, source_path=REPO / "examples" / "negloop_only.dsl")
    assert set(ir.network_outputs) == {"a", "b"}


def test_fixed_leak_in_emitted_smv(tmp_path) -> None:
    import sys as _sys

    _sys.path.insert(0, str(REPO))
    from snn_mc.cli import main as cli_main  # noqa: WPS433

    out = tmp_path / "leak"
    rc = cli_main([
        "run", str(REPO / "examples" / "series_only.dsl"),
        "--out", str(out), "--skip-verify",
    ])
    assert rc == 0
    model = (out / "model.smv").read_text(encoding="utf-8")
    assert "next(r_num) := r_num;" in model
    # The old nondeterministic leak transition must be gone.
    assert "t < 4 : r_num" not in model
