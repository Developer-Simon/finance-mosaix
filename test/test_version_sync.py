import json
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
ELECTRON_DIR = ROOT_DIR / "electron"

if str(ROOT_DIR / "src") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "src"))

from version import get_canonical_version


class VersionSyncTestCase(unittest.TestCase):
    def test_electron_package_version_matches_canonical_version(self):
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
