"""Build a self-contained, relocatable Python runtime for the packaged Electron app.

On Windows this downloads the official "embeddable" CPython distribution, which
ships its own interpreter DLL and standard library, so the resulting
``python-runtime`` folder has no dependency on any Python installation on the
build machine or the end user's machine. A regular ``venv`` (the previous
approach) only contains a thin ``python.exe`` stub plus ``pyvenv.cfg`` that
points back at the base interpreter used to create it - it is NOT relocatable,
which is why the packaged app's python.exe stopped responding once moved to a
system (or even the same system, after the config-rewrite step blanked out the
only valid "home" path) where that base interpreter path no longer resolved.

On other platforms we fall back to a plain venv (still requires a system
Python at runtime) since no official embeddable distribution exists there.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import venv
import zipfile

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path(__file__).resolve().parent / "python-runtime"
PYTHON_VERSION = "3.11.9"
EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/"
    f"python-{PYTHON_VERSION}-embed-amd64.zip"
)
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"


def build_windows_runtime() -> None:
    if RUNTIME_DIR.exists():
        shutil.rmtree(RUNTIME_DIR)
    RUNTIME_DIR.mkdir(parents=True)

    zip_path = RUNTIME_DIR.parent / f"python-embed-{PYTHON_VERSION}.zip"
    print(f"Downloading embeddable Python {PYTHON_VERSION} from {EMBED_URL}")
    urllib.request.urlretrieve(EMBED_URL, zip_path)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(RUNTIME_DIR)
    finally:
        zip_path.unlink(missing_ok=True)

    python_executable = RUNTIME_DIR / "python.exe"

    # The embeddable distribution disables site-packages handling by default
    # (via the python*._pth file). Re-enable it so pip-installed packages are
    # importable.
    pth_candidates = list(RUNTIME_DIR.glob("python*._pth"))
    if not pth_candidates:
        raise RuntimeError("Could not locate the ._pth file in the embeddable Python distribution")
    pth_file = pth_candidates[0]
    lines = pth_file.read_text(encoding="utf-8").splitlines()
    new_lines = []
    has_site_packages_entry = False
    for line in lines:
        stripped = line.strip()
        if stripped == "#import site":
            new_lines.append("import site")
        else:
            new_lines.append(line)
        if stripped == "Lib\\site-packages":
            has_site_packages_entry = True
    if not has_site_packages_entry:
        new_lines.append("Lib\\site-packages")
    pth_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # Bootstrap pip (the embeddable distribution ships without pip/ensurepip).
    get_pip_path = RUNTIME_DIR / "get-pip.py"
    print(f"Downloading get-pip.py from {GET_PIP_URL}")
    urllib.request.urlretrieve(GET_PIP_URL, get_pip_path)
    try:
        subprocess.run(
            [str(python_executable), str(get_pip_path), "--no-warn-script-location"],
            check=True,
            cwd=str(RUNTIME_DIR),
        )
    finally:
        get_pip_path.unlink(missing_ok=True)

    subprocess.run(
        [str(python_executable), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        check=True,
    )
    # Install a real (non-editable) copy of the project into the runtime's
    # site-packages. An editable install (`pip install -e`) only writes a
    # path finder that points back at this ROOT checkout, which does not
    # exist on a machine the packaged app is later moved to.
    subprocess.run(
        [str(python_executable), "-m", "pip", "install", "--no-cache-dir", str(ROOT)],
        check=True,
    )

    print(f"Self-contained Python runtime ready at {RUNTIME_DIR}")


def build_posix_venv_runtime() -> None:
    if RUNTIME_DIR.exists():
        shutil.rmtree(RUNTIME_DIR)

    print(f"Creating Python runtime at {RUNTIME_DIR}")
    venv.EnvBuilder(with_pip=True).create(RUNTIME_DIR)

    python_executable = RUNTIME_DIR / "bin" / "python"
    subprocess.run(
        [str(python_executable), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        check=True,
    )
    # Non-editable install: keeps the runtime relocatable (see note above).
    subprocess.run(
        [str(python_executable), "-m", "pip", "install", "--no-cache-dir", str(ROOT)],
        check=True,
    )

    print(
        "Python runtime bundle created at "
        f"{RUNTIME_DIR} (note: this venv still requires a compatible system "
        "Python installation to be present at runtime; only the Windows "
        "embeddable build is fully self-contained)."
    )


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        build_windows_runtime()
    else:
        build_posix_venv_runtime()
