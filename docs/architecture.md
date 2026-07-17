# Architecture

Finance mosaix is organized into three main areas:

> The project lives in the `finance-mosaix/` directory.

- `src/`: core finance logic and database management
- `dashboard/`: Streamlit-based UI and visualization helpers
- `test/`: automated tests for import and query behavior

## Core modules

### `src/db_schema.py`

Initializes the DuckDB schema and provides connection helpers.

### `src/import_transactions.py`

Contains the Excel import workflow. It reads wide-format transaction sheets, normalizes categories, and inserts transactions into the DuckDB database.

### `src/query_finance.py`

Provides query helpers for balances, spending, search, and goods normalization.

### `src/goods_depreciation.py`

Implements asset depreciation calculations and valuation updates.

## Dashboard components

The `dashboard/` package uses Streamlit to render views and charts.

- `dashboard/app.py`: main dashboard application
- `dashboard/charts.py` and `dashboard/charts_pyplot.py`: chart rendering
- `dashboard/import.py`: import UX and file handling
- `dashboard/data_creator.py`, `data_editor.py`, `data_organizer.py`: data manipulation views

## CLI vs Dashboard

Finance mosaix exposes two separate application surfaces:

- CLI: lightweight command-line workflows for data import, database inspection, and quick queries.
- Dashboard: interactive visualization, report exploration, and data maintenance.

Both interfaces share the same DuckDB backend, so data imported in the CLI can be reviewed in the dashboard, and changes made through the dashboard are visible to the CLI.

## Data flow

1. User imports Excel data.
2. The importer normalizes wide transaction sheets into the long database schema.
3. Transactions are stored in `finance.duckdb`.
4. Query helpers read from the database for reports, summaries, and asset valuation.
5. The dashboard visualizes the same data and provides interactive controls.

## Testing and packaging

- `tool.pytest.ini_options` is configured to run tests from `test/`.
- `pythonpath = src` ensures the test suite can import the core modules correctly.
- `pyproject.toml` captures runtime and optional dependency groups for test, dev, and docs workflows.

## Mainline branch

The repository uses `master` as the mainline branch for contributions and pull requests.
