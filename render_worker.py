import os
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from env_loader import load_env_file


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "log"
BYPASSDELTA_DIR = BASE_DIR / "bypassdelta"
FIFA_WORLDCUP_DIR = BASE_DIR / "bot-fifa-worldcup"

PYTHON_BOT_SCRIPTS = [
    "bot.py",
    "drxfarm.py",
    "drxmusic.py",
    "drxrolemanage.py",
    "drxsrvrmanage.py",
    "key_bot.py",
    "payment_bot.py",
    "script_panel.py",
]
EXTRA_SERVICE_IDS = ["bypassdelta", "bot-fifa-worldcup"]
SERVICE_IDS = PYTHON_BOT_SCRIPTS + EXTRA_SERVICE_IDS

TOKEN_REQUIREMENTS = {
    "bot.py": ("DISCORD_BOT_TOKEN",),
    "drxfarm.py": ("DISCORD_FARM_TOKEN", "DISCORD_BOT_TOKEN", "DISCORD_MUSIC_TOKEN"),
    "drxmusic.py": ("DISCORD_MUSIC_TOKEN", "MUSIC_BOT_TOKEN", "DISCORD_BOT_TOKEN"),
    "drxrolemanage.py": ("DISCORD_BOT_TOKEN",),
    "drxsrvrmanage.py": ("DISCORD_SRVRMANAGE_TOKEN", "DISCORD_SERVERMANAGE_TOKEN", "DISCORD_BOT_TOKEN"),
    "key_bot.py": ("KEY_BOT_TOKEN",),
    "payment_bot.py": ("PAYMENT_BOT_TOKEN",),
    "script_panel.py": ("PANEL_BOT_TOKEN",),
    "bypassdelta": ("BYPASS_DISCORD_TOKEN",),
    "bot-fifa-worldcup": ("DISCORD_FIFA_TOKEN", "DISCORD_BOT_TOKEN"),
}

DATA_FILE_DEFAULTS = {
    "whitelist.json": "[]\n",
    "farm_whitelist.json": "[]\n",
    "keys.json": "{}\n",
    "payment_tickets.json": '{\n  "user_tickets": {},\n  "channels": {}\n}\n',
}
DATA_DIR_LINKS = {
    "bypassdelta/.tmp": "bypassdelta_tmp",
}


@dataclass(frozen=True)
class ServiceCommand:
    command: list[str]
    cwd: Path
    env: dict[str, str]

_LOG_LOCK = threading.Lock()
_STOP_EVENT = threading.Event()


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _daily_log_path(now: datetime | None = None) -> Path:
    when = now or datetime.now()
    return LOG_DIR / f"{when.strftime('%d.%m.%Y')}Launcher.log"


def _log(message: str) -> None:
    stamped = f"{datetime.now().strftime('%H:%M:%S')} [launcher] {message}\n"
    sys.stdout.write(stamped)
    sys.stdout.flush()
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _LOG_LOCK:
            with _daily_log_path().open("a", encoding="utf-8", errors="replace") as handle:
                handle.write(stamped)
    except Exception:
        pass


def _bot_id(script_name: str) -> str:
    return script_name.removesuffix(".py")


def _service_from_token(value: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.lower() == "all":
        return "all"
    if normalized.endswith(".py") and normalized in PYTHON_BOT_SCRIPTS:
        return normalized
    if normalized in SERVICE_IDS:
        return normalized

    candidate = f"{normalized}.py"
    if candidate in PYTHON_BOT_SCRIPTS:
        return candidate

    lowered = normalized.lower()
    if lowered in {"bypass", "bypassbot", "bypass_bot", "bypassdelta", "delta"}:
        return "bypassdelta"
    if lowered in {"fifa", "worldcup", "world-cup", "bot-fifa", "bot-fifa-worldcup"}:
        return "bot-fifa-worldcup"

    for script_name in PYTHON_BOT_SCRIPTS:
        if lowered in {script_name.lower(), _bot_id(script_name).lower()}:
            return script_name
    return None


def _enabled_services() -> list[str]:
    raw = os.getenv("ENABLED_BOTS", "all").strip()
    if not raw:
        raw = "all"

    selected: list[str] = []
    unknown: list[str] = []
    for part in raw.replace("\n", ",").split(","):
        service_id = _service_from_token(part)
        if service_id == "all":
            return SERVICE_IDS[:]
        if service_id is None:
            if part.strip():
                unknown.append(part.strip())
            continue
        if service_id not in selected:
            selected.append(service_id)

    if unknown:
        _log(f"ENABLED_BOTS berisi nama tidak dikenal: {', '.join(unknown)}")
    return selected


def _has_required_token(service_id: str) -> bool:
    keys = TOKEN_REQUIREMENTS.get(service_id, ())
    return any(os.getenv(key, "").strip() for key in keys)


def _prepare_persistent_directory(app_path: Path, disk_path: Path) -> None:
    disk_path.mkdir(parents=True, exist_ok=True)

    try:
        if app_path.exists() and not app_path.is_symlink() and app_path.is_dir():
            shutil.copytree(app_path, disk_path, dirs_exist_ok=True)
            shutil.rmtree(app_path)
        elif app_path.exists() or app_path.is_symlink():
            if app_path.resolve() == disk_path.resolve():
                return
            app_path.unlink()

        app_path.parent.mkdir(parents=True, exist_ok=True)
        app_path.symlink_to(disk_path, target_is_directory=True)
        _log(f"{app_path.relative_to(BASE_DIR)} diarahkan ke {disk_path}")
    except Exception as exc:
        _log(f"Gagal menyiapkan persistent directory {app_path}: {exc}")


def _prepare_persistent_data() -> None:
    raw_dir = os.getenv("PERSISTENT_DATA_DIR", "").strip()
    if not raw_dir:
        return

    data_dir = Path(raw_dir)
    if not data_dir.is_absolute():
        data_dir = BASE_DIR / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    for file_name, default_content in DATA_FILE_DEFAULTS.items():
        app_path = BASE_DIR / file_name
        disk_path = data_dir / file_name
        secret_path = Path("/etc/secrets") / file_name

        if not disk_path.exists():
            if secret_path.exists():
                shutil.copy2(secret_path, disk_path)
                _log(f"{file_name} disalin dari Secret File")
            elif app_path.exists() and not app_path.is_symlink():
                shutil.copy2(app_path, disk_path)
            else:
                disk_path.write_text(default_content, encoding="utf-8")

        try:
            if app_path.exists() or app_path.is_symlink():
                if app_path.resolve() == disk_path.resolve():
                    continue
                app_path.unlink()
            app_path.symlink_to(disk_path)
            _log(f"{file_name} diarahkan ke {disk_path}")
        except Exception as exc:
            _log(f"Gagal menyiapkan persistent data untuk {file_name}: {exc}")

    for relative_dir, disk_name in DATA_DIR_LINKS.items():
        _prepare_persistent_directory(BASE_DIR / relative_dir, data_dir / disk_name)


def _stream_output(script_name: str, pipe, is_error: bool = False) -> None:
    try:
        for line in iter(pipe.readline, ""):
            level = "ERR" if is_error else "OUT"
            text = f"{datetime.now().strftime('%H:%M:%S')} [{script_name}:{level}] {line}"
            target = sys.stderr if is_error else sys.stdout
            target.write(text)
            target.flush()
            try:
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                with _LOG_LOCK:
                    with _daily_log_path().open("a", encoding="utf-8", errors="replace") as handle:
                        handle.write(text)
            except Exception:
                pass
    finally:
        pipe.close()


def _npm_executable() -> str:
    if os.name == "nt":
        return shutil.which("npm.cmd") or shutil.which("npm") or "npm.cmd"
    return shutil.which("npm") or "npm"


def _build_service_command(service_id: str) -> ServiceCommand:
    env = os.environ.copy()

    if service_id in PYTHON_BOT_SCRIPTS:
        script_path = BASE_DIR / service_id
        return ServiceCommand(
            command=[sys.executable, "-u", str(script_path)],
            cwd=BASE_DIR,
            env=env,
        )

    if service_id == "bypassdelta":
        env.setdefault("NODE_ENV", "production" if os.getenv("RAILWAY_ENVIRONMENT") else "development")
        return ServiceCommand(
            command=[_npm_executable(), "start"],
            cwd=BYPASSDELTA_DIR,
            env=env,
        )

    if service_id == "bot-fifa-worldcup":
        env.setdefault("NODE_ENV", "production" if os.getenv("RAILWAY_ENVIRONMENT") else "development")
        persistent_data_dir = os.getenv("PERSISTENT_DATA_DIR", "").strip()
        if persistent_data_dir:
            data_dir = Path(persistent_data_dir)
            if not data_dir.is_absolute():
                data_dir = BASE_DIR / data_dir
            env.setdefault("FIFA_DB_PATH", str(data_dir / "bot-fifa-worldcup-db.json"))
        return ServiceCommand(
            command=[_npm_executable(), "start"],
            cwd=FIFA_WORLDCUP_DIR,
            env=env,
        )

    raise ValueError(f"Service tidak dikenal: {service_id}")


def _service_exists(service_id: str) -> bool:
    if service_id in PYTHON_BOT_SCRIPTS:
        return (BASE_DIR / service_id).exists()
    if service_id == "bypassdelta":
        return (BYPASSDELTA_DIR / "package.json").exists()
    if service_id == "bot-fifa-worldcup":
        return (FIFA_WORLDCUP_DIR / "package.json").exists()
    return False


def _start_service(service_id: str) -> subprocess.Popen:
    service_command = _build_service_command(service_id)
    process = subprocess.Popen(
        service_command.command,
        cwd=str(service_command.cwd),
        env=service_command.env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    threading.Thread(target=_stream_output, args=(service_id, process.stdout, False), daemon=True).start()
    threading.Thread(target=_stream_output, args=(service_id, process.stderr, True), daemon=True).start()
    _log(f"Menjalankan {service_id} (PID {process.pid})")
    return process


def _terminate_process(script_name: str, process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    _log(f"Menghentikan {script_name} (PID {process.pid})")
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()
        process.wait(timeout=20)
    except Exception:
        process.kill()
        process.wait(timeout=5)


def _handle_stop(signum, _frame) -> None:
    _log(f"Menerima signal {signum}, shutdown dimulai")
    _STOP_EVENT.set()


def main() -> int:
    load_env_file()
    _prepare_persistent_data()

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    skip_missing = _flag("SKIP_MISSING_BOT_TOKENS", default=True)
    restart_failed = _flag("RESTART_FAILED_BOTS", default=True)
    restart_delay = max(1, _int_env("RESTART_DELAY_SECONDS", 10))

    services = []
    for service_id in _enabled_services():
        if not _service_exists(service_id):
            _log(f"Skip, file tidak ditemukan: {service_id}")
            continue
        if skip_missing and not _has_required_token(service_id):
            required = " / ".join(TOKEN_REQUIREMENTS.get(service_id, ()))
            _log(f"Skip {service_id}, token belum diset ({required})")
            continue
        services.append(service_id)

    if not services:
        _log("Tidak ada bot yang dijalankan. Cek ENABLED_BOTS dan environment token di hosting.")
        return 1

    processes = {service_id: _start_service(service_id) for service_id in services}

    while not _STOP_EVENT.is_set():
        for script_name, process in list(processes.items()):
            return_code = process.poll()
            if return_code is None:
                continue

            _log(f"{script_name} berhenti dengan exit code {return_code}")
            if restart_failed and not _STOP_EVENT.is_set():
                _log(f"Restart {script_name} dalam {restart_delay} detik")
                if _STOP_EVENT.wait(restart_delay):
                    break
                processes[script_name] = _start_service(script_name)
            else:
                processes.pop(script_name, None)

        if not processes:
            _log("Semua bot berhenti.")
            return 1 if restart_failed else 0

        _STOP_EVENT.wait(1)

    for script_name, process in list(processes.items()):
        _terminate_process(script_name, process)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
