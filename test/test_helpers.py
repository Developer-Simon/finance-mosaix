import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
DASHBOARD_DIR = ROOT_DIR

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from db_schema import init_database


def sample_excel_path(sample_name: str = "Sample.xlsx") -> Path:
    return ROOT_DIR / "Import" / sample_name


def create_temp_database():
    temp_dir = tempfile.TemporaryDirectory(prefix="finance-test-", dir=str(ROOT_DIR))
    db_path = Path(temp_dir.name) / "finance_test.duckdb"
    conn = init_database(str(db_path))
    conn.close()
    return temp_dir, db_path


def seed_basic_finance_data(conn: duckdb.DuckDBPyConnection):
    conn.execute(
        "INSERT INTO accounts (account_id, account_name, account_type) VALUES (1, 'Checking', 'bank')"
    )
    conn.execute(
        "INSERT INTO categories (category_id, category_name, category_type) VALUES (1, 'Groceries', 'expense')"
    )
    conn.execute(
        "INSERT INTO categories (category_id, category_name, category_type) VALUES (2, 'Salary', 'income')"
    )
    conn.execute(
        "INSERT INTO cash_transactions (transaction_id, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet) "
        "VALUES (1, 'Weekly groceries', 1, 1, -30.50, '2026-07-01', 969.50, 'test')"
    )
    conn.execute(
        "INSERT INTO cash_transactions (transaction_id, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet) "
        "VALUES (2, 'Salary deposit', 1, 2, 2500.00, '2026-07-02', 3469.50, 'test')"
    )
    conn.execute(
        "INSERT INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) "
        "VALUES (1, 'test', '2026-07-01', 1, 'Sample Equity', 'SAMPLE', 10.0, 100.0, 100.0, 0.0, 0.0, 1000.00, 1000.00)"
    )
    conn.execute(
        "INSERT INTO goods_valuations (valuation_id, source_sheet, valuation_date, row_nr, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value) "
        "VALUES (1, 'test', '2026-07-02', 1, 'Laptop', 1500.00, 0.10, 1500.00, -100.00, 1400.00)"
    )
    conn.execute(
        "INSERT INTO goods_valuations (valuation_id, source_sheet, valuation_date, row_nr, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value) "
        "VALUES (2, 'test', '2026-07-03', 2, 'Monitor', 800.00, 0.10, 800.00, -100.00, 600.00)"
    )
    conn.execute(
        "INSERT INTO interest_balance_changes (change_id, source_sheet, balance_date, account_name, balance, previous_balance, delta) "
        "VALUES (1, 'test', '2026-07-03', 'Festgeld', 2000.00, 1800.00, 200.00)"
    )
    conn.commit()


class FinanceDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.db_path = create_temp_database()
        self.conn = duckdb.connect(str(self.db_path))
        seed_basic_finance_data(self.conn)

    def tearDown(self):
        if getattr(self, 'conn', None) is not None:
            self.conn.close()
        self.temp_dir.cleanup()
