"""Database migration helpers for Finance mosaix.

This module tracks the current database schema version and applies migrations
from older production formats to the current schema.
"""

import gc
import shutil
import duckdb
from pathlib import Path

CURRENT_DB_VERSION = "0.1"
LEGACY_DB_VERSION = "0.0"
DB_METADATA_TABLE = "db_metadata"
DB_VERSION_KEY = "db_version"


def _table_exists(conn, table_name: str, schema_name: str | None = None) -> bool:
    if "." in table_name:
        schema_name, table_name = table_name.split(".", 1)

    if schema_name is None:
        schema_name = "main"

    if schema_name == "main":
        row = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [schema_name, table_name],
        ).fetchone()
        return bool(row)

    try:
        rows = [row[0] for row in conn.execute(f"SHOW TABLES FROM {schema_name}").fetchall()]
        return table_name in rows
    except Exception:
        try:
            row = conn.execute(f"PRAGMA table_info({schema_name}.{table_name})").fetchone()
            return bool(row)
        except Exception:
            return False


def _has_user_tables(conn) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'main' AND table_name != 'information_schema.tables'"
    ).fetchone()
    return bool(row and row[0] > 0)


def _get_table_columns(conn, table_name: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def _ensure_metadata_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS db_metadata (
            meta_key VARCHAR PRIMARY KEY,
            meta_value VARCHAR
        )
        """
    )


def _backup_database_file(db_path: str, version: str) -> str | None:
    if db_path in (":memory:", ""):
        return None

    db_file = Path(db_path)
    if not db_file.exists():
        return None

    backup_path = db_file.with_name(f"{db_file.stem}_{version}{db_file.suffix}")
    counter = 1
    while backup_path.exists():
        backup_path = db_file.with_name(f"{db_file.stem}_{version}_{counter}{db_file.suffix}")
        counter += 1

    try:
        db_file.rename(backup_path)
    except OSError:
        # If the database file is locked, fall back to a copy-based backup.
        shutil.copy2(db_file, backup_path)
    return str(backup_path)


def get_db_version(conn) -> str:
    if not _table_exists(conn, DB_METADATA_TABLE):
        return LEGACY_DB_VERSION if _has_user_tables(conn) else CURRENT_DB_VERSION

    row = conn.execute(
        "SELECT meta_value FROM db_metadata WHERE meta_key = ?",
        [DB_VERSION_KEY],
    ).fetchone()
    return row[0] if row else LEGACY_DB_VERSION


def set_db_version(conn, version: str):
    _ensure_metadata_table(conn)
    conn.execute("DELETE FROM db_metadata WHERE meta_key = ?", [DB_VERSION_KEY])
    conn.execute(
        "INSERT INTO db_metadata (meta_key, meta_value) VALUES (?, ?)",
        [DB_VERSION_KEY, version],
    )
    conn.commit()


def _next_id(conn, table_name: str, id_column: str) -> int:
    row = conn.execute(f"SELECT COALESCE(MAX({id_column}), 0) + 1 FROM {table_name}").fetchone()
    return int(row[0] or 1)


def _get_or_create_account_id(conn, account_name: str) -> int:
    if not account_name:
        account_name = "Unknown"

    row = conn.execute(
        "SELECT account_id FROM accounts WHERE account_name = ?",
        [account_name],
    ).fetchone()
    if row:
        return row[0]

    account_id = _next_id(conn, "accounts", "account_id")
    columns = _get_table_columns(conn, "accounts")
    insert_columns = ["account_id", "account_name"]
    values = [account_id, account_name]

    if "account_type" in columns:
        insert_columns.append("account_type")
        values.append("bank")
    if "currency" in columns:
        insert_columns.append("currency")
        values.append("EUR")
    if "is_active" in columns:
        insert_columns.append("is_active")
        values.append(True)

    placeholders = ", ".join("?" for _ in insert_columns)
    columns_sql = ", ".join(insert_columns)
    conn.execute(
        f"INSERT INTO accounts ({columns_sql}) VALUES ({placeholders})",
        values,
    )
    return account_id


def _ensure_accounts_table(conn):
    if not _table_exists(conn, "accounts"):
        conn.execute(
            """
            CREATE TABLE accounts (
                account_id INTEGER PRIMARY KEY,
                account_name VARCHAR,
                account_type VARCHAR,
                currency VARCHAR DEFAULT 'EUR',
                created_at DATE DEFAULT CURRENT_DATE,
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        )
        return

    columns = _get_table_columns(conn, "accounts")
    if "currency" not in columns:
        conn.execute("ALTER TABLE accounts ADD COLUMN currency VARCHAR DEFAULT 'EUR'")
    if "created_at" not in columns:
        conn.execute("ALTER TABLE accounts ADD COLUMN created_at DATE DEFAULT CURRENT_DATE")
    if "is_active" not in columns:
        conn.execute("ALTER TABLE accounts ADD COLUMN is_active BOOLEAN DEFAULT TRUE")


def _migrate_cash_transactions_to_account_ids(conn, source_alias: str | None = None):
    if not _table_exists(conn, "cash_transactions"):
        return

    if source_alias:
        if _table_exists(conn, f"{source_alias}.cash_transactions"):
            columns = _get_table_columns(conn, f"{source_alias}.cash_transactions")
            if "account_name" in columns:
                conn.execute(
                    "INSERT INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name, import_date) "
                    "SELECT t.transaction_id, t.row_nr, t.description, COALESCE(t.account_id, a.account_id), t.category_id, t.amount, t.transaction_date, t.balance_after, t.source_sheet, t.section_name, t.import_date "
                    f"FROM {source_alias}.cash_transactions t "
                    "LEFT JOIN accounts a ON t.account_name = a.account_name"
                )
            elif "account_id" in columns:
                conn.execute(
                    "INSERT INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name, import_date) "
                    f"SELECT transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name, import_date "
                    f"FROM {source_alias}.cash_transactions"
                )
        return

    columns = _get_table_columns(conn, "cash_transactions")
    if "account_id" not in columns:
        conn.execute("ALTER TABLE cash_transactions ADD COLUMN account_id INTEGER")

        if "account_name" in columns:
            rows = conn.execute(
                "SELECT DISTINCT account_name FROM cash_transactions WHERE account_name IS NOT NULL"
            ).fetchall()
            for (account_name,) in rows:
                if not account_name:
                    continue
                _get_or_create_account_id(conn, account_name)

            conn.execute(
                """
                UPDATE cash_transactions
                SET account_id = (
                    SELECT account_id FROM accounts WHERE accounts.account_name = cash_transactions.account_name
                )
                WHERE account_name IS NOT NULL
                """
            )
            conn.execute("ALTER TABLE cash_transactions DROP COLUMN account_name")

    _populate_category_combo_table(conn)


def _migrate_account_balances_to_account_ids(conn, source_alias: str | None = None):
    if not _table_exists(conn, "account_balances"):
        return

    if source_alias:
        if _table_exists(conn, f"{source_alias}.account_balances"):
            columns = _get_table_columns(conn, f"{source_alias}.account_balances")
            if "account_name" in columns:
                conn.execute(
                    "INSERT INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) "
                    "SELECT t.balance_id, t.source_sheet, t.balance_date, a.account_id, t.balance, t.previous_balance, t.delta, t.entry_type "
                    f"FROM {source_alias}.account_balances t "
                    "LEFT JOIN accounts a ON t.account_name = a.account_name"
                )
            elif "account_id" in columns:
                conn.execute(
                    "INSERT INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) "
                    f"SELECT balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type "
                    f"FROM {source_alias}.account_balances"
                )
        return

    columns = _get_table_columns(conn, "account_balances")
    if "account_id" not in columns:
        conn.execute("ALTER TABLE account_balances ADD COLUMN account_id INTEGER")

        if "account_name" in columns:
            rows = conn.execute(
                "SELECT DISTINCT account_name FROM account_balances WHERE account_name IS NOT NULL"
            ).fetchall()
            for (account_name,) in rows:
                if not account_name:
                    continue
                _get_or_create_account_id(conn, account_name)

            conn.execute(
                """
                UPDATE account_balances
                SET account_id = (
                    SELECT account_id FROM accounts WHERE accounts.account_name = account_balances.account_name
                )
                WHERE account_name IS NOT NULL
                """
            )
            conn.execute("ALTER TABLE account_balances DROP COLUMN account_name")


def _copy_legacy_accounts(conn, source_alias: str):
    if not _table_exists(conn, f"{source_alias}.accounts"):
        return

    columns = _get_table_columns(conn, f"{source_alias}.accounts")
    insert_columns = ["account_id", "account_name"]
    select_columns = ["account_id", "account_name"]

    if "account_type" in columns:
        insert_columns.append("account_type")
        select_columns.append("account_type")
    else:
        insert_columns.append("account_type")
        select_columns.append("'bank'")

    if "currency" in columns:
        insert_columns.append("currency")
        select_columns.append("currency")
    else:
        insert_columns.append("currency")
        select_columns.append("'EUR'")

    if "created_at" in columns:
        insert_columns.append("created_at")
        select_columns.append("created_at")
    else:
        insert_columns.append("created_at")
        select_columns.append("CURRENT_DATE")

    if "is_active" in columns:
        insert_columns.append("is_active")
        select_columns.append("is_active")
    else:
        insert_columns.append("is_active")
        select_columns.append("TRUE")

    conn.execute(
        f"INSERT INTO accounts ({', '.join(insert_columns)}) "
        f"SELECT {', '.join(select_columns)} FROM {source_alias}.accounts"
    )


def _copy_legacy_categories(conn, source_alias: str):
    if not _table_exists(conn, f"{source_alias}.categories"):
        return

    columns = _get_table_columns(conn, f"{source_alias}.categories")
    insert_columns = ["category_id", "main_category_id", "sub_category_id", "category_name"]
    select_columns = ["category_id", "NULL", "NULL", "category_name"]

    if "category_type" in columns:
        insert_columns.append("category_type")
        select_columns.append("category_type")
    else:
        insert_columns.append("category_type")
        select_columns.append("'expense'")

    if "color_code" in columns:
        insert_columns.append("color_code")
        select_columns.append("color_code")
    else:
        insert_columns.append("color_code")
        select_columns.append("NULL")

    conn.execute(
        f"INSERT INTO categories ({', '.join(insert_columns)}) "
        f"SELECT {', '.join(select_columns)} FROM {source_alias}.categories"
    )


def _copy_legacy_cash_transactions(conn, source_alias: str):
    if not _table_exists(conn, f"{source_alias}.cash_transactions"):
        return

    columns = _get_table_columns(conn, f"{source_alias}.cash_transactions")
    insert_clause = (
        "INSERT INTO cash_transactions (transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name, import_date) "
    )

    if "account_name" in columns:
        account_rows = conn.execute(
            f"SELECT DISTINCT account_name FROM {source_alias}.cash_transactions WHERE account_name IS NOT NULL"
        ).fetchall()
        for (account_name,) in account_rows:
            if account_name:
                _get_or_create_account_id(conn, account_name)

        conn.execute(
            insert_clause
            + "SELECT t.transaction_id, t.row_nr, t.description, a.account_id, t.category_id, t.amount, t.transaction_date, t.balance_after, t.source_sheet, t.section_name, t.import_date "
            + f"FROM {source_alias}.cash_transactions t "
            + "LEFT JOIN accounts a ON t.account_name = a.account_name"
        )
    elif "account_id" in columns:
        conn.execute(
            insert_clause
            + f"SELECT transaction_id, row_nr, description, account_id, category_id, amount, transaction_date, balance_after, source_sheet, section_name, import_date "
            + f"FROM {source_alias}.cash_transactions"
        )
    else:
        conn.execute(
            insert_clause
            + f"SELECT transaction_id, row_nr, description, NULL, category_id, amount, transaction_date, balance_after, source_sheet, section_name, import_date "
            + f"FROM {source_alias}.cash_transactions"
        )


def _copy_legacy_stock_positions(conn, source_alias: str):
    if not _table_exists(conn, f"{source_alias}.stock_positions"):
        return

    conn.execute(
        "INSERT INTO stock_positions (position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running) "
        f"SELECT position_id, source_sheet, snapshot_date, row_nr, name, ticker, quantity, price_previous, price_current, delta_value, delta_percent, position_value, depot_value_running FROM {source_alias}.stock_positions"
    )


def _copy_legacy_goods_valuations(conn, source_alias: str):
    if not _table_exists(conn, f"{source_alias}.goods_valuations"):
        return

    conn.execute(
        "INSERT INTO goods_valuations (valuation_id, source_sheet, valuation_date, row_nr, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value) "
        f"SELECT valuation_id, source_sheet, valuation_date, row_nr, item_name, purchase_value, depreciation_input, value_previous, value_change, current_value FROM {source_alias}.goods_valuations"
    )


def _copy_legacy_interest_balance_changes(conn, source_alias: str):
    if not _table_exists(conn, f"{source_alias}.interest_balance_changes"):
        return

    conn.execute(
        "INSERT INTO interest_balance_changes (change_id, source_sheet, balance_date, account_name, balance, previous_balance, delta) "
        f"SELECT change_id, source_sheet, balance_date, account_name, balance, previous_balance, delta FROM {source_alias}.interest_balance_changes"
    )


def _copy_legacy_account_balances(conn, source_alias: str):
    if not _table_exists(conn, f"{source_alias}.account_balances"):
        return

    columns = _get_table_columns(conn, f"{source_alias}.account_balances")
    if "account_name" in columns:
        conn.execute(
            "INSERT INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) "
            "SELECT t.balance_id, t.source_sheet, t.balance_date, a.account_id, t.balance, t.previous_balance, t.delta, t.entry_type "
            f"FROM {source_alias}.account_balances t "
            "LEFT JOIN accounts a ON t.account_name = a.account_name"
        )
    else:
        conn.execute(
            "INSERT INTO account_balances (balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type) "
            f"SELECT balance_id, source_sheet, balance_date, account_id, balance, previous_balance, delta, entry_type FROM {source_alias}.account_balances"
        )


def _split_category_name(category_name: str | None) -> tuple[str, str | None]:
    if category_name is None:
        return "Uncategorized", None

    category_name = str(category_name).strip()
    if not category_name:
        return "Uncategorized", None

    if "/" in category_name:
        main_name, sub_name = category_name.split("/", 1)
        main_name = main_name.strip() or "Uncategorized"
        return main_name, sub_name

    return category_name, None


def _ensure_category_hierarchy_tables(conn):
    if not _table_exists(conn, "main_categories"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS main_categories (
                main_category_id INTEGER PRIMARY KEY,
                main_category_name VARCHAR UNIQUE
            )
            """
        )

    if not _table_exists(conn, "sub_categories"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sub_categories (
                sub_category_id INTEGER PRIMARY KEY,
                main_category_id INTEGER,
                sub_category_name VARCHAR,
                UNIQUE(main_category_id, sub_category_name),
                FOREIGN KEY (main_category_id) REFERENCES main_categories(main_category_id)
            )
            """
        )


def _populate_category_combo_table(conn):
    if not _table_exists(conn, "cash_transactions") or not _table_exists(conn, "categories"):
        return

    _ensure_category_hierarchy_tables(conn)

    rows = conn.execute(
        "SELECT DISTINCT category_id, category_name, category_type, color_code FROM categories"
    ).fetchall()

    for category_id, category_name, category_type, color_code in rows:
        main_name, sub_name = _split_category_name(category_name)

        main_row = conn.execute(
            "SELECT main_category_id FROM main_categories WHERE main_category_name = ?",
            [main_name],
        ).fetchone()
        if main_row:
            main_category_id = main_row[0]
        else:
            main_category_id = _next_id(conn, "main_categories", "main_category_id")
            conn.execute(
                "INSERT INTO main_categories (main_category_id, main_category_name) VALUES (?, ?)",
                [main_category_id, main_name],
            )

        sub_category_id = None
        if sub_name is not None:
            sub_row = conn.execute(
                "SELECT sub_category_id FROM sub_categories WHERE main_category_id = ? AND sub_category_name = ?",
                [main_category_id, sub_name],
            ).fetchone()
            if sub_row:
                sub_category_id = sub_row[0]
            else:
                sub_category_id = _next_id(conn, "sub_categories", "sub_category_id")
                conn.execute(
                    "INSERT INTO sub_categories (sub_category_id, main_category_id, sub_category_name) VALUES (?, ?, ?)",
                    [sub_category_id, main_category_id, sub_name],
                )

        conn.execute(
            "UPDATE categories SET main_category_id = ?, sub_category_id = ? WHERE category_id = ?",
            [main_category_id, sub_category_id, category_id],
        )

    conn.commit()


def migrate_v0_0_to_0_1(conn, source_alias: str | None = None):
    _ensure_accounts_table(conn)

    if source_alias:
        _copy_legacy_accounts(conn, source_alias)
        _copy_legacy_categories(conn, source_alias)
        _populate_category_combo_table(conn)
        _copy_legacy_cash_transactions(conn, source_alias)
        _copy_legacy_stock_positions(conn, source_alias)
        _copy_legacy_goods_valuations(conn, source_alias)
        _copy_legacy_interest_balance_changes(conn, source_alias)
        _copy_legacy_account_balances(conn, source_alias)
    else:
        _migrate_cash_transactions_to_account_ids(conn)
        _populate_category_combo_table(conn)
        _migrate_account_balances_to_account_ids(conn)

    set_db_version(conn, CURRENT_DB_VERSION)


def _create_schema_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS main_categories (
            main_category_id INTEGER PRIMARY KEY,
            main_category_name VARCHAR UNIQUE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sub_categories (
            sub_category_id INTEGER PRIMARY KEY,
            main_category_id INTEGER,
            sub_category_name VARCHAR,
            UNIQUE(main_category_id, sub_category_name),
            FOREIGN KEY (main_category_id) REFERENCES main_categories(main_category_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY,
            main_category_id INTEGER,
            sub_category_id INTEGER,
            category_name VARCHAR UNIQUE,
            category_type VARCHAR,
            color_code VARCHAR,
            FOREIGN KEY (main_category_id) REFERENCES main_categories(main_category_id),
            FOREIGN KEY (sub_category_id) REFERENCES sub_categories(sub_category_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cash_transactions (
            transaction_id INTEGER,
            row_nr INTEGER,
            description VARCHAR,
            account_id INTEGER,
            category_id INTEGER,
            amount DECIMAL(14, 2),
            transaction_date DATE,
            balance_after DECIMAL(14, 2),
            source_sheet VARCHAR,
            section_name VARCHAR,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (transaction_id, category_id, account_id),
            FOREIGN KEY (account_id) REFERENCES accounts(account_id),
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_positions (
            position_id INTEGER PRIMARY KEY,
            source_sheet VARCHAR,
            snapshot_date DATE,
            row_nr INTEGER,
            name VARCHAR,
            ticker VARCHAR,
            quantity DECIMAL(16, 6),
            price_previous DECIMAL(14, 4),
            price_current DECIMAL(14, 4),
            delta_value DECIMAL(14, 4),
            delta_percent DECIMAL(12, 6),
            position_value DECIMAL(14, 2),
            depot_value_running DECIMAL(14, 2),
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS goods_valuations (
            valuation_id INTEGER PRIMARY KEY,
            source_sheet VARCHAR,
            valuation_date DATE,
            row_nr INTEGER,
            item_name VARCHAR,
            purchase_value DECIMAL(14, 2),
            depreciation_input DECIMAL(10, 4),
            value_previous DECIMAL(14, 2),
            value_change DECIMAL(14, 2),
            current_value DECIMAL(14, 2),
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS interest_balance_changes (
            change_id INTEGER PRIMARY KEY,
            source_sheet VARCHAR,
            balance_date DATE,
            account_name VARCHAR,
            balance DECIMAL(14, 2),
            previous_balance DECIMAL(14, 2),
            delta DECIMAL(14, 2),
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS account_balances (
            balance_id INTEGER PRIMARY KEY,
            source_sheet VARCHAR,
            balance_date DATE,
            account_id INTEGER,
            balance DECIMAL(14, 2),
            previous_balance DECIMAL(14, 2),
            delta DECIMAL(14, 2),
            entry_type VARCHAR,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        )
        """
    )


def migrate_database(conn, db_path: str | None = None):
    _ensure_metadata_table(conn)

    current_version = get_db_version(conn)
    if current_version == CURRENT_DB_VERSION:
        return conn

    if current_version == LEGACY_DB_VERSION:
        if db_path and db_path not in (":memory:", ""):
            conn.close()
            del conn
            gc.collect()

            backup_path = _backup_database_file(db_path, LEGACY_DB_VERSION)
            conn = duckdb.connect(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id INTEGER PRIMARY KEY,
                    account_name VARCHAR,
                    account_type VARCHAR,
                    currency VARCHAR DEFAULT 'EUR',
                    created_at DATE DEFAULT CURRENT_DATE,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            _create_schema_tables(conn)
            conn.execute(f"ATTACH '{backup_path}' AS old")
            migrate_v0_0_to_0_1(conn, source_alias='old')
            conn.execute("DETACH old")
            return conn

        _migrate_cash_transactions_to_account_ids(conn)
        _migrate_account_balances_to_account_ids(conn)
        set_db_version(conn, CURRENT_DB_VERSION)
        return conn

    raise RuntimeError(
        f"Unsupported database version '{current_version}'. "
        f"Expected '{CURRENT_DB_VERSION}' or legacy '{LEGACY_DB_VERSION}'."
    )
