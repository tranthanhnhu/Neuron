"""
Thin wrapper around the NuSMV command-line tool.

Public API:
    find_nusmv()                       -> str          (path to executable; just the name on miss).
    run_nusmv(combined_smv, log_path)  -> int          (exit code; log written to ``log_path``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

_PKG_ROOT = Path(__file__).resolve().parents[2]  # NewStructure/


def _local_nusmv_candidates() -> list[Path]:
    """Bundled or manually unpacked NuSMV under ``tools/nusmv/`` (see tools/README.md)."""
    base = _PKG_ROOT / "tools" / "nusmv"
    if not base.is_dir():
        return []
    found: list[Path] = []
    for name in ("NuSMV.exe", "nusmv", "NuSMV"):
        found.extend(sorted(base.rglob(name)))
    return found


def find_nusmv() -> str:
    """
    INPUT: nothing.
    OUTPUT: full path to the first NuSMV binary found, or the literal name ``NuSMV`` on miss.

    Search order: ``SNN_MC_NUSMV`` env, PATH (``nusmv`` / ``NuSMV``), then ``tools/nusmv/**/bin``.
    Windows builds typically expose ``NuSMV.exe``; Linux/macOS ``nusmv``.
    """
    env = os.environ.get("SNN_MC_NUSMV")
    if env:
        p = Path(env)
        if p.is_file():
            return str(p.resolve())

    for name in ("nusmv", "NuSMV"):
        p = shutil.which(name)
        if p:
            return p

    for candidate in _local_nusmv_candidates():
        if candidate.is_file():
            return str(candidate.resolve())

    return "NuSMV"


def run_nusmv(
    combined_smv: Path,
    log_path: Path,
    *,
    nusmv_exe: Optional[str] = None,
) -> Tuple[int, str]:
    """
    INPUT:
        combined_smv  — path to the single NuSMV input file.
        log_path      — where to persist NuSMV stdout+stderr.
        nusmv_exe     — optional override for the executable (defaults to ``find_nusmv()``).
    OUTPUT: (exit_code, log_text). The log is also written to ``log_path``.
    RAISES: FileNotFoundError if the chosen executable cannot be located.
    """
    exe = nusmv_exe or find_nusmv()
    if not shutil.which(exe) and not Path(exe).is_file():
        raise FileNotFoundError(f"NuSMV not found: {exe}")
    proc = subprocess.run([exe, str(combined_smv)], capture_output=True, text=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    log_path.write_text(text, encoding="utf-8")
    return proc.returncode, text
