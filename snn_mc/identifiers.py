"""
NuSMV identifier sanitization.

NuSMV reserves single uppercase letters used as temporal operators (A, E, G, F, X, U)
and several keywords (MODULE, VAR, ASSIGN, ...). When a DSL writer uses one of these
as a neuron or input name, we transparently prefix it with ``n_`` so the generated SMV
still parses.

KEY FUNCTIONS:
    sanitize_identifier(name) -> str
    rename_in_spec_text(text, mapping) -> str
"""

from __future__ import annotations

import re
from typing import Dict, Set

# Names NuSMV's grammar treats as reserved tokens. Anything that collides becomes ``n_<name>``.
_NUSMV_RESERVED: Set[str] = {
    "A", "E", "G", "F", "X", "U",
    "TRUE", "FALSE",
    "MODULE", "VAR", "DEFINE", "ASSIGN",
    "INIT", "TRANS", "INVAR",
    "CTLSPEC", "LTLSPEC", "INVARSPEC", "SPEC",
    "main",
}


def sanitize_identifier(name: str) -> str:
    """
    INPUT: a DSL identifier (neuron, input, or const name).
    OUTPUT: same name if NuSMV-safe; otherwise prefixed with ``n_``.

    A name is unsafe if it is a single uppercase letter (NuSMV temporal operator)
    or matches a NuSMV reserved keyword.
    """
    if re.fullmatch(r"[A-Z]", name) or name in _NUSMV_RESERVED:
        return f"n_{name}"
    return name


def rename_in_spec_text(text: str, mapping: Dict[str, str]) -> str:
    """
    Rewrite identifiers inside an SMV spec string using ``mapping`` (old -> new).

    INPUT:
      - ``text`` — raw spec text written by the user (CTLSPEC / LTLSPEC body).
      - ``mapping`` — DSL name -> NuSMV-safe name.
    OUTPUT: ``text`` with every standalone occurrence of an old name replaced by its new name.
            Substrings inside larger identifiers are preserved (word-boundary regex).
    """
    if not mapping:
        return text
    out = text
    # Replace longest names first so that ``foo`` does not eat the prefix of ``foobar``.
    for src in sorted(mapping.keys(), key=len, reverse=True):
        dst = mapping[src]
        if src == dst:
            continue
        out = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(src)}(?![A-Za-z0-9_])", dst, out)
    return out
