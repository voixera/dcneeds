import os
import signal
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
LOG_DIR = BASE_DIR / "log"
_LOG_LOCK = threading.Lock()
BOT_SCRIPTS = [
    "bot.py",
    "drxfarm.py",
    "drxmusic.py",
    "drxrolemanage.py",
    "drxsrvrmanage.py",
    "key_bot.py",
    "payment_bot.py",
    "script_panel.py",
]


def _daily_log_path(now: datetime | None = None) -> Path:
    when = now or datetime.now()
    return LOG_DIR / f"{when.strftime('%d.%m.%Y')}Use.log"


def _append_daily_log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = _daily_log_path()
    with _LOG_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", errors="replace", newline="") as handle:
            handle.write(message)


def _log_launcher(message: str) -> None:
    stamped = f"{datetime.now().strftime('%H:%M:%S')} [launcher] {message}\n"
    sys.stdout.write(stamped)
    sys.stdout.flush()
    _append_daily_log(stamped)


def load_env_file(env_path: Path) -> dict[str, str]:
    env_updates: dict[str, str] = {}
    if not env_path.exists():
        return env_updates

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_updates[key.strip()] = value.strip().strip('"').strip("'")
    return env_updates


def stream_output(name: str, pipe, target_stream) -> None:
    try:
        for line in iter(pipe.readline, ""):
            stamped = f"{datetime.now().strftime('%H:%M:%S')} [{name}] {line}"
            target_stream.write(stamped)
            target_stream.flush()
            _append_daily_log(stamped)
    finally:
        pipe.close()


def terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    try:
        process.terminate()
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    env = os.environ.copy()
    env.update(load_env_file(ENV_FILE))

    processes: list[tuple[str, subprocess.Popen]] = []
    output_threads: list[threading.Thread] = []

    for script_name in BOT_SCRIPTS:
        script_path = BASE_DIR / script_name
        if not script_path.exists():
            _log_launcher(f"Skip, file tidak ditemukan: {script_name}")
            continue

        process = subprocess.Popen(
            [sys.executable, "-u", str(script_path)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        processes.append((script_name, process))

        stdout_thread = threading.Thread(
            target=stream_output,
            args=(script_name, process.stdout, sys.stdout),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=stream_output,
            args=(f"{script_name}:ERR", process.stderr, sys.stderr),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        output_threads.extend([stdout_thread, stderr_thread])
        _log_launcher(f"Menjalankan {script_name} (PID {process.pid})")

    if not processes:
        _log_launcher("Tidak ada bot yang dijalankan.")
        return 1

    try:
        while True:
            failed = []
            running = 0
            for script_name, process in processes:
                return_code = process.poll()
                if return_code is None:
                    running += 1
                    continue
                if return_code != 0:
                    failed.append((script_name, return_code))

            if failed:
                for script_name, return_code in failed:
                    _log_launcher(f"{script_name} berhenti dengan exit code {return_code}")
                return 1

            if running == 0:
                _log_launcher("Semua bot sudah berhenti.")
                return 0

            threading.Event().wait(1)
    except KeyboardInterrupt:
        _log_launcher("Menghentikan semua bot...")
        for _, process in processes:
            if os.name == "nt" and process.poll() is None:
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    terminate_process(process)
            else:
                terminate_process(process)

        for _, process in processes:
            if process.poll() is None:
                terminate_process(process)

        return 0
    finally:
        for thread in output_threads:
            thread.join(timeout=1)


if __name__ == "__main__":
    raise SystemExit(main())
