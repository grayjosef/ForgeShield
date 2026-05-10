"""Pytest configuration: ensure ``src/`` is importable without install.

Mirrors the documented run command::

    . .venv/bin/activate
    export PYTHONPATH=src
    python -m pytest -v

so test collection still works even if ``PYTHONPATH`` is not exported
(for IDE runs, etc.).
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
