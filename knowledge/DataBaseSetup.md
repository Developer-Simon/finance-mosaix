# Finance Database Setup - Finance mosaix

## Updated: 2026-07-06

### Current Architecture (Authoritative)
- Schema is pool-specific, no backward compatibility layer.
- Core tables: `accounts`, `categories`, `cash_transactions`, `stock_positions`, `goods_valuations`, `interest_balance_changes`, `account_balances`.
- `account_balances` stores snapshot monitoring rows, with `entry_type` values like `monitoring` and `calculated`.
- Legacy tables (`transactions`, `stocks`, `goods`, `balances_snapshot`) are no longer the target model.

### Importer Contract
- Entry point: `FinanceImporter.import_sheet(...)`.
- Returns dict contract with keys: `status`, `sheet_name`, `account_name`, `transaction_date`, `pools`, `warnings`, `errors`.
- `pools` includes: `cash`, `stocks`, `goods`, `interest` with per-pool `present`, `rows_parsed`, `inserted` (+ `deltas` for interest).
- `account_balances` import is deferred; monitoring snapshots are expected to come from sheet sections labeled `Kontostandskontrolle` in future work.

### Excel Parsing Rules (Sample.xlsx)
- Cash pool:
  - Header row with `Nr.` + `Bezeichnung` and two-level categories.
  - First col = row number, second = description.
  - Last two columns = balance + account.
  - Bilanz/Summe/footer rows are excluded.
- Stocks pool:
  - Section marker near `Depot / Wallet`.
  - Keep real position rows only (must have `Nr.` and name); exclude footer/placeholder rows.
- Goods pool:
  - Section marker near `Sachwerte / Abschreibung`.
  - Keep real item rows only; exclude baseline/summary rows.
- Interest pool:
  - Side panel marker `Festgeld` inside/near stock section.
  - Read account labels + balances; compute delta vs previous month.
- Account balance monitoring snapshots:
  - Expected from `Kontostandskontrolle` sheet sections when supported.
  - Values are stored in `account_balances` with `entry_type`.

### Known Good Validation (Import/Sample.xlsx, sheet Juni 2026)
- Cash: rows_parsed=62, inserted=65, SUM(amount)=-208.93 (matches sheet Bilanz).
- Stocks: inserted=19.
- Goods: inserted=8.
- Interest: inserted=3.

### Query Layer Mapping
- Cash analytics/search/balances read from `cash_transactions` + `categories` + `accounts`.
- New normalized cash category hierarchy data is available through `main_categories` and `sub_categories`, linked from `cash_transactions.main_category_id` and `cash_transactions.sub_category_id`.
- Stock views read from `stock_positions`.
- Goods views read from `goods_valuations`.
- Interest views read from `interest_balance_changes`.
- Account balance snapshots are stored in `account_balances` and can be queried for monitoring or derived calculations.

### Dashboard Mapping
- Existing cash views remain: spending, balances, income/expenses, frequency, average, timeline.
- Added pool views: stock positions/history, goods valuation/history, interest balances/history.
- New account balance organizer support: derive `account_balances` snapshots from cash transaction history and merge account names / dates.
- Future cash reporting may use `main_categories` and `sub_categories` to offer split hierarchies for category drilldowns.

### Testing Notes
- Tests are adapted to pool-specific tables and dict contract.
- Windows DuckDB locking: close setup seed connection before launching subprocess CLI tests.
- Passing command: `python -m unittest discover -s test -v` from `finance-mosaix`.

### Operating Instructions
1. If schema changed, recreate `finance.duckdb` and re-import workbook.
2. Import with explicit date per sheet month for stable interest deltas.
3. Trust importer summary + dict contract first when debugging parsing issues.
4. Compare cash SUM(amount) to sheet Bilanz row as primary correctness check.
5. Update all references (queries/dashboard/tests) directly when schema changes; do not keep compatibility aliases.
