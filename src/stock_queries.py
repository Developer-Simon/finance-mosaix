"""
Stock pool queries for the Finance database.
"""
from pathlib import Path

try:
    from .db_schema import get_connection
except ImportError:
    from db_schema import get_connection


def default_db_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "finance.duckdb")


class StockQueries:
    def __init__(self, conn=None, db_path=None):
        if conn is None:
            if db_path is None:
                db_path = default_db_path()
            self.conn = get_connection(str(db_path))
        else:
            self.conn = conn

    def save_stock_positions(self, records):
        if not records:
            return 0

        saved = 0
        for record in records:
            if record.get("_action") == "delete":
                position_id = int(record["original_key"])
                self.conn.execute(
                    "DELETE FROM stock_positions WHERE position_id = ?",
                    [position_id],
                )
                saved += 1
                continue

            original_key = record.get("original_key")
            if original_key:
                self.conn.execute(
                    "DELETE FROM stock_positions WHERE position_id = ?",
                    [int(original_key)],
                )

            position_id = int(record.get("Position ID")) if record.get("Position ID") not in (None, "") else self._next_id("stock_positions", "position_id")
            snapshot_date = record.get("Snapshot Date")
            name = record.get("Name") or ""
            ticker = record.get("Ticker") or ""
            quantity = float(record.get("Quantity") or 0)
            price_previous = float(record.get("Price Previous") or 0)
            price_current = float(record.get("Price Current") or 0)
            delta_value = float(record.get("Delta Value") or 0)
            delta_percent = float(record.get("Delta Percent") or 0)
            position_value = float(record.get("Position Value") or 0)
            depot_value_running = float(record.get("Depot Value Running") or 0)
            source_sheet = record.get("Source Sheet") or "manual"
            row_nr = int(record.get("row_nr") or 0)

            self.conn.execute(
                "INSERT INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    position_id,
                    source_sheet,
                    snapshot_date,
                    row_nr,
                    name,
                    ticker,
                    quantity,
                    price_previous,
                    price_current,
                    delta_value,
                    delta_percent,
                    position_value,
                    depot_value_running,
                ],
            )
            saved += 1

        self.conn.commit()
        return saved

    def get_stock_names(self):
        result = self.conn.execute(
            "SELECT DISTINCT name FROM stock_positions ORDER BY name"
        ).fetchall()
        return [row[0] for row in result]

    def get_stock_tickers(self):
        result = self.conn.execute(
            "SELECT DISTINCT ticker FROM stock_positions ORDER BY ticker"
        ).fetchall()
        return [row[0] for row in result]

    def get_stock_positions_by_name(self, name):
        sql = """
            SELECT
                position_id,
                snapshot_date,
                name,
                ticker,
                quantity,
                price_previous,
                price_current,
                delta_value,
                delta_percent,
                position_value,
                depot_value_running,
                source_sheet,
                row_nr
            FROM stock_positions
            WHERE name = ?
            ORDER BY snapshot_date DESC, position_id
        """
        return self.conn.execute(sql, [name]).fetchall()

    def get_stock_positions_by_ticker(self, ticker):
        sql = """
            SELECT
                position_id,
                snapshot_date,
                name,
                ticker,
                quantity,
                price_previous,
                price_current,
                delta_value,
                delta_percent,
                position_value,
                depot_value_running,
                source_sheet,
                row_nr
            FROM stock_positions
            WHERE ticker = ?
            ORDER BY snapshot_date DESC, position_id
        """
        return self.conn.execute(sql, [ticker]).fetchall()

    def get_stock_positions_by_snapshot_date(self, snapshot_date):
        sql = """
            SELECT
                position_id,
                snapshot_date,
                name,
                ticker,
                quantity,
                price_previous,
                price_current,
                delta_value,
                delta_percent,
                position_value,
                depot_value_running,
                source_sheet,
                row_nr
            FROM stock_positions
            WHERE snapshot_date = ?
            ORDER BY position_id
        """
        return self.conn.execute(sql, [snapshot_date]).fetchall()

    def get_stock_positions(self, start_date=None, end_date=None):
        sql = """
            SELECT
                position_id,
                snapshot_date,
                name,
                ticker,
                quantity,
                price_previous,
                price_current,
                delta_value,
                delta_percent,
                position_value,
                depot_value_running,
                source_sheet,
                row_nr
            FROM stock_positions
        """
        params = []
        if start_date is not None and end_date is not None:
            sql += " WHERE snapshot_date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date is not None:
            sql += " WHERE snapshot_date >= ?"
            params = [start_date]
        elif end_date is not None:
            sql += " WHERE snapshot_date <= ?"
            params = [end_date]

        sql += " ORDER BY snapshot_date DESC, position_id"
        return self.conn.execute(sql, params).fetchall()

    def merge_stock_positions_by_name(self, source_name, target_name, selected_position_ids=None):
        if source_name == target_name:
            raise ValueError("Source and target must differ.")

        if selected_position_ids is not None:
            if not selected_position_ids:
                return {"source": source_name, "target": target_name, "rows_updated": 0}

            unique_ids = list(dict.fromkeys(selected_position_ids))
            row_count = 0
            for position_id in unique_ids:
                if position_id is None or position_id == "":
                    continue
                row_count += self.conn.execute(
                    "UPDATE stock_positions SET name = ? WHERE position_id = ? AND name = ?",
                    [target_name, int(float(position_id)), source_name],
                ).rowcount
            self.conn.commit()
            return {"source": source_name, "target": target_name, "rows_updated": int(row_count)}

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM stock_positions WHERE name = ?",
            [source_name],
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE stock_positions SET name = ? WHERE name = ?",
            [target_name, source_name],
        )
        self.conn.commit()
        return {
            "source": source_name,
            "target": target_name,
            "rows_updated": int(row_count),
        }

    def merge_stock_positions_by_ticker(self, source_ticker, target_ticker, selected_position_ids=None):
        if source_ticker == target_ticker:
            raise ValueError("Source and target must differ.")

        if selected_position_ids is not None:
            if not selected_position_ids:
                return {"source": source_ticker, "target": target_ticker, "rows_updated": 0}

            unique_ids = list(dict.fromkeys(selected_position_ids))
            row_count = 0
            for position_id in unique_ids:
                if position_id is None or position_id == "":
                    continue
                row_count += self.conn.execute(
                    "UPDATE stock_positions SET ticker = ? WHERE position_id = ? AND ticker = ?",
                    [target_ticker, int(float(position_id)), source_ticker],
                ).rowcount
            self.conn.commit()
            return {"source": source_ticker, "target": target_ticker, "rows_updated": int(row_count)}

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM stock_positions WHERE ticker = ?",
            [source_ticker],
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE stock_positions SET ticker = ? WHERE ticker = ?",
            [target_ticker, source_ticker],
        )
        self.conn.commit()
        return {
            "source": source_ticker,
            "target": target_ticker,
            "rows_updated": int(row_count),
        }

    def merge_stock_positions_by_snapshot_date(self, source_date, target_date):
        if source_date == target_date:
            raise ValueError("Source and target dates must differ.")

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM stock_positions WHERE snapshot_date = ?",
            [source_date],
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE stock_positions SET snapshot_date = ? WHERE snapshot_date = ?",
            [target_date, source_date],
        )
        self.conn.commit()
        return {
            "source_date": source_date,
            "target_date": target_date,
            "rows_updated": int(row_count),
        }

    def get_latest_stock_positions(self):
        latest_snapshot = self.conn.execute(
            "SELECT MAX(snapshot_date) FROM stock_positions"
        ).fetchone()[0]
        if latest_snapshot is None:
            return []

        result = self.conn.execute(
            """
            SELECT
                name,
                ticker,
                quantity,
                price_current,
                position_value,
                delta_value,
                delta_percent
            FROM stock_positions
            WHERE snapshot_date = ?
            ORDER BY position_value DESC
        """,
            [latest_snapshot],
        ).fetchall()
        return result

    def get_stock_value_history(self):
        result = self.conn.execute(
            """
            SELECT snapshot_date, SUM(position_value) as total_value
            FROM stock_positions
            GROUP BY snapshot_date
            ORDER BY snapshot_date
        """
        ).fetchall()
        return result

    def get_stock_position_history(self, name):
        result = self.conn.execute(
            """
            SELECT snapshot_date, quantity, price_current, position_value
            FROM stock_positions
            WHERE name = ?
            ORDER BY snapshot_date
        """,
            [name],
        ).fetchall()
        return result

    def _next_id(self, table_name, id_column):
        row = self.conn.execute(
            f"SELECT COALESCE(MAX({id_column}), 0) + 1 FROM {table_name}"
        ).fetchone()
        return int(row[0] or 1)
