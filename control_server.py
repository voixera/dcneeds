import json
import os
import signal
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from env_loader import load_env_file


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "log"
BOT_SCRIPTS = [
    "bot.py",
    "drxassistant.py",
    "drxfarm.py",
    "drxmusic.py",
    "drxrolemanage.py",
    "drxsrvrmanage.py",
    "key_bot.py",
    "payment_bot.py",
    "script_panel.py",
]

load_env_file()

CONTROL_API_TOKEN = (os.getenv("CONTROL_API_TOKEN") or "").strip()
CONTROL_HOST = (os.getenv("CONTROL_HOST") or "").strip()
if not CONTROL_HOST:
    CONTROL_HOST = "0.0.0.0" if os.getenv("RENDER") else "127.0.0.1"
CONTROL_PORT = int((os.getenv("CONTROL_PORT") or os.getenv("PORT") or "8787").strip() or "8787")
CONTROL_AUTOSTART_BOTS = (os.getenv("CONTROL_AUTOSTART_BOTS") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}

_LOCK = threading.Lock()
_LOG_LOCK = threading.Lock()
_PROCESSES: dict[str, subprocess.Popen] = {}


def _daily_log_path(now: datetime | None = None) -> Path:
    when = now or datetime.now()
    return LOG_DIR / f"{when.strftime('%d.%m.%Y')}Control.log"


def _append_log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamped = f"{datetime.now().strftime('%H:%M:%S')} [control] {message}\n"
    with _LOG_LOCK:
        with _daily_log_path().open("a", encoding="utf-8", errors="replace") as handle:
            handle.write(stamped)
    sys.stdout.write(stamped)
    sys.stdout.flush()


def _bot_id(script_name: str) -> str:
    return script_name.removesuffix(".py")


def _script_name(bot_id: str) -> str | None:
    candidate = f"{bot_id}.py"
    return candidate if candidate in BOT_SCRIPTS else None


def _public_bot_state(script_name: str) -> dict:
    process = _PROCESSES.get(script_name)
    running = process is not None and process.poll() is None
    return {
        "id": _bot_id(script_name),
        "script": script_name,
        "running": running,
        "pid": process.pid if running else None,
        "exitCode": None if running or process is None else process.poll(),
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
    }


def _stream_output(script_name: str, pipe, is_error: bool = False) -> None:
    try:
        for line in iter(pipe.readline, ""):
            level = "ERR" if is_error else "OUT"
            with _LOG_LOCK:
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                with _daily_log_path().open("a", encoding="utf-8", errors="replace") as handle:
                    handle.write(f"{datetime.now().strftime('%H:%M:%S')} [{script_name}:{level}] {line}")
    finally:
        pipe.close()


def _clean_finished_locked() -> None:
    for script_name, process in list(_PROCESSES.items()):
        if process.poll() is not None:
            _PROCESSES.pop(script_name, None)


def start_bot(script_name: str) -> dict:
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        raise ValueError(f"Script tidak ditemukan: {script_name}")

    with _LOCK:
        _clean_finished_locked()
        existing = _PROCESSES.get(script_name)
        if existing is not None and existing.poll() is None:
            return _public_bot_state(script_name)

        env = os.environ.copy()
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
        _PROCESSES[script_name] = process

        threading.Thread(target=_stream_output, args=(script_name, process.stdout, False), daemon=True).start()
        threading.Thread(target=_stream_output, args=(script_name, process.stderr, True), daemon=True).start()
        _append_log(f"Start {script_name} (PID {process.pid})")
        return _public_bot_state(script_name)


def stop_bot(script_name: str) -> dict:
    with _LOCK:
        process = _PROCESSES.get(script_name)
        if process is None or process.poll() is not None:
            _PROCESSES.pop(script_name, None)
            return _public_bot_state(script_name)

        _append_log(f"Stop {script_name} (PID {process.pid})")
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
            process.wait(timeout=10)
        except Exception:
            process.kill()
            process.wait(timeout=5)

        _PROCESSES.pop(script_name, None)
        return _public_bot_state(script_name)


def status_payload() -> dict:
    with _LOCK:
        _clean_finished_locked()
        bots = [_public_bot_state(script_name) for script_name in BOT_SCRIPTS]
    running_count = sum(1 for bot in bots if bot["running"])
    return {
        "ok": True,
        "bots": bots,
        "runningCount": running_count,
        "totalCount": len(bots),
        "serverTime": datetime.now().isoformat(timespec="seconds"),
    }


class ControlHandler(BaseHTTPRequestHandler):
    server_version = "DrxControl/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not CONTROL_API_TOKEN:
            self._send_json(500, {"ok": False, "error": "CONTROL_API_TOKEN belum di-set di .env"})
            return False
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {CONTROL_API_TOKEN}":
            self._send_json(401, {"ok": False, "error": "Unauthorized"})
            return False
        return True

    def do_OPTIONS(self) -> None:
        self._send_json(200, {"ok": True})

    def do_GET(self) -> None:
        if not self._authorized():
            return
        path = urlparse(self.path).path
        if path == "/api/status":
            self._send_json(200, status_payload())
            return
        self._send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        if not self._authorized():
            return
        path = urlparse(self.path).path.strip("/")
        parts = path.split("/")

        try:
            if parts == ["api", "all", "start"]:
                bots = [start_bot(script_name) for script_name in BOT_SCRIPTS]
                self._send_json(200, {"ok": True, "bots": bots})
                return
            if parts == ["api", "all", "stop"]:
                bots = [stop_bot(script_name) for script_name in BOT_SCRIPTS]
                self._send_json(200, {"ok": True, "bots": bots})
                return
            if len(parts) == 4 and parts[:2] == ["api", "bots"]:
                script_name = _script_name(parts[2])
                action = parts[3]
                if script_name is None:
                    self._send_json(404, {"ok": False, "error": "Bot tidak ditemukan"})
                    return
                if action == "start":
                    self._send_json(200, {"ok": True, "bot": start_bot(script_name)})
                    return
                if action == "stop":
                    self._send_json(200, {"ok": True, "bot": stop_bot(script_name)})
                    return
                if action == "restart":
                    stop_bot(script_name)
                    self._send_json(200, {"ok": True, "bot": start_bot(script_name)})
                    return
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})
            return

        self._send_json(404, {"ok": False, "error": "Not found"})


def main() -> int:
    if not CONTROL_API_TOKEN:
        raise RuntimeError("CONTROL_API_TOKEN belum di-set di .env")

    server = ThreadingHTTPServer((CONTROL_HOST, CONTROL_PORT), ControlHandler)
    _append_log(f"Control API listening on http://{CONTROL_HOST}:{CONTROL_PORT}")
    if CONTROL_AUTOSTART_BOTS:
        _append_log("CONTROL_AUTOSTART_BOTS aktif, menjalankan semua bot")
        for script_name in BOT_SCRIPTS:
            try:
                start_bot(script_name)
            except Exception as exc:
                _append_log(f"Gagal autostart {script_name}: {exc}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _append_log("Shutdown requested")
    finally:
        for script_name in list(_PROCESSES):
            stop_bot(script_name)
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
