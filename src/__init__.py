"""
Finance mosaix core package exports.

Expose top-level helpers for database init, importing, and query access.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = [
    "init_database",
    "get_connection",
    "show_schema",
    "FinanceImporter",
    "FinanceQueries",
    "print_balance_summary",
    "print_category_summary",
]

_lazy_modules = {
    "init_database": "db_schema",
    "get_connection": "db_schema",
    "show_schema": "db_schema",
    "FinanceImporter": "import_transactions",
    "FinanceQueries": "query_finance",
    "print_balance_summary": "query_finance",
    "print_category_summary": "query_finance",
}


def __getattr__(name: str) -> Any:
    if name not in _lazy_modules:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = importlib.import_module(f".{_lazy_modules[name]}", __name__)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
