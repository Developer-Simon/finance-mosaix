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

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

Windows:

```powershell
python -m venv .venv
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

The desktop app shows the dashboard in its own window. Packages for Linux, macOS and Windows are attached to each [GitHub release](https://github.com/Developer-Simon/finance-mosaix/releases).

### Variants

Each release has two variants:

- **full**: contains a Python interpreter, so no Python has to be installed. Linux: AppImage and Flatpak bundle. macOS: dmg. Windows: installer.
- **slim**: contains no interpreter. The system needs Python 3.11 or newer with the `venv` module. On first start the app creates its own environment and installs the dependencies into it. Linux: AppImage. macOS: dmg. Windows: installer.

Both variants are named `Finance Mosaix-<version>-<arch>-<variant>.<ext>`. The file `SHA256SUMS.txt` in each release lists the checksums of all files.

### Unsigned packages

The packages are not signed yet. The operating system warns on the first start:

- **macOS**: right-click (or Control-click) the app and choose Open, then confirm. On recent macOS versions this may be blocked. In that case open System Settings → Privacy & Security and click Open Anyway.
- **Windows**: SmartScreen shows "Windows protected your PC". Click "More info", then "Run anyway".

### Data folder

The database (`finance.duckdb`) and the settings are stored in a folder of the app that is not inside the program folder:

| System  | Folder |
|---------|--------|
| Linux   | `~/.config/Finance Mosaix` |
| macOS   | `~/Library/Application Support/Finance Mosaix` |
| Windows | `%APPDATA%\Finance Mosaix` |
| Flatpak | `~/.var/app/io.github.developer_simon.finance_mosaix/config/Finance Mosaix` |

To open the folder, press Alt to show the menu and choose Tools → Open data folder.

An earlier Windows build kept its database in the program folder, `finance-mosaix-electron\resources\finance.duckdb`. The app shows a notice on the first start when it finds this file. To keep the data, close the app and copy `finance.duckdb` into `%APPDATA%\Finance Mosaix\`.

### Development run

Before running Electron on Linux, create and activate the project `.venv` at the repository root and install the Python dependencies:

Linux/macOS:

```bash
cd /path/to/finance-mosaix
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
cd electron
npm install
npm start
```

Windows:

```powershell
cd \path\to\finance-mosaix
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install .
cd electron
npm install
npm start
```

This launches the Streamlit dashboard in an embedded desktop window using the local Python environment. Without a `.venv`, the app uses the bundled runtime from `npm run build:runtime` if it exists, and otherwise a system Python.

### Building packages and releases

The build commands, the Flatpak requirements and the release workflow are described in `electron/README.md`.
