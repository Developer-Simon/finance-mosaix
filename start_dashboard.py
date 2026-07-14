"""Process manager for the Finance mosaix dashboard app.

Usage:
    python start_dashboard.py start
    python start_dashboard.py stop
    python start_dashboard.py restart
    python start_dashboard.py status

If run without a command, this script starts the dashboard.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import List, Optional, Tuple

PID_FILE_NAME = ".dashboard.pid"


def get_python_executable() -> Path:
    root = Path(__file__).resolve().parent
    venv_path = root / ".venv"
    if os.name == "nt":
        candidate = venv_path / "Scripts" / "python.exe"
    else:
        candidate = venv_path / "bin" / "python"

    if candidate.exists():
        return candidate

    return Path(sys.executable)


def get_workspace_root() -> Path:
    return Path(__file__).resolve().parent


def get_app_path() -> Path:
    return get_workspace_root() / "dashboard" / "app.py"


def get_pid_path() -> Path:
    return get_workspace_root() / PID_FILE_NAME


def read_pid() -> Optional[int]:
    pid_path = get_pid_path()
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text().strip())
    except (ValueError, OSError):
        return None


def write_pid(pid: int) -> None:
    get_pid_path().write_text(str(pid))


def remove_pid_file() -> None:
    pid_path = get_pid_path()
    if pid_path.exists():
        pid_path.unlink(missing_ok=True)


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def get_streamlit_command_args(
    app_path: Path,
    host: str,
    port: int,
    enableCORS: bool,
    enableXsrfProtection: bool,
) -> List[str]:
    args = [
        str(app_path),
        "--server.headless",
        "true",
        "--server.address",
        host,
        "--server.port",
        str(port),
    ]

    if not enableCORS:
        args.extend(["--server.enableCORS", "false"])

    if not enableXsrfProtection:
        args.extend(["--server.enableXsrfProtection", "false"])

    return args


def start_dashboard(
    host: str = "localhost",
    port: int = 8501,
    browser: bool = True,
    enable_cors: bool = True,
    enable_xsrf: bool = True,
    foreground: bool = True,
) -> int:
    app_path = get_app_path()
    if not app_path.exists():
        print(f"ERROR: Streamlit app not found at {app_path}")
        return 1

    existing_pid = read_pid()
    if existing_pid and is_process_running(existing_pid):
        print(f"Dashboard already running with PID {existing_pid}")
        if browser:
            webbrowser.open(f"http://{host}:{port}")
        return 0

    if existing_pid:
        remove_pid_file()

    python_executable = get_python_executable()
    command = [
        str(python_executable),
        "-m",
        "streamlit",
        "run",
    ] + get_streamlit_command_args(
        app_path,
        host,
        port,
        enable_cors,
        enable_xsrf,
    )

    print(f"Using Python executable: {python_executable}")
    if foreground:
        print("Starting Streamlit dashboard with output visible in this terminal...")
        process = None
        try:
            process = subprocess.Popen(command)
        except FileNotFoundError:
            print("ERROR: Streamlit is not installed in the selected Python environment.")
            print("Install it with: python -m pip install streamlit")
            return 1
        except OSError as exc:
            print(f"ERROR: Failed to launch dashboard: {exc}")
            return 1

        write_pid(process.pid)
        print(f"Dashboard started with PID {process.pid}")
        url = f"http://{host}:{port}"
        print(f"Opening {url} in the default browser...")
        if browser:
            try:
                webbrowser.open(url)
            except OSError as exc:
                print(f"WARNING: Could not open browser automatically: {exc}")

        try:
            return_code = process.wait()
            return return_code if return_code is not None else 0
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, stopping Streamlit...")
            try:
                process.terminate()
            except OSError:
                pass
            process.wait()
            return 0
        finally:
            remove_pid_file()
    else:
        print("Starting Streamlit dashboard in the background...")
        kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True

        try:
            process = subprocess.Popen(command, **kwargs)
        except FileNotFoundError:
            print("ERROR: Streamlit is not installed in the selected Python environment.")
            print("Install it with: python -m pip install streamlit")
            return 1
        except OSError as exc:
            print(f"ERROR: Failed to launch dashboard: {exc}")
            return 1

        write_pid(process.pid)
        print(f"Dashboard started with PID {process.pid}")
        url = f"http://{host}:{port}"
        print(f"Opening {url} in the default browser...")
        if browser:
            try:
                webbrowser.open(url)
            except OSError as exc:
                print(f"WARNING: Could not open browser automatically: {exc}")
        return 0


def prompt_bool(question: str, default: bool) -> bool:
    default_text = "Y/n" if default else "y/N"
    while True:
        response = input(f"{question} [{default_text}]: ").strip().lower()
        if not response:
            return default
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Please answer y or n.")


def interactive_start_settings() -> Tuple[str, int, bool, bool, bool, bool]:
    print("\nConfigure dashboard server settings:\n")
    host = input("Server host [localhost]: ").strip() or "localhost"
    while True:
        port_value = input("Server port [8501]: ").strip() or "8501"
        try:
            port = int(port_value)
            break
        except ValueError:
            print("Please enter a valid numeric port.")

    browser = prompt_bool("Open dashboard in the default browser?", True)
    enable_cors = prompt_bool("Enable Streamlit CORS support?", True)
    enable_xsrf = prompt_bool("Enable Streamlit XSRF protection?", True)
    foreground = prompt_bool("Show Streamlit server output in this terminal?", False)

    print("\nSelected Streamlit server options:")
    print(f"  host: {host}")
    print(f"  port: {port}")
    print(f"  browser auto-open: {browser}")
    print(f"  enable CORS: {enable_cors}")
    print(f"  enable XSRF: {enable_xsrf}")
    print(f"  show output: {foreground}\n")

    return host, port, browser, enable_cors, enable_xsrf, foreground


def stop_dashboard() -> int:
    pid = read_pid()
    if pid is None:
        print("No dashboard PID file found. Is the dashboard running?")
        return 1
    if not is_process_running(pid):
        print(f"Dashboard process {pid} is not running.")
        remove_pid_file()
        return 0

    print(f"Stopping dashboard process {pid}...")
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        print(f"ERROR: Could not stop dashboard process: {exc}")
        return 1

    for _ in range(10):
        if not is_process_running(pid):
            break
        time.sleep(0.5)

    if is_process_running(pid):
        print(f"WARNING: dashboard process {pid} is still running.")
        return 1

    remove_pid_file()
    print("Dashboard stopped.")
    return 0


def status_dashboard() -> int:
    pid = read_pid()
    if pid is None:
        print("Dashboard is not running.")
        return 1
    if is_process_running(pid):
        print(f"Dashboard is running with PID {pid}.")
        return 0
    print(f"Dashboard PID file exists but process {pid} is not running.")
    return 1


def restart_dashboard() -> int:
    stop_dashboard()
    return start_dashboard()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage the Finance dashboard process."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["start", "stop", "restart", "status"],
        default="start",
        help="Action to perform.",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host address for Streamlit.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Server port for Streamlit.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the default browser automatically.",
    )
    parser.add_argument(
        "--disable-cors",
        action="store_true",
        help="Disable Streamlit CORS support.",
    )
    parser.add_argument(
        "--disable-xsrf",
        action="store_true",
        help="Disable Streamlit XSRF protection.",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run the dashboard in the background and hide console output.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for dashboard host/port/browser/CORS/XSRF settings.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "start":
        if args.interactive:
            host, port, browser, enable_cors, enable_xsrf, foreground = interactive_start_settings()
        else:
            host = args.host
            port = args.port
            browser = not args.no_browser
            enable_cors = not args.disable_cors
            enable_xsrf = not args.disable_xsrf
            foreground = not args.background

        return start_dashboard(
            host=host,
            port=port,
            browser=browser,
            enable_cors=enable_cors,
            enable_xsrf=enable_xsrf,
            foreground=foreground,
        )
    if args.command == "stop":
        return stop_dashboard()
    if args.command == "restart":
        return restart_dashboard()
    if args.command == "status":
        return status_dashboard()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
