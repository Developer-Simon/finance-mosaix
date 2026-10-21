# Electron shell for Finance Mosaix

The shell starts the Streamlit dashboard (`src/finance_mosaix/dashboard/app.py`) on a free local port and shows it in an Electron window. The dashboard and the Python package are not changed by the shell. The shell lives in the `electron/` folder.

## Development

```bash
cd electron
npm install
npm start          # starts the app from source
npm test           # unit tests (node --test)
```

`npm start` runs `scripts/start.js`, which removes `ELECTRON_RUN_AS_NODE` from the environment before Electron starts. Some environments set this variable, and Electron would then run as plain Node.js. Further arguments are passed to the app, e.g. `npm start -- --smoke`.

In development the dashboard uses the Python environment described under Runtime. The database stays in the repository root unless `FINANCE_MOSAIX_DATA_DIR` is set.

## Runtime

At startup `src/resolve-runtime.js` picks the interpreter for the dashboard. The first matching step wins:

1. **`FINANCE_MOSAIX_PYTHON`**: the interpreter named in this environment variable is used as it is. No venv is created.
2. **Development venv** (not packaged): `.venv` in the repository root, i.e. `.venv/bin/python` on Linux and macOS, `.venv\Scripts\python.exe` on Windows.
3. **Bundled runtime**: `python/` in the app resources of a packaged build, `electron/build/python/` in development. It is created by `npm run build:runtime`.
4. **System Python**: the first of `python3` and `python` (on Windows `py -3`, `python`, `python3`) with version 3.11 or newer that also has the `venv` and `ensurepip` modules. The shell creates a venv in `venv/` in the data folder and installs `requirements.txt` into it. The requirements are installed again when the app version or the requirements change. A change of the Python minor version recreates the venv.

If no step matches, the app shows "No usable Python found." together with the rejected candidates. Tools → Reinstall Python environment repeats step 4 with a fresh install. It is only enabled when the system Python is used.

## Variants

Both variants are built with electron-builder on each platform.

- **slim** (`electron-builder.yml`): contains no interpreter. The app needs a system Python as described in step 4. Built as AppImage (Linux), dmg (macOS) and NSIS installer (Windows).
- **full** (`electron-builder.full.yml`, extends the slim configuration): adds the bundled interpreter from `build/python/`. Built as AppImage and Flatpak bundle (Linux), dmg (macOS) and NSIS installer (Windows).

The bundled interpreter is built with:

```bash
npm run build:runtime
```

This command writes `build/requirements.txt` from `pyproject.toml` (`npm run build:requirements`) and then runs `runtime/build-runtime.js`. The script downloads the python-build-standalone archive for the current platform, pinned in `runtime/runtime.lock.json` (CPython 3.13.16, release 20261013). It checks the SHA-256 sum, unpacks the archive into `build/python/`, installs the requirements into it and checks that the main dependencies can be imported. The archives are cached in `build/cache/`. Supported targets are `linux-x64`, `darwin-arm64`, `darwin-x64` and `win32-x64`.

Packages:

```bash
npm run dist:slim   # -> dist/slim/
npm run dist:full   # -> dist/full/  (run npm run build:runtime first)
```

The artifact names follow the pattern `Finance Mosaix-<version>-<arch>-<variant>.<ext>`, for example `Finance Mosaix-0.2.0-x86_64-full.AppImage`. On Linux the full variant also builds a Flatpak bundle. This needs `flatpak-builder` and the Flathub runtimes `org.freedesktop.Platform` and `org.freedesktop.Sdk` in version 26.08, and `org.electronjs.Electron2.BaseApp` in version 26.08. The configuration is in `electron-builder.yml` and `electron-builder.full.yml`. The `dist/` and `build/` folders are not checked in.

The dmg and NSIS packages are built on macOS and Windows respectively. The packages are not signed yet.

## Data folder

In a packaged app the database (`finance.duckdb`), `settings.json`, the sample database and the managed venv are stored in the Electron user data folder. Tools → Open data folder opens it.

| System  | Folder |
|---------|--------|
| Linux   | `~/.config/Finance Mosaix` |
| macOS   | `~/Library/Application Support/Finance Mosaix` |
| Windows | `%APPDATA%\Finance Mosaix` |
| Flatpak | `~/.var/app/io.github.developer_simon.finance_mosaix/config/Finance Mosaix` |

The Flatpak ID is derived from the `appId` by electron-builder, which replaces hyphens with underscores.

### Data of earlier Windows builds

Earlier Windows builds installed to a folder named `finance-mosaix-electron` and kept the database in its `resources` folder, for example `%LOCALAPPDATA%\Programs\finance-mosaix-electron\resources\finance.duckdb`. When the new data folder has no database and such a file exists, the app shows a one-time notice. To keep the data, close the app and copy `finance.duckdb` into `%APPDATA%\Finance Mosaix\`.

## Smoke test

`--smoke` starts the server, requests `/_stcore/health` and `/`, and quits the app. The exit code is 0 when both requests return 200 and the page contains a `<title` element. Otherwise the exit code is 1. No dialogs appear, and messages go to the console.

```bash
npm start -- --smoke                                   # from source

# full, without Python in PATH (the interpreter comes from the package)
xvfb-run -a bash -c 'env -i HOME="$HOME" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" dist/full/linux-unpacked/finance-mosaix --smoke --no-sandbox'

# slim, with the Python of the machine: exit code 1 without a usable Python
xvfb-run -a dist/slim/linux-unpacked/finance-mosaix --smoke --no-sandbox
```

On macOS and Windows the CI runs the packaged executable with `--smoke` in a clean environment (`env -i`), as the full variant above. The workflow is the reference for these commands.

## Releases (CI)

The workflow `.github/workflows/electron.yml` builds the installers. It runs on pushes to `master` that touch `electron/`, `src/` or `pyproject.toml`, on pull requests with the same paths, and on manual runs. These runs only upload workflow artifacts.

Releases come from `.github/workflows/release-please.yml`. On a push to `master` release-please updates its release pull request. When a release is created, the workflow calls `electron.yml` with the new tag, which then:

1. runs the Python and Electron tests on `ubuntu-latest`
2. builds on `ubuntu-latest` (x64), `macos-latest` (arm64), `macos-15-intel` (x64) and `windows-latest` (x64). The version is taken from the tag into `electron/package.json` and `electron/VERSION`, then `npm run build:runtime`, `npm run dist:full` and `npm run dist:slim` run
3. smoke-tests the full variant without Python in PATH on Linux, macOS and Windows, and the slim variant on Linux with the Python of the runner
4. collects the installers in one job, writes `SHA256SUMS.txt`, creates a build provenance attestation for all files (Sigstore, `actions/attest-build-provenance`) and uploads them to the GitHub release of the tag

The release contains the AppImages (full and slim), the Flatpak bundle, the dmg files and the NSIS installers, together with `SHA256SUMS.txt`.

To check that a downloaded file was built by this repository:

```bash
gh attestation verify "Finance Mosaix-0.2.0-x86_64-full.AppImage" --repo Developer-Simon/finance-mosaix
sha256sum -c SHA256SUMS.txt
```

The packages are not signed. On first launch macOS needs Right-click → Open, and Windows shows SmartScreen. See `docs/installation.md` for the steps.
