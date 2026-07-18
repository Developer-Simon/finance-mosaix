import json
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
ELECTRON_DIR = ROOT_DIR / "electron"

if str(ROOT_DIR / "src") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "src"))

import version
from version import get_canonical_version


def normalize_electron_package_version(version: str) -> str:
    return re.sub(r"\.post(?=\d+)", "-post", version).replace(
        ".dev", "-dev"
    )


def run_electron_version_sync() -> None:
    node_executable = shutil.which("node")
    if node_executable is None:
        raise unittest.SkipTest("Node.js is required to run Electron version sync")

    env = dict(**subprocess.os.environ)
    env["PYTHON_EXECUTABLE"] = sys.executable

    result = subprocess.run(
        [node_executable, str(ELECTRON_DIR / "sync_version.js")],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Failed to run electron/sync_version.js:\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


class VersionSyncTestCase(unittest.TestCase):
    def test_electron_package_version_matches_canonical_version(self):
        run_electron_version_sync()

        electron_package_path = ELECTRON_DIR / "package.json"
        with electron_package_path.open("r", encoding="utf-8") as handle:
            package_json = json.load(handle)

        electron_version = package_json.get("version")
        canonical_version = get_canonical_version()
        normalized_canonical_version = normalize_electron_package_version(canonical_version)

        self.assertIsNotNone(electron_version, "electron/package.json must declare a version")
        self.assertEqual(
            electron_version,
            normalized_canonical_version,
            "Electron package version must match the normalized canonical project version",
        )


class CanonicalVersionResolutionTestCase(unittest.TestCase):
    def test_falls_back_to_pyproject_setuptools_scm_fallback_before_installed_metadata(self):
        with (
            mock.patch.object(version, "_read_pyproject_version", return_value=None),
            mock.patch.object(version, "_resolve_setuptools_scm_version", return_value=None),
            mock.patch.object(version, "_read_version_file", return_value=None),
            mock.patch.object(version, "_read_packaged_version_file", return_value=None),
            mock.patch.object(version, "_read_setuptools_scm_fallback_version", return_value="0.2.0"),
            mock.patch.object(version, "_read_installed_package_version", return_value="0.0.0"),
        ):
            self.assertEqual(get_canonical_version(), "0.2.0")

    def test_ignores_placeholder_installed_version(self):
        with mock.patch.object(version, "metadata_version", return_value="0.0.0"):
            self.assertIsNone(version._read_installed_package_version())


if __name__ == "__main__":
    unittest.main()
