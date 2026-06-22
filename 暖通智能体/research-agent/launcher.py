import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
PORT = 8501
URL = f"http://localhost:{PORT}"
IDLE_SECONDS = 90
START_TIMEOUT = 45
LOG_FILE = APP_DIR / "launcher.log"


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {message}\n")


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.6)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def run_text(command) -> str:
    try:
        return subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return ""


def streamlit_pid_on_port(port: int) -> int:
    output = run_text(["netstat", "-ano"])
    for line in output.splitlines():
        if f":{port}" not in line or "LISTENING" not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        command = run_text(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").CommandLine",
            ]
        )
        if "streamlit" in command.lower() and "app.py" in command.lower():
            return pid
    return 0


def established_connection_count(port: int) -> int:
    output = run_text(["netstat", "-ano"])
    count = 0
    for line in output.splitlines():
        if f":{port}" in line and "ESTABLISHED" in line:
            count += 1
    return count


def start_streamlit():
    log("Starting Streamlit.")
    log_file = (APP_DIR / "streamlit-runtime.log").open("a", encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        str(PORT),
        "--server.address",
        "localhost",
        "--browser.gatherUsageStats",
        "false",
    ]
    return subprocess.Popen(
        command,
        cwd=str(APP_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def wait_for_streamlit() -> bool:
    deadline = time.time() + START_TIMEOUT
    while time.time() < deadline:
        if port_is_open(PORT):
            return True
        time.sleep(0.5)
    return False


def open_edge() -> None:
    log("Opening Edge.")
    subprocess.Popen(
        ["cmd", "/c", "start", "", "msedge", URL],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def stop_streamlit(process, existing_pid: int) -> None:
    log("Stopping Streamlit.")
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
            return
        except subprocess.TimeoutExpired:
            process.kill()
            return
    if existing_pid:
        subprocess.run(
            ["taskkill", "/PID", str(existing_pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def monitor_until_idle(process, existing_pid: int) -> None:
    log("Monitoring browser connections.")
    idle_started = None
    time.sleep(12)
    while True:
        if process and process.poll() is not None:
            log("Streamlit process exited before idle timeout.")
            return
        connections = established_connection_count(PORT)
        if connections > 0:
            idle_started = None
        else:
            if idle_started is None:
                idle_started = time.time()
            elif time.time() - idle_started >= IDLE_SECONDS:
                stop_streamlit(process, existing_pid)
                return
        time.sleep(5)


def main() -> None:
    log("Launcher started.")
    process = None
    existing_pid = streamlit_pid_on_port(PORT)
    if existing_pid or port_is_open(PORT):
        log(f"Streamlit already appears to be running. pid={existing_pid}")
    else:
        process = start_streamlit()
        if not wait_for_streamlit():
            log("Streamlit failed to start in time.")
            return
    open_edge()
    monitor_until_idle(process, existing_pid)
    log("Launcher exited.")


if __name__ == "__main__":
    main()
