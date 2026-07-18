from __future__ import annotations

import subprocess
from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path
from typing import Callable

ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT_DIR / "VERSION"
PACKAGED_VERSION_FILE = ROOT_DIR / "electron" / "VERSION"
PYPROJECT_FILE = ROOT_DIR / "pyproject.toml"
PACKAGE_NAME = "finance-mosaix"


def _read_version_file() -> str | None:
    if not VERSION_FILE.exists():
        return None

    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    return version or None


def _read_packaged_version_file() -> str | None:
    if not PACKAGED_VERSION_FILE.exists():
        return None

    version = PACKAGED_VERSION_FILE.read_text(encoding="utf-8").strip()
    return version or None


def _read_installed_package_version() -> str | None:
    try:
        return metadata_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return None
    except Exception:
        return None


def _read_pyproject_version() -> str | None:
    if not PYPROJECT_FILE.exists():
        return None

    try:
        import tomllib

        with PYPROJECT_FILE.open("rb") as handle:
            config = tomllib.load(handle)
    except Exception:
        return None

    version = config.get("project", {}).get("version")
    return str(version).strip() if version else None


def _resolve_setuptools_scm_version() -> str | None:
    try:
        from setuptools_scm import get_version
    except ImportError:
        return None

    try:
        return get_version(root=str(ROOT_DIR), version_scheme="post-release", local_scheme="dirty-tag")
    except Exception:
        return None


def get_canonical_version() -> str:
    strategy: list[Callable[[], str | None]] = [
        _read_installed_package_version,
        _read_pyproject_version,
        _resolve_setuptools_scm_version,
        _read_version_file,
        _read_packaged_version_file,
    ]

    for getter in strategy:
        version = getter()
        if version:
            return version

    return "0.0.0"


if __name__ == "__main__":
    print(get_canonical_version())
