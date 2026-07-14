"""
Account balance pool queries for the Finance database.
"""
import calendar
from datetime import datetime, timedelta
from pathlib import Path

try:
    from .db_schema import get_connection
except ImportError:
    from db_schema import get_connection


def default_db_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "finance.duckdb")


class AccountBalanceQueries:
    def __init__(self, conn=None, db_path=None):
        if conn is None:
            if db_path is None:
                db_path = default_db_path()
            self.conn = get_connection(str(db_path))
        else:
            self.conn = conn

    def save_account_balances(self, records):
        if not records:
            return 0

        saved = 0
        for record in records:
            if record.get("_action") == "delete":
                balance_id = int(record["original_key"])
                self.conn.execute(
                    "DELETE FROM account_balances WHERE balance_id = ?",
                    [balance_id],
                )
                saved += 1
                continue

            original_key = record.get("original_key")
            if original_key:
                self.conn.execute(
                    "DELETE FROM account_balances WHERE balance_id = ?",
                    [int(original_key)],
                )

            balance_id = int(record.get("Balance ID")) if record.get("Balance ID") not in (None, "") else self._next_id("account_balances", "balance_id")
            balance_date = record.get("Balance Date")
            account_name = record.get("Account Name") or "Unknown"
            account_id = self._get_or_create_account_id(account_name)
            balance = float(record.get("Balance") or 0)
            previous_balance = float(record.get("Previous Balance") or 0)
            delta = float(record.get("Delta") or 0)
            entry_type = record.get("Entry Type") or "monitoring"
            source_sheet = record.get("Source Sheet") or "manual"

            self.conn.execute(
                "INSERT INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    balance_id,
                    source_sheet,
                    balance_date,
                    account_id,
                    balance,
                    previous_balance,
                    delta,
                    entry_type,
                ],
            )
            saved += 1

        self.conn.commit()
        return saved

    def get_account_balance_names(self):
        result = self.conn.execute(
            "SELECT DISTINCT a.account_name FROM account_balances b JOIN accounts a ON b.account_id = a.account_id ORDER BY a.account_name"
        ).fetchall()
        return [row[0] for row in result]

    def get_account_balance_entries_by_account_name(self, account_name):
        sql = """
            SELECT
                b.balance_id,
                b.balance_date,
                a.account_name AS account_name,
                b.balance,
                b.previous_balance,
                b.delta,
                b.entry_type,
                b.source_sheet
            FROM account_balances b
            JOIN accounts a ON b.account_id = a.account_id
            WHERE a.account_name = ?
            ORDER BY b.balance_date DESC, b.balance_id
        """
        return self.conn.execute(sql, [account_name]).fetchall()

    def get_account_balance_entries_by_balance_date(self, balance_date):
        sql = """
            SELECT
                b.balance_id,
                b.balance_date,
                a.account_name AS account_name,
                b.balance,
                b.previous_balance,
                b.delta,
                b.entry_type,
                b.source_sheet
            FROM account_balances b
            JOIN accounts a ON b.account_id = a.account_id
            WHERE b.balance_date = ?
            ORDER BY a.account_name, b.balance_id
        """
        return self.conn.execute(sql, [balance_date]).fetchall()

    def get_account_balance_entries(self, start_date=None, end_date=None):
        sql = """
            SELECT
                b.balance_id,
                b.balance_date,
                a.account_name AS account_name,
                b.balance,
                b.previous_balance,
                b.delta,
                b.entry_type,
                b.source_sheet
            FROM account_balances b
            JOIN accounts a ON b.account_id = a.account_id
        """
        params = []
        if start_date is not None and end_date is not None:
            sql += " WHERE balance_date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date is not None:
            sql += " WHERE balance_date >= ?"
            params = [start_date]
        elif end_date is not None:
            sql += " WHERE balance_date <= ?"
            params = [end_date]

        sql += " ORDER BY b.balance_date DESC, b.balance_id"
        return self.conn.execute(sql, params).fetchall()

    def has_calculated_balances(self):
        result = self.conn.execute(
            "SELECT COUNT(*) FROM account_balances WHERE entry_type = 'calculated'"
        ).fetchone()[0]
        return bool(result)

    def get_orphaned_account_balance_account_ids(self):
        result = self.conn.execute(
            """
            SELECT DISTINCT b.account_id
            FROM account_balances b
            LEFT JOIN accounts a ON b.account_id = a.account_id
            WHERE a.account_id IS NULL
            """,
        )
        rows = result.fetchall()
        result.close()
        return [row[0] for row in rows]

    def get_latest_account_balances(self, entry_type=None, as_of_date=None):
        params = []
        sql = """
            SELECT
                a.account_name AS account_name,
                b.balance,
                b.previous_balance,
                b.delta,
                b.entry_type,
                b.source_sheet
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY balance_date DESC, balance_id DESC) AS rn
                FROM account_balances
        """

        if entry_type and as_of_date is not None:
            sql += " WHERE entry_type = ? AND balance_date <= ?"
            params = [entry_type, as_of_date]
        elif entry_type:
            sql += " WHERE entry_type = ?"
            params = [entry_type]
        elif as_of_date is not None:
            sql += " WHERE balance_date <= ?"
            params = [as_of_date]

        sql += " ) b JOIN accounts a ON b.account_id = a.account_id WHERE b.rn = 1 ORDER BY b.balance DESC"
        result = self.conn.execute(sql, params)
        rows = result.fetchall()
        result.close()
        return rows

    def get_account_balance_history(self, account_name=None, entry_type=None):
        params = []
        if account_name:
            sql = """
                SELECT b.balance_date, b.balance, b.delta
                FROM account_balances b
                JOIN accounts a ON b.account_id = a.account_id
                WHERE a.account_name = ?
            """
            params.append(account_name)
            if entry_type:
                sql += " AND b.entry_type = ?"
                params.append(entry_type)
            sql += " ORDER BY b.balance_date"
        else:
            sql = """
                SELECT balance_date, SUM(balance) as total_balance, SUM(delta) as total_delta
                FROM account_balances
            """
            if entry_type:
                sql += " WHERE entry_type = ?"
                params.append(entry_type)
            sql += " GROUP BY balance_date ORDER BY balance_date"

        return self.conn.execute(sql, params).fetchall()

    def _get_exact_balance_row(self, account_id, balance_date, entry_type=None):
        if account_id is None:
            return None

        params = [account_id, balance_date]
        sql = """
            SELECT balance_date, balance, previous_balance, delta, entry_type, source_sheet
            FROM account_balances
            WHERE account_id = ? AND balance_date = ?
        """

        if entry_type:
            sql += " AND entry_type = ?"
            params.append(entry_type)

        sql += " ORDER BY balance_id DESC LIMIT 1"
        return self.conn.execute(sql, params).fetchone()

    def _get_nearest_balance_snapshot(self, account_id, balance_date):
        if account_id is None:
            return None, None

        previous_row = self.conn.execute(
            "SELECT balance_date, balance FROM account_balances WHERE account_id = ? AND balance_date < ? ORDER BY balance_date DESC LIMIT 1",
            [account_id, balance_date],
        ).fetchone()
        next_row = self.conn.execute(
            "SELECT balance_date, balance FROM account_balances WHERE account_id = ? AND balance_date > ? ORDER BY balance_date ASC LIMIT 1",
            [account_id, balance_date],
        ).fetchone()

        previous = (previous_row[0], float(previous_row[1])) if previous_row else (None, None)
        nxt = (next_row[0], float(next_row[1])) if next_row else (None, None)
        return previous, nxt

    def _sum_transaction_delta(self, account_id, start_date, end_date, include_start=True):
        if account_id is None:
            return 0.0

        comparator = ">=" if include_start else ">"
        result = self.conn.execute(
            f"""
                SELECT COALESCE(SUM(t.amount), 0)
                FROM cash_transactions t
                WHERE t.account_id = ?
                  AND t.transaction_date {comparator} ?
                  AND t.transaction_date <= ?
            """,
            [account_id, start_date, end_date],
        ).fetchone()[0]
        return float(result or 0.0)

    def get_account_balance_at_date(self, account_name, balance_date, entry_type_priority=("calculated", "monitoring")):
        account_id = self._get_account_id(account_name)
        if account_id is None:
            return {
                "balance_date": balance_date,
                "account_name": account_name,
                "balance": 0.0,
                "previous_balance": 0.0,
                "delta": 0.0,
                "entry_type": None,
                "source_sheet": None,
                "calculated": False,
            }

        for entry_type in entry_type_priority:
            existing_row = self._get_exact_balance_row(account_id, balance_date, entry_type=entry_type)
            if existing_row:
                balance_date_value, balance, previous_balance, delta, entry_type_value, source_sheet = existing_row
                return {
                    "balance_date": balance_date_value,
                    "account_name": account_name,
                    "balance": float(balance),
                    "previous_balance": float(previous_balance),
                    "delta": float(delta),
                    "entry_type": entry_type_value,
                    "source_sheet": source_sheet,
                    "calculated": entry_type_value == "calculated",
                }

        calculated_row = self.preview_calculated_account_balance(account_name, balance_date)
        calculated_row["calculated"] = True
        return calculated_row

    def preview_calculated_account_balance(self, account_name, balance_date, entry_type="calculated"):
        account_id = self._get_account_id(account_name)
        if account_id is None:
            return {
                "balance_date": balance_date,
                "account_name": account_name,
                "balance": 0.0,
                "previous_balance": 0.0,
                "delta": 0.0,
                "entry_type": entry_type,
                "source_sheet": "calculated",
                "calculated": True,
            }

        exact_row = self._get_exact_balance_row(account_id, balance_date)
        if exact_row:
            balance_date_value, balance, previous_balance, delta, entry_type_value, source_sheet = exact_row
            return {
                "balance_date": balance_date_value,
                "account_name": account_name,
                "balance": float(balance),
                "previous_balance": float(previous_balance),
                "delta": float(delta),
                "entry_type": entry_type_value,
                "source_sheet": source_sheet,
                "calculated": entry_type_value == "calculated",
            }

        previous_snapshot, next_snapshot = self._get_nearest_balance_snapshot(account_id, balance_date)
        if previous_snapshot[0] is not None:
            previous_date, previous_balance = previous_snapshot
            delta = self._sum_transaction_delta(account_id, previous_date, balance_date, include_start=False)
            balance = previous_balance + delta
            return {
                "balance_date": balance_date,
                "account_name": account_name,
                "balance": float(balance),
                "previous_balance": float(previous_balance),
                "delta": float(delta),
                "entry_type": entry_type,
                "source_sheet": "calculated",
                "calculated": True,
            }

        if next_snapshot[0] is not None:
            next_date, next_balance = next_snapshot
            future_delta = self._sum_transaction_delta(account_id, balance_date, next_date, include_start=False)
            balance = next_balance - future_delta
            return {
                "balance_date": balance_date,
                "account_name": account_name,
                "balance": float(balance),
                "previous_balance": 0.0,
                "delta": float(balance),
                "entry_type": entry_type,
                "source_sheet": "calculated",
                "calculated": True,
            }

        cash_row = self.conn.execute(
            "SELECT MAX(balance_after), COUNT(*) FROM cash_transactions WHERE account_id = ? AND transaction_date = ?",
            [account_id, balance_date],
        ).fetchone()
        if cash_row and cash_row[1]:
            balance = float(cash_row[0] or 0.0)
            return {
                "balance_date": balance_date,
                "account_name": account_name,
                "balance": balance,
                "previous_balance": 0.0,
                "delta": balance,
                "entry_type": entry_type,
                "source_sheet": "calculated",
                "calculated": True,
            }

        return {
            "balance_date": balance_date,
            "account_name": account_name,
            "balance": 0.0,
            "previous_balance": 0.0,
            "delta": 0.0,
            "entry_type": entry_type,
            "source_sheet": "calculated",
            "calculated": True,
        }

    def preview_calculated_account_balances(self, account_name, start_date, end_date, entry_type="calculated"):
        if start_date is None or end_date is None:
            raise ValueError("Start date and end date are required.")
        if end_date < start_date:
            raise ValueError("End date must be on or after the start date.")

        preview_rows = []
        account_id = self._get_account_id(account_name)
        if account_id is None:
            preview_dates = []
        else:
            preview_dates = self._get_account_transaction_dates(account_id, start_date, end_date)

        if not preview_dates:
            last_day = calendar.monthrange(start_date.year, start_date.month)[1]
            fallback_date = datetime(start_date.year, start_date.month, last_day).date()
            if fallback_date > end_date:
                fallback_date = end_date
            preview_dates = [fallback_date]

        preview_rows = []
        for preview_date in preview_dates:
            preview = self.preview_calculated_account_balance(account_name, preview_date, entry_type=entry_type)
            preview["source_sheet"] = "Data Organizer"
            preview["entry_type"] = entry_type
            preview["calculated"] = True
            preview_rows.append(preview)

        return preview_rows

    def _get_account_transaction_dates(self, account_id, start_date, end_date):
        result = self.conn.execute(
            """
                SELECT DISTINCT transaction_date
                FROM cash_transactions
                WHERE account_id = ?
                  AND transaction_date BETWEEN ? AND ?
                ORDER BY transaction_date
            """,
            [account_id, start_date, end_date],
        ).fetchall()
        return [row[0] for row in result]

    def create_calculated_account_balances(self, account_name, start_date, end_date, entry_type="calculated"):
        preview_rows = self.preview_calculated_account_balances(account_name, start_date, end_date, entry_type=entry_type)
        inserted = 0
        account_id = self._get_or_create_account_id(account_name)

        for row in preview_rows:
            self.conn.execute(
                "DELETE FROM account_balances WHERE account_id = ? AND balance_date = ? AND entry_type = ?",
                [account_id, row["balance_date"], entry_type],
            )
            balance_id = self._next_id("account_balances", "balance_id")
            self.conn.execute(
                "INSERT INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    balance_id,
                    "Data Organizer",
                    row["balance_date"],
                    account_id,
                    row["balance"],
                    row["previous_balance"],
                    row["delta"],
                    entry_type,
                ],
            )
            inserted += 1

        self.conn.commit()
        return {
            "account_name": account_name,
            "start_date": start_date,
            "end_date": end_date,
            "rows_created": inserted,
        }

    def create_calculated_account_balance(self, account_name, balance_date, entry_type="calculated"):
        result = self.preview_calculated_account_balance(account_name, balance_date, entry_type=entry_type)
        account_id = self._get_or_create_account_id(account_name)

        self.conn.execute(
            "DELETE FROM account_balances WHERE account_id = ? AND balance_date = ? AND entry_type = ?",
            [account_id, balance_date, entry_type],
        )

        balance_id = self._next_id("account_balances", "balance_id")
        self.conn.execute(
            "INSERT INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                balance_id,
                "Data Organizer",
                balance_date,
                account_id,
                result["balance"],
                result["previous_balance"],
                result["delta"],
                entry_type,
            ],
        )
        self.conn.commit()

        result["balance_id"] = balance_id
        result["entry_type"] = entry_type
        result["source_sheet"] = result.get("source_sheet", "calculated")
        return result

    def get_latest_account_balances_by_account(self, entry_type=None):
        params = []
        if entry_type:
            sql = """
                SELECT a.account_name AS account_name, b.balance, b.previous_balance, b.delta, b.entry_type, b.source_sheet
                FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY balance_date DESC, balance_id DESC) AS rn
                    FROM account_balances
                    WHERE entry_type = ?
                ) b
                JOIN accounts a ON b.account_id = a.account_id
                WHERE b.rn = 1
                ORDER BY b.balance DESC
            """
            params = [entry_type]
        else:
            sql = """
                SELECT a.account_name AS account_name, b.balance, b.previous_balance, b.delta, b.entry_type, b.source_sheet
                FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY balance_date DESC, balance_id DESC) AS rn
                    FROM account_balances
                ) b
                JOIN accounts a ON b.account_id = a.account_id
                WHERE b.rn = 1
                ORDER BY b.balance DESC
            """

        return self.conn.execute(sql, params).fetchall()

    def merge_account_balance_names(self, source_account_name, target_account_name, selected_balance_ids=None):
        if not source_account_name or not target_account_name:
            raise ValueError("Both source and target account names must be provided.")
        if source_account_name == target_account_name:
            raise ValueError("Source and target account names must differ.")

        source_account_id = self._get_account_id(source_account_name)
        if source_account_id is None:
            raise ValueError(f"Source account not found: {source_account_name}")
        target_account_id = self._get_or_create_account_id(target_account_name)

        if selected_balance_ids is not None:
            if not selected_balance_ids:
                return {
                    "source": source_account_name,
                    "target": target_account_name,
                    "rows_updated": 0,
                }

            placeholders = ",".join("?" for _ in selected_balance_ids)
            sql = f"UPDATE account_balances SET account_id = ? WHERE account_id = ? AND balance_id IN ({placeholders})"
            params = [target_account_id, source_account_id] + selected_balance_ids
            self.conn.execute(sql, params)
            rows_updated = self.conn.execute("SELECT COUNT(*) FROM account_balances WHERE account_id = ? AND balance_id IN (%s)" % placeholders, [target_account_id] + selected_balance_ids).fetchone()[0]
        else:
            sql = "UPDATE account_balances SET account_id = ? WHERE account_id = ?"
            self.conn.execute(sql, [target_account_id, source_account_id])
            rows_updated = self.conn.execute(
                "SELECT COUNT(*) FROM account_balances WHERE account_id = ?",
                [target_account_id],
            ).fetchone()[0]

        self.conn.commit()

        return {
            "source": source_account_name,
            "target": target_account_name,
            "rows_updated": int(rows_updated),
        }

    def merge_account_balance_dates(self, source_date, target_date):
        if source_date == target_date:
            raise ValueError("Source and target dates must differ.")

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM account_balances WHERE balance_date = ?",
            [source_date],
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE account_balances SET balance_date = ? WHERE balance_date = ?",
            [target_date, source_date],
        )
        self.conn.commit()
        return {
            "source_date": source_date,
            "target_date": target_date,
            "rows_updated": int(row_count),
        }

    def _get_account_id(self, account_name):
        row = self.conn.execute(
            "SELECT account_id FROM accounts WHERE account_name = ?",
            [account_name],
        ).fetchone()
        return row[0] if row else None

    def _get_or_create_account_id(self, account_name):
        if not account_name:
            account_name = "Unknown"
        row = self.conn.execute(
            "SELECT account_id FROM accounts WHERE account_name = ?",
            [account_name],
        ).fetchone()
        if row:
            return row[0]

        account_id = self._next_id("accounts", "account_id")
        self.conn.execute(
            "INSERT INTO accounts (account_id, account_name, account_type, currency, is_active) VALUES (?, ?, 'bank', 'EUR', TRUE)",
            [account_id, account_name],
        )
        return account_id

    def _next_id(self, table_name, id_column):
        row = self.conn.execute(
            f"SELECT COALESCE(MAX({id_column}), 0) + 1 FROM {table_name}"
        ).fetchone()
        return int(row[0] or 1)
