"""
DuckDB Schema Setup for Personal Finance Database
Pool-specific schema: cash transactions, stock positions, goods valuations,
and interest balance changes each live in their own dedicated table so each
pool can be inspected, debugged, and queried in isolation.
"""

import duckdb
import os
from pathlib import Path

try:
    from .db_migrate import migrate_database, get_db_version, set_db_version, CURRENT_DB_VERSION
except ImportError:
    from db_migrate import migrate_database, get_db_version, set_db_version, CURRENT_DB_VERSION


class DuckDBConnectionProxy:
    """Proxy connection that reopens automatically if DuckDB reports a closed connection."""

    def __init__(self, db_path: str = "finance.duckdb", force_migration: bool = False):
        self.db_path = db_path
        self.force_migration = force_migration
        self._conn = self._connect()

    def _connect(self):
        db_existed = Path(self.db_path).exists()
        conn = duckdb.connect(self.db_path)
        if db_existed:
            current_version = get_db_version(conn)
            if self.force_migration or current_version != CURRENT_DB_VERSION:
                conn = migrate_database(conn, self.db_path)
        return conn

    def _ensure_open(self):
        if self._conn is None:
            self._conn = self._connect()
        return self._conn

    def execute(self, *args, **kwargs):
        conn = self._ensure_open()
        try:
            return conn.execute(*args, **kwargs)
        except duckdb.ConnectionException as exc:
            if "Connection already closed" in str(exc):
                self._conn = self._connect()
                return self._conn.execute(*args, **kwargs)
            raise

    def commit(self):
        return self._ensure_open().commit()

    def close(self):
        if self._conn is not None:
            return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._ensure_open(), name)


def init_database(db_path: str = "finance.duckdb", force_migration: bool = False) -> duckdb.DuckDBPyConnection:
    """Initialize DuckDB database with all required tables."""

    # Ensure directory exists (skip for in-memory databases).
    if db_path not in (":memory:", ""):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db_existed = Path(db_path).exists()
    conn = duckdb.connect(db_path)
    db_path_display = os.path.abspath(db_path) if db_path != ":memory:" else ":memory:"

    if db_existed:
        current_version = get_db_version(conn)
        if force_migration or current_version != CURRENT_DB_VERSION:
            if force_migration:
                print(f"[OK] Existing database found at {db_path_display}, version {current_version}. Forced migration to {CURRENT_DB_VERSION}.")
            else:
                print(f"[OK] Existing database found at {db_path_display}, version {current_version}. Migrating to {CURRENT_DB_VERSION}.")
            conn = migrate_database(conn, db_path)
            new_version = get_db_version(conn)
            print(f"[OK] Database migrated to version {new_version}.")
        else:
            print(f"[OK] Existing database found at {db_path_display}, version {current_version}. No migration required.")
    else:
        print(f"[OK] Database not found at {db_path_display}. Creating new database.")
        set_db_version(conn, CURRENT_DB_VERSION)
        print(f"[OK] Database initialized at {db_path_display} with version {CURRENT_DB_VERSION}.")

    # 1. ACCOUNTS TABLE - Cash-pool accounts (bank/broker accounts referenced by cash transactions).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY,
            account_name VARCHAR,
            account_type VARCHAR,  -- 'bank', 'savings', 'investment'
            currency VARCHAR DEFAULT 'EUR',
            created_at DATE DEFAULT CURRENT_DATE,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)

    # 2. MAIN_CATEGORIES TABLE - Top-level cash category groupings.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS main_categories (
            main_category_id INTEGER PRIMARY KEY,
            main_category_name VARCHAR UNIQUE
        )
    """)

    # 3. SUB_CATEGORIES TABLE - Secondary category groupings under main categories.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sub_categories (
            sub_category_id INTEGER PRIMARY KEY,
            main_category_id INTEGER,
            sub_category_name VARCHAR,
            UNIQUE(main_category_id, sub_category_name),
            FOREIGN KEY (main_category_id) REFERENCES main_categories(main_category_id)
        )
    """)

    # 4. CATEGORIES TABLE - Normalized combinations of main/sub categories.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY,
            main_category_id INTEGER,
            sub_category_id INTEGER,
            category_name VARCHAR UNIQUE,
            category_type VARCHAR,  -- 'income', 'expense', 'transfer'
            color_code VARCHAR,
            FOREIGN KEY (main_category_id) REFERENCES main_categories(main_category_id),
            FOREIGN KEY (sub_category_id) REFERENCES sub_categories(sub_category_id)
        )
    """)

    # 5. CASH_TRANSACTIONS TABLE - Long format (one category per row) for the cash pool.
    conn.execute("""
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
    """)

    # 4. STOCK_POSITIONS TABLE - Monthly stock/crypto depot position snapshots.
    conn.execute("""
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
    """)

    # 5. GOODS_VALUATIONS TABLE - Monthly goods/asset depreciation valuations (append-only log).
    conn.execute("""
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
    """)

    # 6. INTEREST_BALANCE_CHANGES TABLE - Monthly Festgeld/interest account balance deltas.
    conn.execute("""
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
    """)

    # 7. ACCOUNT_BALANCES TABLE - Snapshot monitoring of account totals.
    conn.execute("""
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
    """)

    if not db_existed:
        set_db_version(conn, CURRENT_DB_VERSION)
        print(f"[OK] Database metadata set to version {CURRENT_DB_VERSION}.")

    print(f"[OK] Database started, location at {db_path_display}")

    return conn


def get_connection(db_path: str = "finance.duckdb", force_migration: bool = False):
    """Get connection to existing database and apply migrations if needed."""
    return DuckDBConnectionProxy(db_path=db_path, force_migration=force_migration)


def show_schema(db_path: str = "finance.duckdb"):
    """Display the current database schema."""
    conn = get_connection(db_path)
    
    print("\n" + "="*60)
    print("DATABASE SCHEMA")
    print("="*60)
    
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchall()
    
    for (table_name,) in tables:
        print(f"\n[TABLE] {table_name.upper()}")
        print("-" * 60)
        columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        for col in columns:
            cid, name, type_, notnull, dflt_value, pk = col
            pk_marker = " [PK]" if pk else ""
            print(f"  - {name:<20} {type_:<15}{pk_marker}")


if __name__ == "__main__":
    conn = init_database("finance.duckdb")
    show_schema("finance.duckdb")
    conn.close()
