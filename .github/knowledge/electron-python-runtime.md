# Finance Mosaix Electron App

This note covers the Electron desktop shell and the bundled Python runtime used by
Finance Mosaix. Commands and the variants are described in `electron/README.md`.

## Electron app overview

The `electron/` directory contains the desktop shell. It starts the Streamlit dashboard
from `src/finance_mosaix/dashboard/app.py` on a free local port and shows it in an
Electron window. The shell is split into modules under `electron/src/`:

- `resolve-runtime.js`: picks the Python interpreter (see below)
- `python-locator.js`, `venv-manager.js`: system Python and the managed venv
- `server-process.js`: starts, health-checks and stops the Streamlit process
- `legacy-notice.js`, `smoke.js`, `chrome.js`, `i18n.js`: legacy data notice, `--smoke`
  check, window chrome and texts

## Packaged Python runtime

The full variant ships a relocatable CPython built by
[python-build-standalone](https://github.com/astral-sh/python-build-standalone). The
slim variant has no interpreter and uses a system Python.

### How the runtime is built

`npm run build:runtime` (in `electron/`) runs `runtime/build-runtime.js`:

1. The archive for the current platform is read from `runtime/runtime.lock.json`
   (release, Python version, asset name and SHA-256 per target). It is downloaded to
   `build/cache/` if it is not cached yet.
2. The SHA-256 sum is checked, both for a cached archive and for a new download. A
   cached archive with a wrong sum is deleted and downloaded again.
3. The archive is unpacked into `build/python/`. On Windows the script uses the
   system `tar.exe`, because the GNU tar of Git Bash reads `D:\...` as a remote host.
4. `build/requirements.txt` is installed into the runtime with `pip`. The environment
   variables `PYTHONNOUSERSITE=1` and the `PYTHONPATH` and `PYTHONHOME` variables are
   removed for this step, so the build does not depend on the user's Python.
5. An import check runs for streamlit, duckdb, pandas, numpy, openpyxl, altair,
   matplotlib and seaborn.

`build/requirements.txt` comes from `scripts/write_requirements.py` through
`npm run build:requirements`.

The packaged app finds the runtime at `<resources>/python/bin/python3` (Windows:
`python.exe`). Packaging copies `electron/build/python/` there (`electron-builder.full.yml`).

### Updating the Python version

Change `release`, `python` and the `asset` and `sha256` values of each target in
`runtime/runtime.lock.json`. Each target needs its own SHA-256 sum. Then run
`npm run build:runtime` on each platform that is packaged.

### Repairing a broken runtime

If the bundled interpreter fails to start or the dashboard does not import its
dependencies, delete `electron/build/python/` and run `npm run build:runtime` again.

For the system Python variant, use Tools → Reinstall Python environment in the app, or
delete the `venv/` folder in the data folder. The next start recreates it.

### Interpreter order at runtime

`src/resolve-runtime.js` checks, in this order: `FINANCE_MOSAIX_PYTHON`, the development
venv `.venv` (not packaged), the bundled runtime, then the system Python with the managed
venv in the user data folder. The order is also described in `electron/README.md`.

## Electron version resolution in CI

### Symptom

When the version sync step (`electron/sync_version.js`, `npm run sync-version`) runs
without a tag, it can report:

- `Electron package version updated -> 0.0.0`

This causes Electron package metadata to regress to a placeholder version.

### Root cause pattern

`electron/sync_version.js` asks Python for `finance_mosaix.core.version.get_canonical_version()`.
If `setuptools_scm` is not available in the Python environment used by the workflow,
SCM-based version resolution may fail and fallback selection becomes critical.

In this project, installed package metadata may temporarily be `0.0.0` in build
flows, so treating installed metadata as a strong source can produce an incorrect
Electron version.

### Guardrails implemented

1. `finance_mosaix/core/version.py` treats installed metadata version `0.0.0` as a placeholder
   and ignores it.
2. `finance_mosaix/core/version.py` reads `[tool.setuptools_scm].fallback_version` from
   `pyproject.toml` and uses it before installed package metadata.
3. In `.github/workflows/electron.yml` a release build takes the version from the tag
   (`npm version`, `electron/VERSION`). Other runs call `npm run sync-version` after
   `actions/checkout` with `fetch-depth: 0`.
4. `test/test_version_sync.py` includes regression tests for this exact fallback
   scenario.

### Current canonical fallback order

`get_canonical_version()` resolves version in this order:

1. `project.version` in `pyproject.toml` (if static versioning is used later)
2. `setuptools_scm.get_version(...)`
3. root `VERSION` file
4. `electron/VERSION`
5. `[tool.setuptools_scm].fallback_version`
6. installed package metadata (except `0.0.0` placeholder)

### CI checklist for future changes

- Keep `actions/checkout` with `fetch-depth: 0` so tags/history are available.
- Make sure the Python used by `npm run sync-version` can resolve the version in the
  workflow (`.github/workflows/electron.yml`).
- If versioning behavior changes, run `pytest test/test_version_sync.py -q`.
- Do not rely on installed package metadata alone for canonical versioning.
