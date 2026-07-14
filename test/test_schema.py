import duckdb
import unittest
from pathlib import Path

from test_helpers import FinanceDatabaseTestCase


class TestDatabaseSchema(FinanceDatabaseTestCase):
    def test_schema_has_expected_tables(self):
        conn = self.conn
        tables = [row[0] for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()]

        expected_tables = [
            'accounts',
            'account_balances',
            'cash_transactions',
            'categories',
            'goods_valuations',
            'interest_balance_changes',
            'main_categories',
            'stock_positions',
            'sub_categories',
        ]

        for table_name in expected_tables:
            self.assertIn(table_name, tables)

    def test_categories_table_uses_combo_ids(self):
        conn = self.conn
        category_columns = [row[1] for row in conn.execute("PRAGMA table_info(categories)").fetchall()]
        self.assertIn('main_category_id', category_columns)
        self.assertIn('sub_category_id', category_columns)
        self.assertIn('category_name', category_columns)

    def test_cash_transactions_references_category_id(self):
        conn = self.conn
        cash_columns = [row[1] for row in conn.execute("PRAGMA table_info(cash_transactions)").fetchall()]
        self.assertIn('category_id', cash_columns)
        self.assertNotIn('main_category_id', cash_columns)
        self.assertNotIn('sub_category_id', cash_columns)

    def test_legacy_migration_updates_category_structure(self):
        legacy_db_path = Path(self.temp_dir.name) / "legacy.duckdb"
        legacy_conn = duckdb.connect(str(legacy_db_path))

        legacy_conn.execute(
            "CREATE TABLE IF NOT EXISTS accounts (account_id INTEGER PRIMARY KEY, account_name VARCHAR, account_type VARCHAR)"
        )
        legacy_conn.execute(
            "CREATE TABLE IF NOT EXISTS categories (category_id INTEGER PRIMARY KEY, category_name VARCHAR, category_type VARCHAR)"
        )
        legacy_conn.execute(
            "CREATE TABLE IF NOT EXISTS cash_transactions (transaction_id INTEGER, row_nr INTEGER, description VARCHAR, account_name VARCHAR, category_id INTEGER, amount DECIMAL(14,2), transaction_date DATE, balance_after DECIMAL(14,2), source_sheet VARCHAR, section_name VARCHAR, import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        legacy_conn.execute(
            "INSERT INTO categories (category_id, category_name, category_type) VALUES (?, ?, ?)",
            [1, 'Food/Restaurants/Delivery', 'expense']
        )
        legacy_conn.execute(
            "INSERT INTO cash_transactions (transaction_id, row_nr, description, account_name, category_id, amount, transaction_date, balance_after, source_sheet) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [1, 1, 'Legacy expense', 'Checking', 1, -50.00, '2026-07-01', 950.00, 'legacy']
        )
        legacy_conn.commit()
        legacy_conn.close()

        from query_finance import FinanceQueries

        queries = FinanceQueries(str(legacy_db_path))

        migrated_rows = queries.conn.execute(
            "SELECT COUNT(*) FROM cash_transactions WHERE account_id IS NOT NULL"
        ).fetchone()[0]
        self.assertEqual(migrated_rows, 1)

        migrated_main = queries.conn.execute(
            "SELECT main_category_name FROM main_categories ORDER BY main_category_name"
        ).fetchall()
        self.assertEqual(migrated_main, [('Food',)])
