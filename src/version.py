from __future__ import annotations

import subprocess
from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path
from typing import Any, Callable

try:
    from setuptools_scm.version import ScmVersion
except ImportError:  # allow module import without setuptools_scm installed
    ScmVersion = Any

ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT_DIR / "VERSION"
PACKAGED_VERSION_FILE = ROOT_DIR / "electron" / "VERSION"
PYPROJECT_FILE = ROOT_DIR / "pyproject.toml"
PACKAGE_NAME = "finance-mosaix"
PLACEHOLDER_VERSION = "0.0.0"


def _read_pyproject_config() -> dict[str, Any] | None:
    if not PYPROJECT_FILE.exists():
        return None

    try:
        import tomllib

        with PYPROJECT_FILE.open("rb") as handle:
            config = tomllib.load(handle)
    except Exception:
        return None

    return config


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
        version = metadata_version(PACKAGE_NAME).strip()
    except PackageNotFoundError:
        return None
    except Exception:
        return None

    # Some build flows can install an interim placeholder version.
    if version == PLACEHOLDER_VERSION:
        return None

    return version or None


def _read_pyproject_version() -> str | None:
    config = _read_pyproject_config()
    if config is None:
        return None

    version = config.get("project", {}).get("version")
    return str(version).strip() if version else None


def _read_setuptools_scm_fallback_version() -> str | None:
    config = _read_pyproject_config()
    if config is None:
        return None

    version = config.get("tool", {}).get("setuptools_scm", {}).get("fallback_version")
    return str(version).strip() if version else None


def _run_git_command(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ("git",) + args,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip()


def _git_has_ref(ref: str) -> bool:
    return _run_git_command("rev-parse", "--verify", ref)[0] == 0


def _git_count_commits(range_spec: str) -> int | None:
    code, output = _run_git_command("rev-list", "--count", range_spec)
    if code == 0 and output.isdigit():
        return int(output)
    return None


def _get_latest_tag(ref: str | None = None) -> str | None:
    args = ("describe", "--tags", "--abbrev=0")
    if ref is not None:
        args += (ref,)
    code, output = _run_git_command(*args)
    return output if code == 0 and output else None


def _select_master_ref() -> str | None:
    for ref in ("origin/master", "origin/main", "master", "main"):
        if _git_has_ref(ref):
            return ref
    return None


def _master_patch_distance(tag_ref: str, master_ref: str) -> int:
    count = _git_count_commits(f"{tag_ref}..{master_ref}")
    return count or 0


def _branch_post_distance(master_ref: str) -> int:
    code, merge_base = _run_git_command("merge-base", "HEAD", master_ref)
    if code != 0 or not merge_base:
        return 0

    count = _git_count_commits(f"{merge_base}..HEAD")
    return count or 0


def bump_patch_by_distance(version: ScmVersion) -> str:
    if version.exact:
        return version.format_with("{tag}")

    release = list(version.tag.release)
    while len(release) < 3:
        release.append(0)
    major, minor, _ = release[:3]

    master_ref = _select_master_ref()
    tag_ref = _get_latest_tag(master_ref) or str(version.tag)
    master_patch = _master_patch_distance(tag_ref, master_ref) if master_ref is not None else 0

    if master_ref is not None and version.branch is not None:
        branch_name = version.branch.rsplit("/", 1)[-1]
        if branch_name not in {"master", "main"}:
            branch_post = _branch_post_distance(master_ref)
            if branch_post > 0:
                return f"{major}.{minor}.{master_patch}.post{branch_post}"

    return f"{major}.{minor}.{master_patch}"


def _resolve_setuptools_scm_version() -> str | None:
    try:
        from setuptools_scm import get_version
    except ImportError:
        return None

    try:
        return get_version(
            root=str(ROOT_DIR),
            version_scheme=bump_patch_by_distance,
            local_scheme="dirty-tag",
        )
    except Exception:
        return None


def get_canonical_version() -> str:
    strategy: list[Callable[[], str | None]] = [
        _read_pyproject_version,
        _resolve_setuptools_scm_version,
        _read_version_file,
        _read_packaged_version_file,
        _read_setuptools_scm_fallback_version,
        _read_installed_package_version,
    ]

    for getter in strategy:
        version = getter()
        if version:
            return version

    return "0.0.0"


if __name__ == "__main__":
    print(get_canonical_version())
