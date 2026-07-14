"""
Goods pool queries for the Finance database.
"""
from pathlib import Path
from datetime import date

try:
    from .db_schema import get_connection
    from .goods_depreciation import calculate_goods_current_value
except ImportError:
    from db_schema import get_connection
    from goods_depreciation import calculate_goods_current_value


def default_db_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "finance.duckdb")


class GoodsQueries:
    def __init__(self, conn=None, db_path=None):
        if conn is None:
            if db_path is None:
                db_path = default_db_path()
            self.conn = get_connection(str(db_path))
        else:
            self.conn = conn

    def save_goods_valuations(self, records):
        if not records:
            return 0

        saved = 0
        for record in records:
            if record.get("_action") == "delete":
                valuation_id = int(record["original_key"])
                self.conn.execute(
                    "DELETE FROM goods_valuations WHERE valuation_id = ?",
                    [valuation_id],
                )
                saved += 1
                continue

            original_key = record.get("original_key")
            if original_key:
                self.conn.execute(
                    "DELETE FROM goods_valuations WHERE valuation_id = ?",
                    [int(original_key)],
                )

            valuation_id = int(record.get("Valuation ID")) if record.get("Valuation ID") not in (None, "") else self._next_id("goods_valuations", "valuation_id")
            valuation_date = record.get("Valuation Date")
            item_name = record.get("Item Name") or ""
            purchase_value = float(record.get("Purchase Value") or 0)
            depreciation_input = float(record.get("Depreciation Input") or 0)
            value_previous = float(record.get("Value Previous") or 0)
            value_change = float(record.get("Value Change") or 0)
            current_value = float(record.get("Current Value") or 0)
            source_sheet = record.get("Source Sheet") or "manual"
            row_nr = int(record.get("row_nr") or 0)

            self.conn.execute(
                "INSERT INTO goods_valuations (valuation_id, source_sheet, valuation_date, row_nr, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    valuation_id,
                    source_sheet,
                    valuation_date,
                    row_nr,
                    item_name,
                    purchase_value,
                    depreciation_input,
                    value_previous,
                    value_change,
                    current_value,
                ],
            )
            saved += 1

        self.conn.commit()
        return saved

    def get_goods_item_names(self):
        result = self.conn.execute(
            "SELECT DISTINCT item_name FROM goods_valuations ORDER BY item_name"
        ).fetchall()
        return [row[0] for row in result]

    def get_goods_valuations_by_item_name(self, item_name):
        sql = """
            SELECT
                valuation_id,
                valuation_date,
                item_name,
                purchase_value,
                depreciation_input,
                value_previous,
                value_change,
                current_value,
                source_sheet,
                row_nr
            FROM goods_valuations
            WHERE item_name = ?
            ORDER BY valuation_date DESC, valuation_id
        """
        return self.conn.execute(sql, [item_name]).fetchall()

    def get_goods_valuations_by_valuation_date(self, valuation_date):
        sql = """
            SELECT
                valuation_id,
                valuation_date,
                item_name,
                purchase_value,
                depreciation_input,
                value_previous,
                value_change,
                current_value,
                source_sheet,
                row_nr
            FROM goods_valuations
            WHERE valuation_date = ?
            ORDER BY valuation_id
        """
        return self.conn.execute(sql, [valuation_date]).fetchall()

    def get_goods_valuations(self, start_date=None, end_date=None):
        sql = """
            SELECT
                valuation_id,
                valuation_date,
                item_name,
                purchase_value,
                depreciation_input,
                value_previous,
                value_change,
                current_value,
                source_sheet,
                row_nr
            FROM goods_valuations
        """
        params = []
        if start_date is not None and end_date is not None:
            sql += " WHERE valuation_date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date is not None:
            sql += " WHERE valuation_date >= ?"
            params = [start_date]
        elif end_date is not None:
            sql += " WHERE valuation_date <= ?"
            params = [end_date]

        sql += " ORDER BY valuation_date DESC, valuation_id"
        return self.conn.execute(sql, params).fetchall()

    def merge_goods_valuations_by_item_name(self, source_item_name, target_item_name, selected_valuation_ids=None):
        if source_item_name == target_item_name:
            raise ValueError("Source and target must differ.")

        if selected_valuation_ids is not None:
            if not selected_valuation_ids:
                return {"source": source_item_name, "target": target_item_name, "rows_updated": 0}

            unique_ids = list(dict.fromkeys(selected_valuation_ids))
            row_count = 0
            for valuation_id in unique_ids:
                if valuation_id is None or valuation_id == "":
                    continue
                row_count += self.conn.execute(
                    "UPDATE goods_valuations SET item_name = ? WHERE valuation_id = ? AND item_name = ?",
                    [target_item_name, int(float(valuation_id)), source_item_name],
                ).rowcount
            self.conn.commit()
            return {"source": source_item_name, "target": target_item_name, "rows_updated": int(row_count)}

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM goods_valuations WHERE item_name = ?",
            [source_item_name],
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE goods_valuations SET item_name = ? WHERE item_name = ?",
            [target_item_name, source_item_name],
        )
        self.conn.commit()
        return {
            "source": source_item_name,
            "target": target_item_name,
            "rows_updated": int(row_count),
        }

    def merge_goods_valuations_by_valuation_date(self, source_date, target_date):
        if source_date == target_date:
            raise ValueError("Source and target dates must differ.")

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM goods_valuations WHERE valuation_date = ?",
            [source_date],
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE goods_valuations SET valuation_date = ? WHERE valuation_date = ?",
            [target_date, source_date],
        )
        self.conn.commit()
        return {
            "source_date": source_date,
            "target_date": target_date,
            "rows_updated": int(row_count),
        }

    def get_latest_goods_valuations(self):
        latest_sheet = self.conn.execute(
            "SELECT source_sheet FROM goods_valuations ORDER BY valuation_date DESC LIMIT 1"
        ).fetchone()
        if not latest_sheet:
            return []

        result = self.conn.execute(
            """
            SELECT item_name, purchase_value, current_value, value_change
            FROM goods_valuations
            WHERE source_sheet = ?
            ORDER BY current_value DESC
        """,
            [latest_sheet[0]],
        ).fetchall()
        return result

    def get_goods_value_history(self, item_name=None):
        if item_name:
            result = self.conn.execute(
                """
                SELECT valuation_date, current_value
                FROM goods_valuations
                WHERE item_name = ?
                ORDER BY valuation_date
            """,
                [item_name],
            ).fetchall()
        else:
            result = self.conn.execute(
                """
                SELECT valuation_date, SUM(current_value) as total_value
                FROM goods_valuations
                GROUP BY valuation_date
                ORDER BY valuation_date
            """
            ).fetchall()
        return result

    def get_asset_depreciation(self):
        return self.get_latest_goods_valuations()

    @staticmethod
    def _to_float(value, default=0.0):
        if value is None or value == "":
            return default
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _parse_date(value):
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
        try:
            return date(value.year, value.month, value.day)
        except Exception:
            return None

    @staticmethod
    def _months_between(start_date, end_date):
        if start_date is None or end_date is None:
            return 0
        return max(0, (end_date.year - start_date.year) * 12 + end_date.month - start_date.month)

    @staticmethod
    def _row_diff_exists(original_row, normalized_row):
        return (
            original_row[6] != normalized_row[6]
            or original_row[7] != normalized_row[7]
        )

    def _calculate_normalized_goods_rows(self, rows):
        normalized_by_id = {}
        grouped_rows = {}
        for row in rows:
            item_name = row[2] or ""
            grouped_rows.setdefault(item_name, []).append(row)

        for item_name, item_rows in grouped_rows.items():
            item_rows_sorted = sorted(
                item_rows,
                key=lambda r: (
                    self._parse_date(r[1]) or date.min,
                    r[0],
                ),
            )
            previous_date = None
            previous_current_value = None

            for row in item_rows_sorted:
                valuation_id, valuation_date, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value, source_sheet, row_nr = row

                purchase_value_numeric = self._to_float(purchase_value)
                depreciation_input_numeric = self._to_float(depreciation_input)
                value_previous_numeric = self._to_float(value_previous, purchase_value_numeric)

                if (value_previous in (None, "") or value_previous_numeric == 0.0) and previous_current_value is not None:
                    value_previous_numeric = previous_current_value

                current_value_present = current_value not in (None, "")
                value_change_present = value_change not in (None, "")

                current_date = self._parse_date(valuation_date)
                months_diff = self._months_between(previous_date, current_date) if previous_date else 0

                if purchase_value is not None and depreciation_input is not None:
                    computed_current = calculate_goods_current_value(
                        purchase_value,
                        depreciation_input,
                        value_previous_numeric,
                        months_diff,
                    )
                    computed_change = round(computed_current - value_previous_numeric, 2)
                elif value_change_present:
                    computed_change = round(self._to_float(value_change, 0.0), 2)
                    computed_current = round(value_previous_numeric + computed_change, 2)
                elif current_value_present:
                    computed_current = self._to_float(current_value, value_previous_numeric)
                    computed_change = round(computed_current - value_previous_numeric, 2)
                else:
                    computed_current = round(value_previous_numeric, 2)
                    computed_change = 0.0

                normalized = (
                    valuation_id,
                    valuation_date,
                    item_name,
                    purchase_value,
                    depreciation_input,
                    value_previous,
                    computed_change,
                    computed_current,
                    source_sheet,
                    row_nr,
                )
                normalized_by_id[valuation_id] = normalized

                previous_date = current_date
                previous_current_value = computed_current

        normalized_rows = [normalized_by_id.get(row[0], row) for row in rows]
        changed_ids = [row[0] for row, normalized in zip(rows, normalized_rows) if self._row_diff_exists(row, normalized)]
        return normalized_rows, changed_ids

    def normalize_goods_valuations(self, item_name=None, valuation_date=None, valuation_ids=None, what_if=True):
        if item_name is not None and valuation_date is not None:
            raise ValueError("Provide either item_name or valuation_date, not both.")

        if item_name:
            rows = self.get_goods_valuations_by_item_name(item_name)
        elif valuation_date:
            rows = self.get_goods_valuations_by_valuation_date(valuation_date)
        else:
            rows = self.get_goods_valuations()

        normalized_rows, changed_ids = self._calculate_normalized_goods_rows(rows)
        rows_changed = len(changed_ids)

        if not what_if:
            if valuation_ids is not None:
                active_ids = {int(float(i)) for i in valuation_ids if i not in (None, "")}
            else:
                active_ids = set(changed_ids)

            updated = 0
            for original, normalized in zip(rows, normalized_rows):
                if original[0] in active_ids and self._row_diff_exists(original, normalized):
                    self.conn.execute(
                        "UPDATE goods_valuations SET value_change = ?, current_value = ? WHERE valuation_id = ?",
                        [
                            float(normalized[6]),
                            float(normalized[7]),
                            int(original[0]),
                        ],
                    )
                    updated += 1
            self.conn.commit()
            rows_changed = updated

        return {
            "rows_processed": len(rows),
            "rows_changed": rows_changed,
            "original_rows": rows,
            "normalized_rows": normalized_rows,
            "changed_ids": changed_ids,
        }

    def preview_goods_normalization(self, item_name=None, valuation_date=None):
        return self.normalize_goods_valuations(
            item_name=item_name,
            valuation_date=valuation_date,
            what_if=True,
        )

    def _next_id(self, table_name, id_column):
        row = self.conn.execute(
            f"SELECT COALESCE(MAX({id_column}), 0) + 1 FROM {table_name}"
        ).fetchone()
        return int(row[0] or 1)
