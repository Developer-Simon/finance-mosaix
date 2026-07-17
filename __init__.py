"""FinanceMosaix package alias for Finance mosaix.

This package exists as a code-friendly alias to the local finance-mosaix checkout,
so internal imports can use `FinanceMosaix.*` while the local folder remains
named `finance-mosaix`.
"""

from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Allow the alias package to expose the existing finance-mosaix package contents.
if '__path__' in globals():
    __path__.insert(0, str(ROOT_DIR))
else:
    __path__ = [str(ROOT_DIR)]

__all__ = ["dashboard", "src"]