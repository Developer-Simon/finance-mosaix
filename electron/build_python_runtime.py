from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path(__file__).resolve().parent / "python-runtime"

if RUNTIME_DIR.exists():
    shutil.rmtree(RUNTIME_DIR)

print(f"Creating Python runtime at {RUNTIME_DIR}")
venv.EnvBuilder(with_pip=True).create(RUNTIME_DIR)

if sys.platform.startswith("win"):
    python_executable = RUNTIME_DIR / "Scripts" / "python.exe"
else:
    python_executable = RUNTIME_DIR / "bin" / "python"

print(f"Using runtime Python executable: {python_executable}")
subprocess.run([str(python_executable), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
subprocess.run([str(python_executable), "-m", "pip", "install", "--no-cache-dir", "-e", str(ROOT)], check=True)
print("Python runtime build complete.")
