from pathlib import Path
from datetime import date

import duckdb

from src.db_schema import init_database


def seed_sample_data(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("INSERT OR IGNORE INTO accounts (account_id, account_name, account_type, currency, is_active) VALUES (1, 'Checking Account', 'bank', 'EUR', TRUE)")
    conn.execute("INSERT OR IGNORE INTO accounts (account_id, account_name, account_type, currency, is_active) VALUES (2, 'Savings Account', 'bank', 'EUR', TRUE)")
    conn.execute("INSERT OR IGNORE INTO accounts (account_id, account_name, account_type, currency, is_active) VALUES (3, 'Brokerage Account', 'investment', 'EUR', TRUE)")

    conn.execute("INSERT OR IGNORE INTO main_categories (main_category_id, main_category_name) VALUES (1, 'Income')")
    conn.execute("INSERT OR IGNORE INTO main_categories (main_category_id, main_category_name) VALUES (2, 'Expenses')")
    conn.execute("INSERT OR IGNORE INTO main_categories (main_category_id, main_category_name) VALUES (3, 'Transfers')")

    conn.execute("INSERT OR IGNORE INTO sub_categories (sub_category_id, main_category_id, sub_category_name) VALUES (1, 1, 'Salary')")
    conn.execute("INSERT OR IGNORE INTO sub_categories (sub_category_id, main_category_id, sub_category_name) VALUES (2, 2, 'Groceries')")
    conn.execute("INSERT OR IGNORE INTO sub_categories (sub_category_id, main_category_id, sub_category_name) VALUES (3, 2, 'Utilities')")
    conn.execute("INSERT OR IGNORE INTO sub_categories (sub_category_id, main_category_id, sub_category_name) VALUES (4, 2, 'Entertainment')")
    conn.execute("INSERT OR IGNORE INTO sub_categories (sub_category_id, main_category_id, sub_category_name) VALUES (5, 3, 'Savings Transfer')")

    conn.execute("INSERT OR IGNORE INTO categories (category_id, main_category_id, sub_category_id, category_name, category_type, color_code) VALUES (1, 1, 1, 'Salary', 'income', '#2ecc71')")
    conn.execute("INSERT OR IGNORE INTO categories (category_id, main_category_id, sub_category_id, category_name, category_type, color_code) VALUES (2, 2, 2, 'Groceries', 'expense', '#e74c3c')")
    conn.execute("INSERT OR IGNORE INTO categories (category_id, main_category_id, sub_category_id, category_name, category_type, color_code) VALUES (3, 2, 3, 'Utilities', 'expense', '#f39c12')")
    conn.execute("INSERT OR IGNORE INTO categories (category_id, main_category_id, sub_category_id, category_name, category_type, color_code) VALUES (4, 2, 4, 'Entertainment', 'expense', '#9b59b6')")
    conn.execute("INSERT OR IGNORE INTO categories (category_id, main_category_id, sub_category_id, category_name, category_type, color_code) VALUES (5, 3, 5, 'Transfer to savings', 'transfer', '#34495e')")

    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (1, 1, 'Salary June', 1, 1, 3200.00, '2026-06-01', 3200.00, 'Sample Import', 'Income')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (2, 2, 'Groceries', 1, 2, -125.40, '2026-06-02', 3074.60, 'Sample Import', 'Expenses')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (3, 3, 'Electricity bill', 1, 3, -85.20, '2026-06-05', 2989.40, 'Sample Import', 'Expenses')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (4, 4, 'Streaming subscription', 1, 4, -15.99, '2026-06-10', 2973.41, 'Sample Import', 'Expenses')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (5, 5, 'Transfer to savings', 1, 5, -500.00, '2026-06-15', 2473.41, 'Sample Import', 'Transfer')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (6, 6, 'Salary July', 1, 1, 3200.00, '2026-07-01', 5673.41, 'Sample Import', 'Income')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (7, 7, 'Vacation', 1, 4, -420.00, '2026-07-05', 5253.41, 'Sample Import', 'Expenses')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (8, 8, 'Transfer to savings', 1, 5, -700.00, '2026-07-10', 4553.41, 'Sample Import', 'Transfer')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (9, 9, 'Dividend payout', 1, 1, 45.00, '2026-07-12', 4598.41, 'Sample Import', 'Income')")

    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (10, 1, 'Savings deposit', 2, 5, 500.00, '2026-06-15', 500.00, 'Sample Import', 'Transfer')")
    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (11, 2, 'Savings interest', 2, 1, 5.00, '2026-07-15', 505.00, 'Sample Import', 'Income')")

    conn.execute("INSERT OR IGNORE INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name) VALUES (12, 1, 'Brokerage deposit', 3, 5, 1200.00, '2026-07-10', 1200.00, 'Sample Import', 'Transfer')")

    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (1, 'Sample Import', '2026-04-15', 1, 'ACME Corp', 'ACME', 20.0, 115.00, 122.00, 140.00, 0.0609, 2440.00, 2440.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (2, 'Sample Import', '2026-04-15', 2, 'FutureTech', 'FTECH', 5.0, 320.00, 330.00, 50.00, 0.0313, 1650.00, 4090.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (3, 'Sample Import', '2026-04-15', 3, 'Green Energy', 'GREEN', 12.0, 70.00, 79.00, 108.00, 0.1286, 948.00, 5038.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (4, 'Sample Import', '2026-04-15', 4, 'SolarWind', 'SOLR', 8.0, 55.00, 60.00, 40.00, 0.0909, 480.00, 5518.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (5, 'Sample Import', '2026-04-15', 5, 'MedHealth', 'MEDH', 10.0, 95.00, 100.00, 50.00, 0.0526, 1000.00, 6518.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (6, 'Sample Import', '2026-04-15', 6, 'FinBank', 'FBNK', 15.0, 18.00, 19.00, 15.00, 0.0556, 285.00, 6803.00)")

    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (7, 'Sample Import', '2026-05-15', 1, 'ACME Corp', 'ACME', 20.0, 122.00, 128.00, 120.00, 0.0492, 2560.00, 2560.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (8, 'Sample Import', '2026-05-15', 2, 'FutureTech', 'FTECH', 5.0, 330.00, 345.00, 75.00, 0.0455, 1725.00, 4285.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (9, 'Sample Import', '2026-05-15', 3, 'Green Energy', 'GREEN', 12.0, 79.00, 87.00, 96.00, 0.1015, 1044.00, 5329.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (10, 'Sample Import', '2026-05-15', 4, 'SolarWind', 'SOLR', 8.0, 60.00, 66.00, 48.00, 0.0800, 528.00, 5857.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (11, 'Sample Import', '2026-05-15', 5, 'MedHealth', 'MEDH', 10.0, 100.00, 106.00, 60.00, 0.0600, 1060.00, 6917.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (12, 'Sample Import', '2026-05-15', 6, 'FinBank', 'FBNK', 15.0, 19.00, 20.00, 15.00, 0.0526, 300.00, 7217.00)")

    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (13, 'Sample Import', '2026-06-15', 1, 'ACME Corp', 'ACME', 20.0, 128.00, 134.00, 120.00, 0.0469, 2680.00, 2680.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (14, 'Sample Import', '2026-06-15', 2, 'FutureTech', 'FTECH', 5.0, 345.00, 355.00, 50.00, 0.0289, 1775.00, 4455.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (15, 'Sample Import', '2026-06-15', 3, 'Green Energy', 'GREEN', 12.0, 87.00, 92.00, 60.00, 0.0575, 1104.00, 5559.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (16, 'Sample Import', '2026-06-15', 4, 'SolarWind', 'SOLR', 8.0, 66.00, 64.00, -16.00, -0.0364, 512.00, 6071.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (17, 'Sample Import', '2026-06-15', 5, 'MedHealth', 'MEDH', 10.0, 106.00, 108.00, 20.00, 0.0189, 1080.00, 7151.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (18, 'Sample Import', '2026-06-15', 6, 'FinBank', 'FBNK', 15.0, 20.00, 20.00, 0.00, 0.0000, 300.00, 7451.00)")

    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (19, 'Sample Import', '2026-07-15', 1, 'ACME Corp', 'ACME', 20.0, 134.00, 132.00, -40.00, -0.0150, 2640.00, 2640.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (20, 'Sample Import', '2026-07-15', 2, 'FutureTech', 'FTECH', 5.0, 355.00, 360.00, 25.00, 0.0141, 1800.00, 4440.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (21, 'Sample Import', '2026-07-15', 3, 'Green Energy', 'GREEN', 12.0, 92.00, 95.00, 36.00, 0.0348, 1140.00, 5580.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (22, 'Sample Import', '2026-07-15', 4, 'SolarWind', 'SOLR', 8.0, 64.00, 67.00, 24.00, 0.0471, 536.00, 6116.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (23, 'Sample Import', '2026-07-15', 5, 'MedHealth', 'MEDH', 10.0, 108.00, 112.00, 40.00, 0.0377, 1120.00, 7236.00)")
    conn.execute("INSERT OR IGNORE INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (24, 'Sample Import', '2026-07-15', 6, 'FinBank', 'FBNK', 15.0, 20.00, 21.00, 15.00, 0.0500, 315.00, 7551.00)")

    conn.execute("INSERT OR IGNORE INTO goods_valuations (valuation_id, source_sheet, valuation_date, row_nr, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value) VALUES (1, 'Sample Import', '2026-07-15', 1, 'Laptop', 1500.00, 0.10, 1350.00, -100.00, 1250.00)")
    conn.execute("INSERT OR IGNORE INTO goods_valuations (valuation_id, source_sheet, valuation_date, row_nr, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value) VALUES (2, 'Sample Import', '2026-07-15', 2, 'Bicycle', 800.00, 0.05, 760.00, -20.00, 740.00)")
    conn.execute("INSERT OR IGNORE INTO goods_valuations (valuation_id, source_sheet, valuation_date, row_nr, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value) VALUES (3, 'Sample Import', '2026-07-15', 3, 'Camera', 1200.00, 0.08, 1200.00, -96.00, 1104.00)")

    conn.execute("INSERT OR IGNORE INTO interest_balance_changes (change_id, source_sheet, balance_date, account_name, balance, previous_balance, delta) VALUES (1, 'Sample Import', '2026-07-15', 'Festgeld', 2050.00, 2000.00, 50.00)")
    conn.execute("INSERT OR IGNORE INTO interest_balance_changes (change_id, source_sheet, balance_date, account_name, balance, previous_balance, delta) VALUES (2, 'Sample Import', '2026-06-30', 'Savings Interest', 505.00, 500.00, 5.00)")

    conn.execute("INSERT OR IGNORE INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) VALUES (1, 'Sample Import', '2026-07-15', 1, 4598.41, 5253.41, -655.00, 'calculated')")
    conn.execute("INSERT OR IGNORE INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) VALUES (2, 'Sample Import', '2026-07-15', 2, 505.00, 500.00, 5.00, 'snapshot')")
    conn.execute("INSERT OR IGNORE INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) VALUES (3, 'Sample Import', '2026-07-15', 3, 1200.00, 0.00, 1200.00, 'snapshot')")

    conn.commit()


def main() -> None:
    db_path = Path(__file__).resolve().parent / "finance_sample.duckdb"
    init_database(str(db_path))
    conn = duckdb.connect(str(db_path))
    seed_sample_data(conn)
    conn.close()
    print(f"Sample database created at {db_path}")


if __name__ == "__main__":
    main()
