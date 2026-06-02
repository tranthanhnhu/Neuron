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


def test_weights_and_output_in_ir() -> None:
    dsl = """
horizon 30
input stim
block simple_series input=stim output=c2 N=2 prefix=c weights=3,5 threshold=4 params=default
"""
    ir = parse_text(dsl, source_path=REPO / "examples" / "series_negloop.dsl")
    assert ir.horizon == 30
    assert "c2" in ir.network_outputs
    weights = [e.weight for e in ir.edges]
    assert 3 in weights and 5 in weights
    # threshold == default tau (4) => no redundant clone, neurons keep base set.
    assert ir.neuron_params.get("c1") == "default"
    assert "default_tau4" not in ir.params


def test_threshold_override_clones_only_when_different() -> None:
    dsl = """
input stim
block simple_series input=stim N=2 prefix=c threshold=6 params=default
"""
    ir = parse_text(dsl, source_path=REPO / "examples" / "series_negloop.dsl")
    # threshold differs from default tau => a dedicated param set with tau=6 is created.
    assert ir.neuron_params.get("c1") == "default_tau6"
    assert ir.params["default_tau6"].tau == 6
