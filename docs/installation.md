---
layout: page
title: Installation
tags: [installation, setup, getting-started]
---

# Installation

## Prerequisites

- Python 3.11+ (or compatible Python 3.x)
- `pip` installed
- Optional: a virtual environment for isolation

## Setup

From the `finance-mosaix/` directory:

```bash
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install .
```

This will create `finance.duckdb` in the `finance-mosaix/` directory unless you pass a custom `--db` path.

### Run the dashboard

Start the Streamlit dashboard from `finance-mosaix/`:

```bash
python start_dashboard.py
```

Then open the local URL provided by Streamlit in your browser.

## Electron desktop app

A desktop wrapper is available under `electron/`.

### Development run

```bash
cd electron
npm install
npm start
```

This launches the Streamlit dashboard in an embedded desktop window using the local Python environment. If you want to use the packaged Python runtime, first build it with:

```bash
cd electron
npm run build-runtime
```

### Packaging for Windows

```bash
cd electron
npm run dist
```

The build is configured to include the dashboard sources and the bundled Python runtime.

### Packaging workflow

A GitHub Actions workflow is available at `.github/workflows/electron-package.yml`.
It builds the Python runtime, installs Node dependencies, and runs `npm run dist` on Windows.

