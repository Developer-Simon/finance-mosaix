# Usage

Finance mosaix supports two complementary application surfaces: a command-line interface and a browser-based dashboard.

## CLI

Finance mosaix provides a CLI for fast import workflows, database inspection, and terminal-based reporting.

### Naming and folders

Finance mosaix is the public brand. The internal package name is `FinanceMosaix`, and the project lives in the `finance-mosaix/` directory.

From the project root, use the installed CLI entry point or the local module in `src/finance_cli.py`.

### Initialize the database

```bash
python src/finance_cli.py --init
```

### Import transactions from Excel

```bash
python src/finance_cli.py --import path/to/file.xlsx
```

The importer will:
- show available sheets
- let you select a sheet
- create or select an account
- normalize wide Excel data to long format
- insert rows into the DuckDB database

### Show account balances

```bash
python src/finance_cli.py --balance
```

### Show spending for the last N days

```bash
python src/finance_cli.py --spending 30
```

### Search transactions

```bash
python src/finance_cli.py --search rent
```

### View schema

```bash
python src/finance_cli.py --schema
```

### Normalize goods valuations

```bash
python src/finance_cli.py --normalize goods
```

For a full CLI reference, see [CLI Reference](cli.md).

## Dashboard

The dashboard is a Streamlit application for interactive charts, metrics, and data maintenance.

Start the dashboard with:

```bash
python start_dashboard.py
```

The dashboard provides:
- data import helpers
- account and transaction summaries
- charts and metrics
- asset and goods valuation views

For a full dashboard walkthrough, see [Dashboard](dashboard.md).

## Database file

The default database file is `finance.duckdb` in the project root. You can override it with the `--db` option in the CLI.
