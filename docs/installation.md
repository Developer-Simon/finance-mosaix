# Installation

## Prerequisites

- Python 3.11+ (or compatible Python 3.x)
- `pip` installed
- Optional: a virtual environment for isolation

## Setup

From the `finance-mosaix/` directory:

```bash
.\.venv\Scripts\activate
pip install -r requirements.txt
```

This will create `finance.duckdb` in the `finance-mosaix/` directory unless you pass a custom `--db` path.

## Run the dashboard

Start the Streamlit dashboard from `finance-mosaix/`:

```bash
python start_dashboard.py
```

Then open the local URL provided by Streamlit in your browser.
