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

# Rewrite pyvenv.cfg so the bundled runtime is not tightly coupled to the build machine Python path.
pyvenv_cfg = RUNTIME_DIR / "pyvenv.cfg"
if pyvenv_cfg.exists():
    text = pyvenv_cfg.read_text(encoding="utf-8")
    runtime_python = RUNTIME_DIR / "Scripts" / "python.exe" if sys.platform.startswith("win") else RUNTIME_DIR / "bin" / "python"
    runtime_home = RUNTIME_DIR / "Scripts" if sys.platform.startswith("win") else RUNTIME_DIR / "bin"
    runtime_command = f"{runtime_python} -m venv --without-scm-ignore-files {RUNTIME_DIR}"

    lines = text.splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("home = "):
            new_lines.append(f"home = {runtime_home}")
        elif line.startswith("executable = "):
            new_lines.append(f"executable = {runtime_python}")
        elif line.startswith("command = "):
            new_lines.append(f"command = {runtime_command}")
        else:
            new_lines.append(line)

    pyvenv_cfg.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Rewrote pyvenv.cfg for relocatable runtime: {pyvenv_cfg}")

print("Python runtime build complete.")
