"""
Database Utilities and Query Helpers for Finance Database
Pool-aware wrapper around cash, stock, goods, and interest query helpers.
"""

from datetime import datetime, timedelta
from pathlib import Path

try:
    from .cash_queries import CashQueries
    from .goods_queries import GoodsQueries
    from .interest_queries import InterestQueries
    from .stock_queries import StockQueries
    from .account_balance_queries import AccountBalanceQueries
    from .db_schema import get_connection
except ImportError:
    from cash_queries import CashQueries
    from goods_queries import GoodsQueries
    from interest_queries import InterestQueries
    from stock_queries import StockQueries
    from account_balance_queries import AccountBalanceQueries
    from db_schema import get_connection


def default_db_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "finance.duckdb")


class FinanceQueries:
    """Common query wrapper that delegates to pool-specific query helpers."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = default_db_path()

        self.cash = CashQueries(db_path=db_path)
        self.stock = StockQueries(conn=self.cash.conn)
        self.goods = GoodsQueries(conn=self.cash.conn)
        self.interest = InterestQueries(conn=self.cash.conn)
        self.account_balance = AccountBalanceQueries(conn=self.cash.conn)
        self.conn = self.cash.conn

    def __getattr__(self, name):
        for pool in (self.cash, self.stock, self.goods, self.interest, self.account_balance):
            if hasattr(pool, name):
                return getattr(pool, name)
        raise AttributeError(f"{self.__class__.__name__!r} object has no attribute {name!r}")

    def get_account_balances(self, as_of_date=None):
        """Return account balances using snapshots if available and cash-derived values otherwise."""
        if as_of_date is None:
            as_of_date = datetime.now().date()

        balances = []
        for account_name in self.cash.get_active_account_names():
            snapshot = self.account_balance.get_account_balance_at_date(account_name, as_of_date)
            balances.append((snapshot["account_name"], snapshot["balance"], snapshot.get("source_sheet")))
        return balances

    def get_account_balances_with_flags(self, as_of_date=None):
        """Return latest account balances and whether each row is based on calculated data."""
        if as_of_date is None:
            as_of_date = datetime.now().date()

        result = []
        for account_name in self.cash.get_active_account_names():
            snapshot = self.account_balance.get_account_balance_at_date(account_name, as_of_date)
            result.append(
                (
                    snapshot["account_name"],
                    snapshot["balance"],
                    snapshot.get("source_sheet"),
                    snapshot.get("calculated", False),
                )
            )
        return result

    def get_account_balance_snapshot(self, account_name, balance_date):
        return self.account_balance.get_account_balance_at_date(account_name, balance_date)

    def preview_account_balance_snapshots(self, account_name, start_date, end_date):
        return self.account_balance.preview_calculated_account_balances(account_name, start_date, end_date)

    def create_account_balance_snapshots(self, account_name, start_date, end_date):
        return self.account_balance.create_calculated_account_balances(account_name, start_date, end_date)

    def has_calculated_account_balances(self):
        return self.account_balance.has_calculated_balances()

    def has_account_balances_with_missing_accounts(self):
        return bool(self.account_balance.get_orphaned_account_balance_account_ids())

    def needs_calculated_account_balance_snapshots(self):
        active_accounts = self.cash.get_active_account_names()
        if not active_accounts:
            return False

        calculated_accounts = {
            row[0]
            for row in self.account_balance.get_latest_account_balances(entry_type='calculated')
        }
        return len(calculated_accounts) != len(active_accounts)

    def get_all_pools_timeline(self, start_date=None, end_date=None):
        """Get timeline totals across cash, stocks, goods, and interest pools."""
        if start_date is None:
            start_date = datetime.now().date() - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now().date()

        date_rows = self.conn.execute(
            """
            SELECT DISTINCT dt
            FROM (
                SELECT transaction_date AS dt FROM cash_transactions WHERE transaction_date BETWEEN ? AND ?
                UNION ALL
                SELECT balance_date AS dt FROM account_balances WHERE balance_date BETWEEN ? AND ?
                UNION ALL
                SELECT snapshot_date AS dt FROM stock_positions WHERE snapshot_date BETWEEN ? AND ?
                UNION ALL
                SELECT valuation_date AS dt FROM goods_valuations WHERE valuation_date BETWEEN ? AND ?
                UNION ALL
                SELECT balance_date AS dt FROM interest_balance_changes WHERE balance_date BETWEEN ? AND ?
            )
            ORDER BY dt
            """,
            [start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date],
        ).fetchall()
        dates = [row[0] for row in date_rows]

        cash_balances = {}
        active_accounts = self.cash.get_active_account_names()
        for date in dates:
            cash_balances[date] = sum(
                self.account_balance.get_account_balance_at_date(account_name, date)["balance"]
                for account_name in active_accounts
            )

        stocks = {
            row[0]: row[1]
            for row in self.conn.execute(
                """
                SELECT snapshot_date AS date, SUM(position_value) AS stock_balance
                FROM stock_positions
                WHERE snapshot_date BETWEEN ? AND ?
                GROUP BY snapshot_date
                """,
                [start_date, end_date],
            ).fetchall()
        }
        goods = {
            row[0]: row[1]
            for row in self.conn.execute(
                """
                SELECT valuation_date AS date, SUM(current_value) AS goods_balance
                FROM goods_valuations
                WHERE valuation_date BETWEEN ? AND ?
                GROUP BY valuation_date
                """,
                [start_date, end_date],
            ).fetchall()
        }
        interest = {
            row[0]: row[1]
            for row in self.conn.execute(
                """
                SELECT balance_date AS date, SUM(balance) AS interest_balance
                FROM interest_balance_changes
                WHERE balance_date BETWEEN ? AND ?
                GROUP BY balance_date
                """,
                [start_date, end_date],
            ).fetchall()
        }

        last_stock = 0.0
        last_goods = 0.0
        last_interest = 0.0
        result = []
        for date in dates:
            if date in stocks:
                last_stock = stocks[date]
            if date in goods:
                last_goods = goods[date]
            if date in interest:
                last_interest = interest[date]

            result.append(
                (
                    date,
                    cash_balances.get(date, 0.0),
                    last_stock,
                    last_goods,
                    last_interest,
                )
            )

        return result

    def get_database_date_range(self):
        """Return the earliest and latest date found across all date-based tables."""
        result = self.conn.execute("""
            SELECT MIN(dt) AS min_date, MAX(dt) AS max_date
            FROM (
                SELECT transaction_date AS dt FROM cash_transactions
                UNION ALL
                SELECT snapshot_date FROM stock_positions
                UNION ALL
                SELECT valuation_date FROM goods_valuations
                UNION ALL
                SELECT balance_date FROM interest_balance_changes
                UNION ALL
                SELECT balance_date FROM account_balances
            )
        """).fetchone()

        if not result or result[0] is None or result[1] is None:
            return None, None
        return result[0], result[1]


class GoodsValuationHelper:
    """Read-only helper for goods valuations imported directly from the sheet."""

    def __init__(self, db_path: str = "finance.duckdb"):
        self.conn = get_connection(db_path)

    def get_latest_valuations(self):
        latest_sheet = self.conn.execute(
            "SELECT source_sheet FROM goods_valuations ORDER BY valuation_date DESC LIMIT 1"
        ).fetchone()
        if not latest_sheet:
            return {"valuations": [], "total_value": 0}

        rows = self.conn.execute(
            """
            SELECT item_name, purchase_value, current_value, value_change
            FROM goods_valuations
            WHERE source_sheet = ?
            ORDER BY current_value DESC
            """,
            [latest_sheet[0]],
        ).fetchall()

        valuations = [
            {
                "item_name": item_name,
                "purchase_value": purchase_value,
                "current_value": current_value,
                "value_change": value_change,
            }
            for item_name, purchase_value, current_value, value_change in rows
        ]
        total_value = sum(v["current_value"] or 0 for v in valuations)

        return {"valuations": valuations, "total_value": total_value}


def print_balance_summary():
    """Print account balance summary."""
    queries = FinanceQueries()
    balances = queries.get_balance_by_account()

    print("\n" + "=" * 60)
    print("ACCOUNT BALANCE SUMMARY")
    print("=" * 60)

    total = 0
    for account, balance, last_tx in balances:
        if balance:
            print(f"  {account:<30} €{balance:>12,.2f}  (Last: {last_tx})")
            total += balance

    print("-" * 60)
    print(f"  {'TOTAL':<30} €{total:>12,.2f}")


def print_category_summary(days=30):
    """Print category spending summary."""
    queries = FinanceQueries()
    categories = queries.get_spending_by_category(
        start_date=datetime.now().date() - timedelta(days=days)
    )

    print("\n" + "=" * 60)
    print(f"SPENDING SUMMARY (Last {days} days)")
    print("=" * 60)

    total = 0
    for cat, count, amount, avg in categories:
        print(f"  {cat:<30} €{amount:>10,.2f}  ({count} tx, avg: €{avg:>8,.2f})")
        total += amount

    print("-" * 60)
    print(f"  {'TOTAL':<30} €{total:>10,.2f}")


if __name__ == "__main__":
    print_balance_summary()
    print_category_summary(30)
