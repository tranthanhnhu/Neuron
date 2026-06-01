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
    assert ir.neuron_params.get("c1") == "default_tau4"
