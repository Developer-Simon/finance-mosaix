---
layout: page
title: CLI Reference
---

# CLI Reference

The Finance mosaix command-line interface is a lightweight way to manage your DuckDB database, import Excel transactions, and run quick finance queries without opening a browser.

## When to use the CLI

Use the CLI when you want:
- fast import workflows for recurring Excel sheets
- scripted or automated data tasks
- quick balance, spending, or search reports from the terminal
- a lightweight interface without the Streamlit dashboard

## Starting the CLI

From the project root:

```bash
python src/finance_cli.py --help
```

If the package is installed, you may also use the installed entry point instead of the local script.

The project public name is Finance mosaix, while the internal package/project directory conventions are `FinanceMosaix` and `finance-mosaix/`.

## Commands

### Initialize the database

```bash
python src/finance_cli.py --init
```

This creates the default DuckDB database file if it does not already exist.

### Import transactions from Excel

```bash
python src/finance_cli.py --import path/to/file.xlsx
```

The importer will:
- show available sheets
- let you select a sheet
- create or select an account
- normalize wide Excel data into the long database schema
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
python src/finance_cli.py --search "rent"
```

### View database schema

```bash
python src/finance_cli.py --schema
```

### Normalize goods valuations

```bash
python src/finance_cli.py --normalize goods
```

## Database file

The default database file is `finance.duckdb` in the project root. You can use the `--db` option to pass a custom location.

## Recommended CLI workflow

1. Initialize the database.
2. Import Excel transaction sheets.
3. Validate balances and spending with quick commands.
4. Open the dashboard to review charts and metrics after import.

For interactive dashboard workflows, see [Dashboard](dashboard.md).

## CLI vs Dashboard

Use the CLI when you prefer scripts, automation, and terminal reports.
Use the dashboard when you want interactive visual exploration and guided data maintenance.
