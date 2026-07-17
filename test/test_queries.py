import datetime
import unittest

import duckdb

from .test_helpers import FinanceDatabaseTestCase
from query_finance import FinanceQueries
from stock_queries import StockQueries
from dashboard.data_creator import _get_stock_snapshot_prefill_for_date


class TestFinanceQueries(FinanceDatabaseTestCase):
    def test_balance_and_spending(self):
        queries = FinanceQueries(str(self.db_path))

        balances = queries.get_balance_by_account(as_of_date="2026-07-02")
        self.assertEqual(len(balances), 1)
        account_name, balance, last_tx = balances[0]
        self.assertEqual(account_name, "Checking")
        self.assertAlmostEqual(float(balance), 3469.50, places=2)

        spending = queries.get_spending_by_category(start_date="2026-07-01", end_date="2026-07-02")
        self.assertEqual(len(spending), 1)
        category_name, tx_count, total_amount, avg_amount = spending[0]
        self.assertEqual(category_name, "Groceries")
        self.assertEqual(int(tx_count), 1)
        self.assertAlmostEqual(float(total_amount), -30.50, places=2)
        self.assertAlmostEqual(float(avg_amount), -30.50, places=2)

        queries.conn.close()

    def test_merge_accounts(self):
        queries = FinanceQueries(str(self.db_path))

        result = queries.merge_accounts("Checking", "Savings")
        self.assertEqual(result["source"], "Checking")
        self.assertEqual(result["target"], "Savings")
        self.assertEqual(result["rows_updated"], 2)

        account_names = [row[0] for row in queries.conn.execute("SELECT account_name FROM accounts ORDER BY account_name").fetchall()]
        self.assertIn("Savings", account_names)
        self.assertNotIn("Checking", account_names)

        transactions = queries.conn.execute("SELECT DISTINCT account_id FROM cash_transactions").fetchall()
        self.assertEqual(len(transactions), 1)

        queries.conn.close()

    def test_merge_categories(self):
        queries = FinanceQueries(str(self.db_path))

        result = queries.merge_categories("Groceries", "Food")
        self.assertEqual(result["source"], "Groceries")
        self.assertEqual(result["target"], "Food")
        self.assertEqual(result["rows_updated"], 1)

        category_names = [row[0] for row in queries.conn.execute("SELECT category_name FROM categories ORDER BY category_name").fetchall()]
        self.assertIn("Food", category_names)
        self.assertNotIn("Groceries", category_names)

        tx_category_ids = [row[0] for row in queries.conn.execute("SELECT DISTINCT category_id FROM cash_transactions").fetchall()]
        self.assertEqual(len(tx_category_ids), 2)

        queries.conn.close()

    def test_merge_transaction_dates(self):
        queries = FinanceQueries(str(self.db_path))

        result = queries.merge_transaction_dates("2026-07-01", "2026-07-02")
        self.assertEqual(result["source_date"], "2026-07-01")
        self.assertEqual(result["target_date"], "2026-07-02")
        self.assertEqual(result["rows_updated"], 1)

        dates = [row[0] for row in queries.conn.execute("SELECT DISTINCT transaction_date FROM cash_transactions").fetchall()]
        self.assertEqual(sorted(str(d) for d in dates), ["2026-07-02"])

        queries.conn.close()

    def test_goods_and_interest_helpers(self):
        queries = FinanceQueries(str(self.db_path))

        goods_history = queries.get_goods_value_history()
        self.assertEqual(len(goods_history), 2)
        self.assertEqual(goods_history[0][0], datetime.date(2026, 7, 2))
        self.assertAlmostEqual(float(goods_history[0][1]), 1400.00, places=2)
        self.assertEqual(goods_history[1][0], datetime.date(2026, 7, 3))
        self.assertAlmostEqual(float(goods_history[1][1]), 600.00, places=2)

        goods_item_history = queries.get_goods_value_history("Laptop")
        self.assertEqual(len(goods_item_history), 1)
        self.assertEqual(goods_item_history[0][0], datetime.date(2026, 7, 2))
        self.assertAlmostEqual(float(goods_item_history[0][1]), 1400.00, places=2)

        depreciation = queries.get_asset_depreciation()
        self.assertEqual(len(depreciation), 2)

        interest_history = queries.get_interest_balance_history()
        self.assertEqual(len(interest_history), 1)
        self.assertEqual(interest_history[0][0], datetime.date(2026, 7, 3))
        self.assertAlmostEqual(float(interest_history[0][1]), 2000.00, places=2)

        queries.conn.close()

    def test_all_pools_timeline_fills_missing_snapshots(self):
        queries = FinanceQueries(str(self.db_path))
        timeline = queries.get_all_pools_timeline(start_date='2026-07-01', end_date='2026-07-03')

        self.assertEqual(len(timeline), 3)
        self.assertEqual(timeline[0][0], datetime.date(2026, 7, 1))
        self.assertAlmostEqual(float(timeline[0][2]), 1000.00, places=2)
        self.assertAlmostEqual(float(timeline[0][3]), 0.00, places=2)
        self.assertAlmostEqual(float(timeline[0][4]), 0.00, places=2)

        self.assertEqual(timeline[1][0], datetime.date(2026, 7, 2))
        self.assertAlmostEqual(float(timeline[1][2]), 1000.00, places=2)
        self.assertAlmostEqual(float(timeline[1][3]), 1400.00, places=2)
        self.assertAlmostEqual(float(timeline[1][4]), 0.00, places=2)

        self.assertEqual(timeline[2][0], datetime.date(2026, 7, 3))
        self.assertAlmostEqual(float(timeline[2][2]), 1000.00, places=2)
        self.assertAlmostEqual(float(timeline[2][3]), 600.00, places=2)
        self.assertAlmostEqual(float(timeline[2][4]), 2000.00, places=2)

        queries.conn.close()


class TestStockQueryHelpers(FinanceDatabaseTestCase):
    def test_stock_snapshot_prefill_uses_previous_current_price(self):
        stock_conn = duckdb.connect(str(self.db_path))
        stock_queries = StockQueries(conn=stock_conn)

        stock_conn.execute(
            "INSERT INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) "
            "VALUES (2, 'test', '2026-07-15', 1, 'Sample Equity', 'SAMPLE', 10.0, 100.0, 100.0, 0.0, 0.0, 1000.00, 1000.00)"
        )
        stock_conn.execute(
            "INSERT INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) "
            "VALUES (3, 'test', '2026-08-01', 1, 'Sample Equity', 'SAMPLE', 10.0, 100.0, 110.0, 100.0, 10.0, 1100.00, 1100.00)"
        )
        stock_conn.commit()

        prefill = _get_stock_snapshot_prefill_for_date(stock_queries, '2026-08-05')
        self.assertEqual(len(prefill), 1)
        self.assertEqual(prefill.iloc[0]['Ticker'], 'SAMPLE')
        self.assertAlmostEqual(float(prefill.iloc[0]['Price Previous']), 110.0, places=2)

        stock_conn.close()


if __name__ == "__main__":
    unittest.main()
