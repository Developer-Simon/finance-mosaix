# Finance Dashboard

A lightweight Streamlit dashboard for exploring and visualising personal finance data from the Finance Database.

---

## Quick Start

1. Create and activate a virtual environment (recommended).

Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the dashboard:

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## What You Get

- Interactive visualisations for spending, income, balances and trends
- Date range and Top‑N category filtering in the sidebar
- Cached, fast database queries for responsive charts
- Option to view and export underlying data

---

## Project Layout

Files in this folder:

- `app.py` — Streamlit application (UI + sidebar)
- `charts.py` — Chart and plotting functions
- `data.py` — Cached query helpers
- `database.py` — Database access utilities (if present)
- `requirements.txt` — Python dependencies

---

## Available Visualisations

- Spending Distribution (pie + horizontal bar)
- Account Balances
- Income vs Expenses
- Transaction Frequency
- Average Transaction Size
- Asset Depreciation projection
- Balance Timeline (historical balances)

Each chart queries the database and renders a matplotlib figure suitable for Streamlit.

---

## New Account Balances Support

- `Account Balances` are now backed by the new `account_balances` pool.
- The dashboard supports monitoring snapshots and derived account balance calculations from cash history.
- Organizer actions include:
  - `Calculate from Cash` to create a calculated account balance entry.
  - merge account names and merge balance dates for `account_balances` rows.
- Legacy Pyplot balance charts remain unchanged and continue to use existing cash-based balances.

---

## Sidebar Controls

Common controls exposed in the sidebar:

- Visualization selector
- Start / End date
- Top categories (slider)
- Minimum transaction amount
- Account selection (optional)
- Show source data (table)

Changing controls refreshes the active visualization.

---

## Extending the Dashboard

To add a new visualization:

1. Add a plotting function in `charts.py` (e.g. `monthly_cashflow_chart(queries)`).
2. Add the option to the sidebar select box in `app.py`.
3. Call your plotting function from the selection branch.

---

## Requirements

Suggested `requirements.txt` content:

```
streamlit>=1.35
pandas>=2.2
numpy>=1.26
matplotlib>=3.8
seaborn>=0.13
sqlalchemy>=2.0
openpyxl>=3.1
```

Add `psycopg2-binary` for PostgreSQL or `pymysql` for MySQL as needed.

---

## Troubleshooting

- If no charts appear, verify the database connection and that transactions are imported.
- If you get import errors, ensure the virtual environment is activated and run `pip install -r requirements.txt`.

Run Streamlit using `python -m streamlit run app.py` if the `streamlit` command is not found.

---

## Next Steps

- Tune the charts in `charts.py` for your dataset.
- Add CSV / image export buttons in the UI as needed.

---

## License

This project is intended for educational and personal use. Adapt and extend as desired.
