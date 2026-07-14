"""
Cash pool queries for the Finance database.
"""
from datetime import datetime, timedelta
from pathlib import Path

try:
    from .db_schema import get_connection
except ImportError:
    from db_schema import get_connection


def default_db_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "finance.duckdb")


class CashQueries:
    def __init__(self, conn=None, db_path=None):
        if conn is None:
            if db_path is None:
                db_path = default_db_path()
            self.conn = get_connection(str(db_path))
        else:
            self.conn = conn

    def get_balance_by_account(self, as_of_date=None):
        if as_of_date is None:
            as_of_date = datetime.now().date()

        result = self.conn.execute(
            """
            SELECT
                a.account_name,
                MAX(t.balance_after) as current_balance,
                MAX(t.transaction_date) as last_transaction
            FROM accounts a
            LEFT JOIN cash_transactions t ON a.account_id = t.account_id
                AND t.transaction_date <= ?
            WHERE a.is_active = TRUE
            GROUP BY a.account_name
            ORDER BY current_balance DESC
        """,
            [as_of_date],
        ).fetchall()

        return result

    def get_account_balances(self, as_of_date=None):
        return self.get_balance_by_account(as_of_date)

    def get_active_account_names(self):
        result = self.conn.execute(
            "SELECT account_name FROM accounts WHERE is_active = TRUE ORDER BY account_name"
        ).fetchall()
        return [row[0] for row in result]

    def get_category_names(self):
        result = self.conn.execute(
            "SELECT category_name FROM categories ORDER BY category_name"
        ).fetchall()
        return [row[0] for row in result]

    def get_categories(self):
        result = self.conn.execute(
            "SELECT category_id, main_category_id, sub_category_id, category_name, category_type, color_code FROM categories ORDER BY category_name"
        ).fetchall()
        return result

    def get_main_category_names(self):
        result = self.conn.execute(
            "SELECT main_category_name FROM main_categories ORDER BY main_category_name"
        ).fetchall()
        return [row[0] for row in result]

    def get_sub_category_names(self):
        result = self.conn.execute(
            "SELECT sub_category_name FROM sub_categories ORDER BY sub_category_name"
        ).fetchall()
        return [row[0] for row in result]

    def save_categories(self, records):
        if not records:
            return 0

        saved = 0
        for record in records:
            if record.get("_action") == "delete":
                original_key = record.get("original_key")
                if original_key:
                    self.conn.execute(
                        "DELETE FROM categories WHERE category_id = ?",
                        [int(float(original_key))],
                    )
                    saved += 1
                continue

            original_key = record.get("original_key")
            category_id = int(float(original_key)) if original_key not in (None, "") else self._next_id("categories", "category_id")

            main_category_id = record.get("Main Category ID")
            if main_category_id in (None, ""):
                main_category_id = None
            else:
                main_category_id = int(float(main_category_id))

            sub_category_id = record.get("Sub Category ID")
            if sub_category_id in (None, ""):
                sub_category_id = None
            else:
                sub_category_id = int(float(sub_category_id))

            category_name = record.get("Category Name") or "Uncategorized"
            category_type = record.get("Category Type") or "expense"
            color_code = record.get("Color Code")

            if original_key:
                self.conn.execute(
                    "UPDATE categories SET main_category_id = ?, sub_category_id = ?, category_name = ?, category_type = ?, color_code = ? WHERE category_id = ?",
                    [
                        main_category_id,
                        sub_category_id,
                        category_name,
                        category_type,
                        color_code,
                        category_id,
                    ],
                )
            else:
                self.conn.execute(
                    "INSERT INTO categories (category_id, main_category_id, sub_category_id, category_name, category_type, color_code) VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        category_id,
                        main_category_id,
                        sub_category_id,
                        category_name,
                        category_type,
                        color_code,
                    ],
                )

            saved += 1

        self.conn.commit()
        return saved

    def merge_accounts(self, source_account_name, target_account_name, selected_keys=None):
        if not source_account_name or not target_account_name:
            raise ValueError("Both source and target account names must be provided.")
        if source_account_name == target_account_name:
            raise ValueError("Source and target account names must differ.")

        source_row = self.conn.execute(
            "SELECT account_id FROM accounts WHERE account_name = ?",
            [source_account_name],
        ).fetchone()
        if not source_row:
            raise ValueError(f"Source account not found: {source_account_name}")
        source_account_id = source_row[0]

        target_row = self.conn.execute(
            "SELECT account_id FROM accounts WHERE account_name = ?",
            [target_account_name],
        ).fetchone()
        if target_row:
            target_account_id = target_row[0]
        else:
            target_account_id = self._next_id("accounts", "account_id")
            self.conn.execute(
                "INSERT INTO accounts (account_id, account_name, account_type, currency, is_active) VALUES (?, ?, 'bank', 'EUR', TRUE)",
                [target_account_id, target_account_name],
            )

        if selected_keys is not None:
            if not selected_keys:
                return {
                    "source": source_account_name,
                    "target": target_account_name,
                    "rows_updated": 0,
                }

            row_count = 0
            unique_keys = list(dict.fromkeys(selected_keys))
            for key in unique_keys:
                parts = key.split("|")
                if len(parts) != 4:
                    continue
                transaction_id, key_account_id, category_id, row_nr = parts
                if int(float(key_account_id)) != source_account_id:
                    continue
                params = [target_account_id, int(float(transaction_id)), int(float(category_id)), source_account_id]
                sql = "UPDATE cash_transactions SET account_id = ? WHERE transaction_id = ? AND category_id = ? AND account_id = ?"
                self.conn.execute(sql, params)
                row_count += self.conn.execute(
                    "SELECT COUNT(*) FROM cash_transactions WHERE transaction_id = ? AND category_id = ? AND account_id = ?",
                    [int(float(transaction_id)), int(float(category_id)), target_account_id],
                ).fetchone()[0]

            remaining = self.conn.execute(
                "SELECT COUNT(*) FROM cash_transactions WHERE account_id = ?",
                [source_account_id],
            ).fetchone()[0]
            if remaining == 0:
                self.conn.execute(
                    "DELETE FROM accounts WHERE account_id = ?",
                    [source_account_id],
                )
            self.conn.commit()

            return {
                "source": source_account_name,
                "target": target_account_name,
                "rows_updated": int(row_count),
            }

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM cash_transactions WHERE account_id = ?",
            [source_account_id],
        ).fetchone()[0]

        self.conn.execute(
            "UPDATE cash_transactions SET account_id = ? WHERE account_id = ?",
            [target_account_id, source_account_id],
        )
        self.conn.execute(
            "DELETE FROM accounts WHERE account_id = ?",
            [source_account_id],
        )
        self.conn.commit()

        return {
            "source": source_account_name,
            "target": target_account_name,
            "rows_updated": int(row_count),
        }

    def merge_categories(self, source_category_name, target_category_name, selected_keys=None):
        if not source_category_name or not target_category_name:
            raise ValueError("Both source and target category names must be provided.")
        if source_category_name == target_category_name:
            raise ValueError("Source and target category names must differ.")

        source_row = self.conn.execute(
            "SELECT category_id, category_type FROM categories WHERE category_name = ?",
            [source_category_name],
        ).fetchone()
        if not source_row:
            raise ValueError(f"Source category not found: {source_category_name}")
        source_category_id, source_category_type = source_row

        target_row = self.conn.execute(
            "SELECT category_id FROM categories WHERE category_name = ?",
            [target_category_name],
        ).fetchone()
        if target_row:
            target_category_id = target_row[0]
        else:
            target_category_id = self._next_id("categories", "category_id")
            main_name, sub_name = self._split_category_name(target_category_name)
            main_row = self.conn.execute(
                "SELECT main_category_id FROM main_categories WHERE main_category_name = ?",
                [main_name],
            ).fetchone()
            if main_row:
                main_category_id = main_row[0]
            else:
                main_category_id = self._next_id("main_categories", "main_category_id")
                self.conn.execute(
                    "INSERT INTO main_categories (main_category_id, main_category_name) VALUES (?, ?)",
                    [main_category_id, main_name],
                )

            sub_category_id = None
            if sub_name is not None:
                sub_row = self.conn.execute(
                    "SELECT sub_category_id FROM sub_categories WHERE main_category_id = ? AND sub_category_name = ?",
                    [main_category_id, sub_name],
                ).fetchone()
                if sub_row:
                    sub_category_id = sub_row[0]
                else:
                    sub_category_id = self._next_id("sub_categories", "sub_category_id")
                    self.conn.execute(
                        "INSERT INTO sub_categories (sub_category_id, main_category_id, sub_category_name) VALUES (?, ?, ?)",
                        [sub_category_id, main_category_id, sub_name],
                    )

            self.conn.execute(
                "INSERT INTO categories (category_id, main_category_id, sub_category_id, category_name, category_type) VALUES (?, ?, ?, ?, ?)",
                [target_category_id, main_category_id, sub_category_id, target_category_name, source_category_type],
            )
        if selected_keys is not None:
            if not selected_keys:
                return {
                    "source": source_category_name,
                    "target": target_category_name,
                    "rows_updated": 0,
                }

            row_count = 0
            unique_keys = list(dict.fromkeys(selected_keys))
            for key in unique_keys:
                parts = key.split("|")
                if len(parts) != 4:
                    continue
                transaction_id, account_id, key_category_id, row_nr = parts
                if int(float(key_category_id)) != source_category_id:
                    continue
                params = [target_category_id, int(float(transaction_id)), int(float(account_id)), source_category_id]
                self.conn.execute(
                    "UPDATE cash_transactions SET category_id = ? WHERE transaction_id = ? AND account_id = ? AND category_id = ?",
                    params,
                )
                row_count += self.conn.execute(
                    "SELECT COUNT(*) FROM cash_transactions WHERE transaction_id = ? AND account_id = ? AND category_id = ?",
                    [int(float(transaction_id)), int(float(account_id)), target_category_id],
                ).fetchone()[0]

            remaining = self.conn.execute(
                "SELECT COUNT(*) FROM cash_transactions WHERE category_id = ?",
                [source_category_id],
            ).fetchone()[0]
            if remaining == 0:
                self.conn.execute(
                    "DELETE FROM categories WHERE category_id = ?",
                    [source_category_id],
                )
            self.conn.commit()

            return {
                "source": source_category_name,
                "target": target_category_name,
                "rows_updated": int(row_count),
            }

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM cash_transactions WHERE category_id = ?",
            [source_category_id],
        ).fetchone()[0]

        self.conn.execute(
            "UPDATE cash_transactions SET category_id = ? WHERE category_id = ?",
            [target_category_id, source_category_id],
        )
        self.conn.execute(
            "DELETE FROM categories WHERE category_id = ?",
            [source_category_id],
        )
        self.conn.commit()

        return {
            "source": source_category_name,
            "target": target_category_name,
            "rows_updated": int(row_count),
        }

    def merge_transaction_dates(self, source_date, target_date):
        if source_date == target_date:
            raise ValueError("Source and target dates must differ.")

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM cash_transactions WHERE transaction_date = ?",
            [source_date],
        ).fetchone()[0]
        if row_count == 0:
            raise ValueError(f"No transactions found on source date: {source_date}")

        self.conn.execute(
            "UPDATE cash_transactions SET transaction_date = ? WHERE transaction_date = ?",
            [target_date, source_date],
        )
        self.conn.commit()

        return {
            "source_date": source_date,
            "target_date": target_date,
            "rows_updated": int(row_count),
        }

    def get_spending_by_category(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.now().date() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now().date()

        result = self.conn.execute(
            """
            SELECT
                c.category_name,
                COUNT(*) as transaction_count,
                SUM(t.amount) as total_amount,
                AVG(t.amount) as average_amount
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.transaction_date BETWEEN ? AND ?
                AND c.category_type = 'expense'
            GROUP BY c.category_name
            ORDER BY total_amount DESC
        """,
            [start_date, end_date],
        ).fetchall()

        return result

    def get_total_income(self):
        result = self.conn.execute(
            """
            SELECT SUM(t.amount)
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE c.category_type = 'income'
        """
        ).fetchone()[0]
        return result or 0

    def get_total_expenses(self):
        result = self.conn.execute(
            """
            SELECT SUM(t.amount)
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE c.category_type = 'expense'
        """
        ).fetchone()[0]
        return result or 0

    def get_transaction_frequency(self):
        result = self.conn.execute(
            """
            SELECT
                c.category_name,
                COUNT(*) as transaction_count
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            GROUP BY c.category_name
            ORDER BY transaction_count DESC
        """
        ).fetchall()
        return result

    def get_average_transaction(self):
        result = self.conn.execute(
            """
            SELECT
                c.category_name,
                AVG(t.amount) as average_amount
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            GROUP BY c.category_name
            ORDER BY average_amount DESC
        """
        ).fetchall()
        return result

    def get_balance_history(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.now().date() - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now().date()

        result = self.conn.execute(
            """
            SELECT
                transaction_date,
                MAX(balance_after) as balance
            FROM cash_transactions
            WHERE transaction_date BETWEEN ? AND ?
            GROUP BY transaction_date
            ORDER BY transaction_date
        """,
            [start_date, end_date],
        ).fetchall()

        return result

    def get_net_income(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.now().date() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now().date()

        result = self.conn.execute(
            """
            SELECT
                c.category_type,
                SUM(t.amount) as total
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.transaction_date BETWEEN ? AND ?
            GROUP BY c.category_type
        """,
            [start_date, end_date],
        ).fetchall()

        return result

    def get_monthly_summary(self, year=None, month=None):
        if year is None or month is None:
            today = datetime.now().date()
            year, month = today.year, today.month

        result = self.conn.execute(
            """
            SELECT
                DATE_TRUNC('month', t.transaction_date)::DATE as month,
                c.category_type,
                SUM(t.amount) as total
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE YEAR(t.transaction_date) = ?
                AND MONTH(t.transaction_date) = ?
            GROUP BY DATE_TRUNC('month', t.transaction_date), c.category_type
            ORDER BY DATE_TRUNC('month', t.transaction_date), c.category_type
        """,
            [year, month],
        ).fetchall()

        return result

    def search_transactions(self, search_term, limit=20):
        search_pattern = f"%{search_term}%"
        result = self.conn.execute(
            """
            SELECT
                t.transaction_id,
                t.description,
                c.category_name,
                t.amount,
                t.transaction_date,
                a.account_name
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            JOIN accounts a ON t.account_id = a.account_id
            WHERE LOWER(t.description) LIKE LOWER(?)
                OR LOWER(c.category_name) LIKE LOWER(?)
            ORDER BY t.transaction_date DESC
            LIMIT ?
        """,
            [search_pattern, search_pattern, limit],
        ).fetchall()

        return result

    def get_transactions(self, start_date=None, end_date=None, minimum_amount=None, limit=None):
        sql = """
            SELECT
                t.transaction_id,
                t.transaction_date,
                a.account_name,
                c.category_name,
                t.description,
                t.amount,
                t.balance_after,
                t.source_sheet,
                t.account_id,
                t.category_id,
                t.row_nr
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            JOIN accounts a ON t.account_id = a.account_id
        """

        conditions = []
        params = []

        if start_date is not None:
            conditions.append("t.transaction_date >= ?")
            params.append(start_date)

        if end_date is not None:
            conditions.append("t.transaction_date <= ?")
            params.append(end_date)

        if minimum_amount is not None:
            conditions.append("ABS(t.amount) >= ?")
            params.append(minimum_amount)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY t.transaction_date DESC, t.transaction_id DESC"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        return self.conn.execute(sql, params).fetchall()

    def get_transactions_by_account_name(self, account_name):
        sql = """
            SELECT
                t.transaction_id,
                t.transaction_date,
                a.account_name,
                c.category_name,
                t.description,
                t.amount,
                t.balance_after,
                t.source_sheet,
                t.account_id,
                t.category_id,
                t.row_nr
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            JOIN accounts a ON t.account_id = a.account_id
            WHERE a.account_name = ?
            ORDER BY t.transaction_date DESC, t.transaction_id DESC
        """
        return self.conn.execute(sql, [account_name]).fetchall()

    def get_transactions_by_category_name(self, category_name):
        sql = """
            SELECT
                t.transaction_id,
                t.transaction_date,
                a.account_name,
                c.category_name,
                t.description,
                t.amount,
                t.balance_after,
                t.source_sheet,
                t.account_id,
                t.category_id,
                t.row_nr
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            JOIN accounts a ON t.account_id = a.account_id
            WHERE c.category_name = ?
            ORDER BY t.transaction_date DESC, t.transaction_id DESC
        """
        return self.conn.execute(sql, [category_name]).fetchall()

    def get_transactions_by_date(self, transaction_date):
        sql = """
            SELECT
                t.transaction_id,
                t.transaction_date,
                a.account_name,
                c.category_name,
                t.description,
                t.amount,
                t.balance_after,
                t.source_sheet,
                t.account_id,
                t.category_id,
                t.row_nr
            FROM cash_transactions t
            JOIN categories c ON t.category_id = c.category_id
            JOIN accounts a ON t.account_id = a.account_id
            WHERE t.transaction_date = ?
            ORDER BY t.transaction_date DESC, t.transaction_id DESC
        """
        return self.conn.execute(sql, [transaction_date]).fetchall()

    def _next_id(self, table_name, id_column):
        row = self.conn.execute(
            f"SELECT COALESCE(MAX({id_column}), 0) + 1 FROM {table_name}"
        ).fetchone()
        return int(row[0] or 1)

    def _split_category_name(self, category_name):
        if category_name is None:
            return "Uncategorized", None
        category_name = str(category_name).strip()
        if not category_name:
            return "Uncategorized", None
        if "/" in category_name:
            main_name, sub_name = category_name.split("/", 1)
            return main_name.strip() or "Uncategorized", sub_name
        return category_name, None

    def _get_or_create_account_id(self, account_name):
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

    def _get_or_create_category_id(self, category_name):
        row = self.conn.execute(
            "SELECT category_id FROM categories WHERE category_name = ?",
            [category_name],
        ).fetchone()
        if row:
            return row[0]

        category_id = self._next_id("categories", "category_id")
        main_name, sub_name = self._split_category_name(category_name)

        main_row = self.conn.execute(
            "SELECT main_category_id FROM main_categories WHERE main_category_name = ?",
            [main_name],
        ).fetchone()
        if main_row:
            main_category_id = main_row[0]
        else:
            main_category_id = self._next_id("main_categories", "main_category_id")
            self.conn.execute(
                "INSERT INTO main_categories (main_category_id, main_category_name) VALUES (?, ?)",
                [main_category_id, main_name],
            )

        sub_category_id = None
        if sub_name is not None:
            sub_row = self.conn.execute(
                "SELECT sub_category_id FROM sub_categories WHERE main_category_id = ? AND sub_category_name = ?",
                [main_category_id, sub_name],
            ).fetchone()
            if sub_row:
                sub_category_id = sub_row[0]
            else:
                sub_category_id = self._next_id("sub_categories", "sub_category_id")
                self.conn.execute(
                    "INSERT INTO sub_categories (sub_category_id, main_category_id, sub_category_name) VALUES (?, ?, ?)",
                    [sub_category_id, main_category_id, sub_name],
                )

        self.conn.execute(
            "INSERT INTO categories (category_id, main_category_id, sub_category_id, category_name, category_type) VALUES (?, ?, ?, ?, 'expense')",
            [category_id, main_category_id, sub_category_id, category_name],
        )
        return category_id

    def save_transactions(self, transactions):
        if not transactions:
            return 0

        saved = 0
        for transaction in transactions:
            if transaction.get("_action") == "delete":
                orig_transaction_id, orig_account_id, orig_category_id = transaction["original_key"].split("|")
                self.conn.execute(
                    "DELETE FROM cash_transactions WHERE transaction_id = ? AND account_id = ? AND category_id = ?",
                    [orig_transaction_id, orig_account_id, orig_category_id],
                )
                saved += 1
                continue

            original_key = transaction.get("original_key")
            if original_key:
                orig_transaction_id, orig_account_id, orig_category_id = original_key.split("|")
                self.conn.execute(
                    "DELETE FROM cash_transactions WHERE transaction_id = ? AND account_id = ? AND category_id = ?",
                    [orig_transaction_id, orig_account_id, orig_category_id],
                )

            account_id = self._get_or_create_account_id(transaction.get("Account") or "Unknown")
            category_id = self._get_or_create_category_id(transaction.get("Category") or "Uncategorized")
            transaction_id = int(transaction["Transaction ID"]) if transaction.get("Transaction ID") not in (None, "") else self._next_id("cash_transactions", "transaction_id")
            row_nr = int(transaction.get("row_nr") or 0)
            description = transaction.get("Description") or ""
            amount = float(transaction.get("Amount") or 0)
            transaction_date = transaction.get("Date")
            balance_after = float(transaction.get("Balance After") or 0)
            source_sheet = transaction.get("Source Sheet") or "manual"

            self.conn.execute(
                "INSERT INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    transaction_id,
                    row_nr,
                    description,
                    account_id,
                    category_id,
                    amount,
                    transaction_date,
                    balance_after,
                    source_sheet,
                ],
            )
            saved += 1

        self.conn.commit()
        return saved
