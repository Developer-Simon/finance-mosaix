"""Central resolution of data locations (database, sample database, settings).

If the environment variable FINANCE_MOSAIX_DATA_DIR is set, all data files live in
that directory. Otherwise the historical locations inside the repository are used.
"""

import os
from pathlib import Path

DATA_DIR_ENV = "FINANCE_MOSAIX_DATA_DIR"

_PACKAGE_DIR = Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    value = os.environ.get(DATA_DIR_ENV)
    if value:
        path = Path(value)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return repo_root()


def settings_path() -> Path:
    if os.environ.get(DATA_DIR_ENV):
        return data_dir() / "settings.json"
    return _PACKAGE_DIR / "dashboard" / "settings.json"


def default_db_path() -> Path:
    return data_dir() / "finance.duckdb"


def sample_db_path() -> Path:
    return data_dir() / "finance_sample.duckdb"


def resolve_db_path(value: str | None) -> Path:
    if not value or not value.strip():
        return default_db_path().resolve()
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (data_dir() / path).resolve()
