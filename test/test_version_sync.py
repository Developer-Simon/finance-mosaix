import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
ELECTRON_DIR = ROOT_DIR / "electron"

if str(ROOT_DIR / "src") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "src"))

from version import get_canonical_version


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

        self.assertIsNotNone(electron_version, "electron/package.json must declare a version")
        self.assertEqual(
            electron_version,
            canonical_version,
            "Electron package version must match the canonical project version",
        )


if __name__ == "__main__":
    unittest.main()
