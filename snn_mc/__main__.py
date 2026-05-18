"""
Module entry: enables ``python -m snn_mc ...`` (delegates to cli.main).
"""

from snn_mc.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
