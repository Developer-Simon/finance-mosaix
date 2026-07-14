# Database Migration Knowledge

## Overview
This note captures the key issue encountered during DuckDB schema migration for Finance mosaix, the root cause, the fix applied, and guidance for future migrations.

## Problem Summary
- Legacy `finance.duckdb` databases contained schema version `0.0` and data in old table formats.
- Migration code was intended to:
  - back up the legacy database,
  - create the new normalized schema in the target database,
  - copy legacy rows into the new tables,
  - and set the new database version to `0.1`.
- The migration produced a valid new database file, but the migrated DB was empty except for the metadata and schema.

## Root Cause
- `_table_exists()` relied on `information_schema.tables` for all schemas, which failed for attached legacy schema aliases like `old`.
- As a result, legacy table existence checks returned false during migration, and copy functions skipped row transfer.
- Additionally, `get_connection()` in `src/db_schema.py` ignored the migrated connection returned by `migrate_database()`, which could cause inconsistent behavior when migration replaced the connection.

## Fix Applied
1. Updated `src/db_migrate.py`:
   - Added fallback logic in `_table_exists()` to support attached schemas via `SHOW TABLES FROM <schema>` and `PRAGMA table_info(<schema>.<table>)`.
   - Ensured attached legacy aliases such as `old` are correctly recognized during migration.
2. Updated `src/db_schema.py`:
   - Changed `get_connection()` to return `migrate_database(conn, db_path)` instead of discarding the migrated connection.

## Validation
- Verified that a copied legacy DB is migrated and preserves the following counts:
  - `accounts`
  - `cash_transactions`
  - `categories`
  - `main_categories`
  - `sub_categories`
  - `goods_valuations`
  - `interest_balance_changes`
  - `stock_positions`
  - `account_balances` (zero if legacy DB had none)
- Confirmed the migrated database version is set to `0.1`.

## New 0.1 Category Hierarchy
- Added normalized cash category tables:
  - `main_categories` stores the top-level portion of slash-delimited categories.
  - `sub_categories` stores the remaining tail after the first slash.
- `categories` becomes the normalized combo table and stores `main_category_id` + `sub_category_id`.
- `cash_transactions` now references `category_id` only, not direct `main_category_id`/`sub_category_id` columns.
- During migration, legacy `categories.category_name` values are split on the first `/`:
  - left of the first slash → `main_category_name`
  - right of the first slash (including repeated slashes) → `sub_category_name`
- If no slash exists, the entry maps to a main category only and leaves `sub_category_id` NULL.

## Gotchas
- DuckDB attached schemas like `ATTACH '<path>' AS old` do not always expose tables through `information_schema.tables` for the attached alias. Use `SHOW TABLES FROM <alias>` or `PRAGMA table_info(<alias>.<table>)` to detect legacy tables reliably.
- Never copy `cash_transactions` into the new schema before normalizing `categories`. Because DuckDB enforces foreign keys immediately, inserting `cash_transactions` rows before `categories` rows have `main_category_id`/`sub_category_id` set can trigger a constraint violation when those category rows are later updated.
- If the migration process closes and reopens the database file (for backup/restore), make sure the code returns the reopened connection. Otherwise, callers may continue using a stale connection and observe inconsistent schema state.
- Keep the new schema relationship clear: `cash_transactions.category_id` references `categories.category_id`, and only `categories` links to `main_categories`/`sub_categories`.

## Future Migration Guidance
- Always validate attached schema queries when using `ATTACH '<path>' AS <alias>`.
- Prefer schema-aware existence checks for attached schemas rather than relying only on `information_schema` views.
- Ensure the migration helper returns the final open connection if it may close and reopen the database file.
- Keep migration logic idempotent and preserve all legacy rows whenever schema conversion is intended.

## Lessons Learned
- DuckDB attached schemas may not expose rows in `information_schema.tables` under the attached alias; use `SHOW TABLES FROM <alias>` or `PRAGMA table_info(<alias>.<table>)`.
- Saving the migrated connection matters when migration reopened the file after backup.
- Backup before migration is important but the data copy step must preserve legacy rows, not just recreate schema.
