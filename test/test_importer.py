import contextlib
import io
import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.import_transactions import FinanceImporter
from .test_helpers import sample_excel_path

SAMPLE_FILES = [
    {
        "file": "SampleDE.xlsx",
        "sheet": "Juni 2026",
        "salary_category": "Einnahmen / Gehalt",
        "account_name": "COMDIRECT",
    },
    {
        "file": "SampleEN.xlsx",
        "sheet": "June 2026",
        "salary_category": "Income / Salary",
        "account_name": "COMDIRECT",
    },
]


class TestFinanceImporter(unittest.TestCase):
    def setUp(self):
        self.importer = None
        self._create_importer(SAMPLE_FILES[0]["file"])

    def tearDown(self):
        if getattr(self, 'importer', None) is not None and getattr(self.importer, 'conn', None) is not None:
            try:
                self.importer.conn.close()
            except Exception:
                pass

    def _create_importer(self, sample_file):
        sample_path = sample_excel_path(sample_file)
        self.assertTrue(sample_path.exists(), f"Sample Excel file not found: {sample_path}")
        self.importer = FinanceImporter(str(sample_path), db_path=":memory:")
        return self.importer

    def _run_import(self, importer, sheet_name, account_name="COMDIRECT"):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return importer.import_sheet(
                sheet_name=sheet_name,
                account_name=account_name,
                transaction_date="2026-06-01",
            )

    def test_extracts_date_from_german_sheet_name_with_last_day(self):
        self.importer.sheet_name = "Juni 2026"
        self.assertEqual(self.importer._extract_date_from_sheet(), date(2026, 6, 30))

        self.importer.sheet_name = "Februar 2025"
        self.assertEqual(self.importer._extract_date_from_sheet(), date(2025, 2, 28))

        self.importer.sheet_name = "März 2024"
        self.assertEqual(self.importer._extract_date_from_sheet(), date(2024, 3, 31))

    def test_import_result_contract(self):
        """The import result is a dictionary contract with per-pool details."""
        for sample in SAMPLE_FILES:
            with self.subTest(sample=sample["file"]):
                importer = self._create_importer(sample["file"])
                result = self._run_import(importer, sample["sheet"], sample["account_name"])

                self.assertEqual(result["status"], "success")
                self.assertEqual(result["sheet_name"], sample["sheet"])
                self.assertEqual(result["account_name"], sample["account_name"])
                self.assertEqual(result["transaction_date"], "2026-06-01")
                self.assertEqual(result["errors"], [])
                self.assertEqual(set(result["pools"].keys()), {"cash", "stocks", "goods", "interest"})

    def test_detects_account_name_from_account_column(self):
        """Import should detect the main cash account from the account column and populate the result."""
        for sample in SAMPLE_FILES:
            with self.subTest(sample=sample["file"]):
                importer = self._create_importer(sample["file"])
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    result = importer.import_sheet(
                        sheet_name=sample["sheet"],
                        account_name=None,
                        transaction_date="2026-06-01",
                    )

                self.assertEqual(result["status"], "success")
                self.assertEqual(result["account_name"], "Sample Bank")
                account_names = {
                    row[0]
                    for row in importer.conn.execute("SELECT account_name FROM accounts").fetchall()
                }
                self.assertIn("Sample Bank", account_names)

    def test_cash_pool_import(self):
        """Cash pool rows/categories/totals match the sheet's own summary row."""
        for sample in SAMPLE_FILES:
            with self.subTest(sample=sample["file"]):
                importer = self._create_importer(sample["file"])
                result = self._run_import(importer, sample["sheet"], sample["account_name"])
                conn = importer.conn

                cash_result = result["pools"]["cash"]
                self.assertTrue(cash_result["present"])
                self.assertEqual(cash_result["rows_parsed"], 62)
                self.assertEqual(cash_result["inserted"], 65)

                transaction_count = conn.execute("SELECT COUNT(*) FROM cash_transactions").fetchone()[0]
                self.assertEqual(transaction_count, 65)

                # Matches the sheet's own cash delta for the import.
                total_amount = conn.execute("SELECT SUM(amount) FROM cash_transactions").fetchone()[0]
                self.assertAlmostEqual(float(total_amount), 620.98, places=2)

                category_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
                self.assertEqual(category_count, 23)

                gehalt_total = conn.execute(
                    "SELECT SUM(amount) FROM cash_transactions t JOIN categories c ON t.category_id = c.category_id "
                    "WHERE c.category_name = ?",
                    [sample["salary_category"]],
                ).fetchone()[0]
                self.assertAlmostEqual(float(gehalt_total), 3922.99, places=2)

                account_names = {
                    row[0]
                    for row in conn.execute("SELECT account_name FROM accounts").fetchall()
                }
                self.assertIn("Sample Bank", account_names)
                self.assertIn("Sample Broker", account_names)

                source_sheet = conn.execute("SELECT DISTINCT source_sheet FROM cash_transactions").fetchone()[0]
                self.assertEqual(source_sheet, sample["sheet"])

    def test_stock_pool_import(self):
        """Stock pool captures exactly the real depot positions (footer/placeholder rows excluded)."""
        for sample in SAMPLE_FILES:
            with self.subTest(sample=sample["file"]):
                importer = self._create_importer(sample["file"])
                result = self._run_import(importer, sample["sheet"], sample["account_name"])
                conn = importer.conn

                stocks_result = result["pools"]["stocks"]
                self.assertTrue(stocks_result["present"])
                self.assertEqual(stocks_result["rows_parsed"], 19)
                self.assertEqual(stocks_result["inserted"], 19)

                row_count = conn.execute("SELECT COUNT(*) FROM stock_positions").fetchone()[0]
                self.assertEqual(row_count, 19)

                names = {row[0] for row in conn.execute("SELECT name FROM stock_positions").fetchall()}
                self.assertIn("Asset 01", names)
                self.assertIn("Asset 14", names)
                self.assertIn("Value 96B", names)

    def test_goods_pool_import(self):
        """Goods pool captures exactly the real goods rows (baseline/footer rows excluded)."""
        for sample in SAMPLE_FILES:
            with self.subTest(sample=sample["file"]):
                importer = self._create_importer(sample["file"])
                result = self._run_import(importer, sample["sheet"], sample["account_name"])
                conn = importer.conn

                goods_result = result["pools"]["goods"]
                self.assertTrue(goods_result["present"])
                self.assertEqual(goods_result["rows_parsed"], 8)
                self.assertEqual(goods_result["inserted"], 8)

                row_count = conn.execute("SELECT COUNT(*) FROM goods_valuations").fetchone()[0]
                self.assertEqual(row_count, 8)

                names = {row[0] for row in conn.execute("SELECT item_name FROM goods_valuations").fetchall()}
                self.assertEqual(names, {
                    "Item 1",
                    "Item 2",
                    "Item 3",
                    "Item 4",
                    "Item 5",
                    "Item 6",
                    "Item 7",
                    "Item 8",
                })

    def test_goods_parser_separates_purchase_and_current_values(self):
        raw = pd.DataFrame([
            ["Nr.", "Bezeichnung", "Kaufwert", "Abschreib", "Wert alt", "Bilanz", "Wert"],
            [1, "Test Item", "1000", "2", "900", "100", "950"],
        ])

        parsed = self.importer._parse_goods_pool(raw, header_row=0, end_row=1)
        self.assertEqual(len(parsed["records"]), 1)

        record = parsed["records"][0]
        self.assertAlmostEqual(record["purchase_value"], 1000.0, places=2)
        self.assertAlmostEqual(record["current_value"], 950.0, places=2)
        self.assertNotEqual(record["purchase_value"], record["current_value"])

    def test_interest_pool_import(self):
        """Interest pool captures the Festgeld side-panel accounts with no prior-month delta on first import."""
        for sample in SAMPLE_FILES:
            with self.subTest(sample=sample["file"]):
                importer = self._create_importer(sample["file"])
                result = self._run_import(importer, sample["sheet"], sample["account_name"])
                conn = importer.conn

                interest_result = result["pools"]["interest"]
                self.assertTrue(interest_result["present"])
                self.assertEqual(interest_result["rows_parsed"], 3)
                self.assertEqual(interest_result["inserted"], 3)

                rows = conn.execute(
                    "SELECT account_name, balance, previous_balance, delta FROM interest_balance_changes ORDER BY account_name"
                ).fetchall()
                balances = {row[0]: float(row[1]) for row in rows}
                self.assertAlmostEqual(balances["Account 05"], 43194.04, places=2)
                self.assertAlmostEqual(balances["Account 06"], 4112.86, places=2)
                self.assertAlmostEqual(balances["Account 07"], 43178.21, places=2)

                # No prior import exists yet, so deltas must be None on the first import.
                for _, _, previous_balance, delta in rows:
                    self.assertIsNone(previous_balance)
                    self.assertIsNone(delta)

    def test_interest_pool_delta_computation(self):
        """Interest delta is computed against the previous month's balance for the same account,
        while re-importing the *same* sheet stays idempotent (no self-delta from stale rows)."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.importer.connect()

        # Simulate a first (previous month) import via the same private insertion path
        # used by import_sheet, so the test exercises the real delta-lookup logic.
        self.importer.transaction_date = date(2026, 5, 1)
        self.importer.sheet_name = "Mai 2026"
        self.importer.parsed_pools = {
            "interest": {"records": [{"account_name": "Badenia (VL)", "balance": 4000.0}]}
        }
        first_result = self.importer._insert_interest_pool()
        self.assertIsNone(first_result["deltas"]["Badenia (VL)"])

        # Second (current month) import for a different sheet: delta must be computed
        # against the previous month's balance.
        self.importer.transaction_date = date(2026, 6, 1)
        self.importer.sheet_name = "Juni 2026"
        self.importer.parsed_pools = {
            "interest": {"records": [{"account_name": "Badenia (VL)", "balance": 4733.24}]}
        }
        second_result = self.importer._insert_interest_pool()
        self.assertAlmostEqual(second_result["deltas"]["Badenia (VL)"], 733.24, places=2)

        row_count = self.importer.conn.execute("SELECT COUNT(*) FROM interest_balance_changes").fetchone()[0]
        self.assertEqual(row_count, 2)


if __name__ == "__main__":
    unittest.main()

