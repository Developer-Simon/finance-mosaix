# Finance Mosaix Electron App

This note covers the Electron desktop wrapper and the packaged Python runtime used by
Finance Mosaix.

## Electron app overview

The `electron/` directory contains the desktop wrapper that launches the Streamlit
dashboard from `dashboard/app.py` inside a native Electron window.

### Local development

1. Open a terminal at the project root.
2. Install Node dependencies inside `electron/`:

```bash
cd electron
npm install
```

3. Start the Electron app:

```bash
npm start
```

The app launches the Streamlit dashboard and embeds it in a desktop window.

### Packaging

From the `electron/` directory:

```bash
npm run dist
```

The build is configured for Windows with `nsis` and includes the project files
required to launch the dashboard.

### Icon regeneration

If the packaged icon needs to be rebuilt from the SVG source, run:

```bash
npm run generate-icon
```

This generates `docs/img/favicon.ico` from `docs/img/favicon.svg` at 256x256.

### Notes

- The Electron wrapper looks for Python either from the host environment or via the
  `PYTHON_EXECUTABLE` environment variable.
- For a bundled runtime, use:

```bash
npm run build-runtime
```

- `npm run dist` now builds the embedded Python runtime automatically before packaging.
- Generated Electron folder artifacts include `python-runtime/`, `dist/`, and `build_log.txt`.
- To clean the Electron folder before a fresh build, remove `electron/node_modules/`,
  `electron/python-runtime/`, `electron/dist/`, and `electron/build_log.txt`.
- `electron/build_python_runtime.py` is the canonical runtime builder; the shell script
  `electron/build-python-runtime.sh` may be removed if you want a smaller folder.

## Electron Packaged Python Runtime

The Electron desktop wrapper (`electron/`) bundles a private Python runtime so the
Streamlit dashboard can run on a machine without a system-wide Python install. This
runtime is built by [`electron/build_python_runtime.py`](../electron/build_python_runtime.py)
into `electron/python-runtime` (gitignored, regenerated locally and in CI — never
committed).

### Why the previous runtime approach broke

The original script created the runtime with a plain `venv.EnvBuilder`, then rewrote
`pyvenv.cfg` to try to make it relocatable, and installed the project with
`pip install -e .`.

This was broken for two independent reasons:

1. **A stock Windows venv is not self-contained.** `Scripts/python.exe` is only a thin
   stub — it has no interpreter DLL or standard library of its own. It relies entirely
   on `pyvenv.cfg`'s `home = ...` value to locate the *original* base Python
   installation's DLL and stdlib. The old script rewrote `home` to point at the venv's
   own `Scripts` folder, which doesn't contain the stdlib/DLLs either — so
   `python.exe` could no longer initialize. In practice this showed up as `python.exe`
   hanging or exiting immediately without useful output whenever Electron tried to
   launch Streamlit.
2. **Editable installs aren't relocatable.** `pip install -e ROOT` writes a path finder
   pointing at the absolute dev checkout path. That path doesn't exist once the runtime
   is packaged and moved to another machine.

Even without those bugs, a regular venv is always tied to whatever base Python produced
it — it can never be a truly portable, drop-in runtime for an end user's machine.

### Current approach

On Windows, `build_python_runtime.py` now:

1. Downloads the official **embeddable CPython distribution**
   (`python.org/ftp/python/<version>/python-<version>-embed-amd64.zip`), which ships
   its own interpreter DLL and standard library — no dependency on any Python
   installation on the build machine or the end user's machine.
2. Enables `site-packages` support by editing the shipped `python311._pth` file
   (uncommenting `import site` and adding `Lib\site-packages`).
3. Bootstraps `pip` via `get-pip.py`.
4. Installs the project with a normal (non-editable) `pip install ROOT` so the package
   files are copied into the runtime's own `site-packages`, not linked back to the dev
   checkout.

The result is a fully self-contained `python-runtime` folder: no external Python
dependency, and no absolute paths back to the build machine. It is genuinely
relocatable, which is what the packaged Electron installer (built by
`npm run dist` / `.github/workflows/electron-package.yml`) requires to work on a fresh
system.

`python.exe` now lives directly at `python-runtime/python.exe` (embeddable layout)
rather than `python-runtime/Scripts/python.exe` (venv layout). `electron/main.js`'s
`getPythonExecutable()` checks the new location first and falls back to the old
`Scripts/python.exe` path for backward compatibility with any previously built runtime.

For non-Windows platforms (no official embeddable distribution exists), the script
falls back to a plain venv via `build_posix_venv_runtime()` — this still requires a
compatible system Python to be present at runtime and is not fully self-contained.

### Repairing a broken runtime

If the packaged app's `python.exe` hangs or fails to start (e.g. after moving the app,
or after `pyvenv.cfg` corruption from an older build), rebuild the runtime from
scratch:

```powershell
cd electron
Remove-Item -Recurse -Force python-runtime
python build_python_runtime.py
npm start
```

## Electron Version Resolution In CI

### Symptom

During `npm run dist`, the version sync step (`electron/sync_version.js`) can report:

- `Electron package version updated -> 0.0.0`

This causes Electron package metadata to regress to a placeholder version.

### Root cause pattern

`electron/sync_version.js` asks Python for `src.version.get_canonical_version()`.
If `setuptools_scm` is not available in the Python environment used by the workflow,
SCM-based version resolution may fail and fallback selection becomes critical.

In this project, installed package metadata may temporarily be `0.0.0` in build
flows, so treating installed metadata as a strong source can produce an incorrect
Electron version.

### Guardrails implemented

1. `src/version.py` now treats installed metadata version `0.0.0` as a placeholder
   and ignores it.
2. `src/version.py` now reads `[tool.setuptools_scm].fallback_version` from
   `pyproject.toml` and uses it before installed package metadata.
3. `.github/workflows/electron-package.yml` now installs `setuptools_scm` in both
   Windows and Linux packaging jobs.
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
- Ensure `setuptools_scm` is installed before `npm run dist`.
- If versioning behavior changes, run `pytest test/test_version_sync.py -q`.
- Do not rely on installed package metadata alone for canonical versioning.
