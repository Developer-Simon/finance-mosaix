# Data Flow

Finance mosaix uses DuckDB as a shared backend for both the CLI and the dashboard. This page explains how data enters the system and how it is reused across the project.

## Import path

1. Excel data is imported through the CLI or the dashboard Excel Import page.
2. The importer normalizes wide-format transaction sheets into the long DuckDB schema.
3. Transactions, account balances, stock snapshots, goods valuations, and interest changes are stored in `finance.duckdb`.

## Storage model

The database contains tables for:
- cash transactions
- account balances
- stock positions and portfolio snapshots
- goods valuations
- interest balance changes

## Shared backend

Both the CLI and the dashboard read from the same database file:
- the CLI is best for scripted imports, queries, and automation
- the dashboard is best for interactive visualization, reporting, and data review

Changes made through one interface are visible to the other because both use the same DuckDB database.

## Reporting path

Query helpers generate reports and chart inputs from the stored data. The dashboard uses these helpers to render:
- summary metrics
- trend charts
- account history
- category drill-downs
- portfolio and goods valuation views

## Maintenance path

The dashboard includes tools for data maintenance, such as:
- account balance snapshot cleanup
- data normalization
- merge and organizer workflows

The CLI can be used to inspect the schema, run quick queries, and validate imported data before review.
