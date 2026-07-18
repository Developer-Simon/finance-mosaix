# Electron Packaged Python Runtime

The Electron desktop wrapper (`electron/`) bundles a private Python runtime so the
Streamlit dashboard can run on a machine without a system-wide Python install. This
runtime is built by [`electron/build_python_runtime.py`](../electron/build_python_runtime.py)
into `electron/python-runtime` (gitignored, regenerated locally and in CI — never
committed).

## History: why the old approach broke

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
   hanging / exiting immediately without useful output whenever Electron tried to
   launch Streamlit.
2. **Editable installs aren't relocatable.** `pip install -e ROOT` writes a path finder
   pointing at the absolute dev checkout path. That path doesn't exist once the runtime
   is packaged and moved to another machine.

Even without those bugs, a regular venv is always tied to whatever base Python produced
it — it can never be a truly portable, drop-in runtime for an end user's machine.

## Current approach

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

## Repairing a broken runtime

If the packaged app's `python.exe` hangs or fails to start (e.g. after moving the app,
or after `pyvenv.cfg` corruption from an older build), rebuild the runtime from
scratch:

```powershell
cd electron
Remove-Item -Recurse -Force python-runtime
python build_python_runtime.py
npm start
```
