"""
Interest pool queries for the Finance database.
"""
from pathlib import Path

try:
    from .db_schema import get_connection
except ImportError:
    from db_schema import get_connection


def default_db_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "finance.duckdb")


class InterestQueries:
    def __init__(self, conn=None, db_path=None):
        if conn is None:
            if db_path is None:
                db_path = default_db_path()
            self.conn = get_connection(str(db_path))
        else:
            self.conn = conn

    def save_interest_balance_changes(self, records):
        if not records:
            return 0

        saved = 0
        for record in records:
            if record.get("_action") == "delete":
                change_id = int(record["original_key"])
                self.conn.execute(
                    "DELETE FROM interest_balance_changes WHERE change_id = ?",
                    [change_id],
                )
                saved += 1
                continue

            original_key = record.get("original_key")
            if original_key:
                self.conn.execute(
                    "DELETE FROM interest_balance_changes WHERE change_id = ?",
                    [int(original_key)],
                )

            change_id = int(record.get("Change ID")) if record.get("Change ID") not in (None, "") else self._next_id("interest_balance_changes", "change_id")
            balance_date = record.get("Balance Date")
            account_name = record.get("Account Name") or ""
            balance = float(record.get("Balance") or 0)
            previous_balance = float(record.get("Previous Balance") or 0)
            delta = float(record.get("Delta") or 0)
            source_sheet = record.get("Source Sheet") or "manual"

            self.conn.execute(
                "INSERT INTO interest_balance_changes (change_id, source_sheet, balance_date, account_name, balance, previous_balance, delta) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    change_id,
                    source_sheet,
                    balance_date,
                    account_name,
                    balance,
                    previous_balance,
                    delta,
                ],
            )
            saved += 1

        self.conn.commit()
        return saved

    def get_interest_account_names(self):
        result = self.conn.execute(
            "SELECT DISTINCT account_name FROM interest_balance_changes ORDER BY account_name"
        ).fetchall()
        return [row[0] for row in result]

    def get_interest_balance_changes_by_account_name(self, account_name):
        sql = """
            SELECT
                change_id,
                balance_date,
                account_name,
                balance,
                previous_balance,
                delta,
                source_sheet
            FROM interest_balance_changes
            WHERE account_name = ?
            ORDER BY balance_date DESC, change_id
        """
        return self.conn.execute(sql, [account_name]).fetchall()

    def get_interest_balance_changes_by_balance_date(self, balance_date):
        sql = """
            SELECT
                change_id,
                balance_date,
                account_name,
                balance,
                previous_balance,
                delta,
                source_sheet
            FROM interest_balance_changes
            WHERE balance_date = ?
            ORDER BY account_name, change_id
        """
        return self.conn.execute(sql, [balance_date]).fetchall()

    def get_interest_balance_changes(self, start_date=None, end_date=None):
        sql = """
            SELECT
                change_id,
                balance_date,
                account_name,
                balance,
                previous_balance,
                delta,
                source_sheet
            FROM interest_balance_changes
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

        sql += " ORDER BY balance_date DESC, change_id"
        return self.conn.execute(sql, params).fetchall()

    def merge_interest_account_names(self, source_name, target_name, selected_change_ids=None):
        if source_name == target_name:
            raise ValueError("Source and target must differ.")

        if selected_change_ids is not None:
            if not selected_change_ids:
                return {"source": source_name, "target": target_name, "rows_updated": 0}

            unique_ids = list(dict.fromkeys(selected_change_ids))
            row_count = 0
            for change_id in unique_ids:
                if change_id is None or change_id == "":
                    continue
                row_count += self.conn.execute(
                    "UPDATE interest_balance_changes SET account_name = ? WHERE change_id = ? AND account_name = ?",
                    [target_name, int(float(change_id)), source_name],
                ).rowcount
            self.conn.commit()
            return {"source": source_name, "target": target_name, "rows_updated": int(row_count)}

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM interest_balance_changes WHERE account_name = ?",
            [source_name],
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE interest_balance_changes SET account_name = ? WHERE account_name = ?",
            [target_name, source_name],
        )
        self.conn.commit()
        return {
            "source": source_name,
            "target": target_name,
            "rows_updated": int(row_count),
        }

    def merge_interest_balance_dates(self, source_date, target_date):
        if source_date == target_date:
            raise ValueError("Source and target dates must differ.")

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM interest_balance_changes WHERE balance_date = ?",
            [source_date],
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE interest_balance_changes SET balance_date = ? WHERE balance_date = ?",
            [target_date, source_date],
        )
        self.conn.commit()
        return {
            "source_date": source_date,
            "target_date": target_date,
            "rows_updated": int(row_count),
        }

    def get_latest_interest_balances(self):
        latest_sheet = self.conn.execute(
            "SELECT source_sheet FROM interest_balance_changes ORDER BY balance_date DESC LIMIT 1"
        ).fetchone()
        if not latest_sheet:
            return []

        result = self.conn.execute(
            """
            SELECT change_id, account_name, balance, previous_balance, delta
            FROM interest_balance_changes
            WHERE source_sheet = ?
            ORDER BY balance DESC
        """,
            [latest_sheet[0]],
        ).fetchall()
        return result

    def get_interest_balance_history(self, account_name=None):
        if account_name:
            result = self.conn.execute(
                """
                SELECT balance_date, balance, delta
                FROM interest_balance_changes
                WHERE account_name = ?
                ORDER BY balance_date
            """,
                [account_name],
            ).fetchall()
        else:
            result = self.conn.execute(
                """
                SELECT balance_date, SUM(balance) as total_balance, SUM(delta) as total_delta
                FROM interest_balance_changes
                GROUP BY balance_date
                ORDER BY balance_date
            """
            ).fetchall()
        return result

    def _next_id(self, table_name, id_column):
        row = self.conn.execute(
            f"SELECT COALESCE(MAX({id_column}), 0) + 1 FROM {table_name}"
        ).fetchone()
        return int(row[0] or 1)
