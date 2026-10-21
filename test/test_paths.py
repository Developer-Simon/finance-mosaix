import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from finance_mosaix.core.paths import (
    DATA_DIR_ENV,
    data_dir,
    default_db_path,
    repo_root,
    resolve_db_path,
    sample_db_path,
    settings_path,
)
from finance_mosaix.dashboard.onboarding import _resolve_database_path


class DataPathsWithoutEnvTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(DATA_DIR_ENV, None)

    def test_without_env_uses_repo_root(self):
        self.assertEqual(data_dir(), repo_root())
        self.assertEqual(default_db_path(), repo_root() / "finance.duckdb")
        self.assertEqual(settings_path(), repo_root() / "src/finance_mosaix/dashboard/settings.json")


class DataPathsWithEnvTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="finance-paths-test-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        patcher = mock.patch.dict(os.environ, {DATA_DIR_ENV: str(self.tmp)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_with_env_uses_data_dir(self):
        self.assertEqual(default_db_path(), self.tmp / "finance.duckdb")
        self.assertEqual(settings_path(), self.tmp / "settings.json")
        self.assertEqual(sample_db_path(), self.tmp / "finance_sample.duckdb")

    def test_with_env_creates_missing_dir(self):
        target = self.tmp / "a" / "b"
        os.environ[DATA_DIR_ENV] = str(target)
        self.assertTrue(data_dir().is_dir())

    def test_resolve_db_path_relative_absolute_empty(self):
        self.assertEqual(resolve_db_path("x.duckdb"), self.tmp / "x.duckdb")
        absolute = self.tmp / "elsewhere" / "y.duckdb"
        self.assertEqual(resolve_db_path(str(absolute)), absolute.resolve())
        self.assertEqual(resolve_db_path(""), default_db_path())
        self.assertEqual(resolve_db_path(None), default_db_path())

    def test_resolve_db_path_handles_spaces(self):
        self.assertEqual(
            resolve_db_path("Meine Daten/ö.duckdb"),
            self.tmp / "Meine Daten" / "ö.duckdb",
        )

    def test_onboarding_resolve_uses_data_dir(self):
        self.assertEqual(
            _resolve_database_path("", demo_mode=True),
            str(self.tmp / "finance_sample.duckdb"),
        )


if __name__ == "__main__":
    unittest.main()
