import os
import sys
import time
import sqlite3
import threading
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
import pystray
from PIL import Image, ImageDraw


ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

APP_TITLE = os.getenv("TRAY_APP_TITLE", "IG Tracker")
LOG_PATH = Path(os.getenv("TRAY_LOG_PATH", str(ROOT_DIR / "tracker.log")))
DB_PATH = Path(os.getenv("TRAY_DB_PATH", str(ROOT_DIR / "instagram_tracker.db")))
REPORTS_DIR = Path(os.getenv("TRAY_REPORTS_DIR", str(ROOT_DIR / "reports")))
REPORT_DAYS = int(os.getenv("TRAY_REPORT_DAYS", "7"))
POLL_SECONDS = int(os.getenv("TRAY_STATUS_POLL_SECONDS", "5"))
AUTO_START = os.getenv("TRAY_AUTO_START", "false").lower() == "true"
MONITOR_ONLY = os.getenv("TRAY_MONITOR_ONLY", "false").lower() == "true"
AUTO_MONITOR_ON_SCHEDULER = os.getenv("TRAY_AUTO_MONITOR_ON_SCHEDULER", "true").lower() == "true"

_process_lock = threading.Lock()
_process = None
_log_handle = None
_stop_event = threading.Event()
_runtime_monitor_only = MONITOR_ONLY
_scheduler_detected = False


def _detect_scheduler_tracker():
    if not sys.platform.startswith("win"):
        return False
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
        text = (result.stdout or "").lower()
        return "main.py" in text or "ig-followers-and-following" in text
    except Exception:
        return False


def _create_image():
    size = 64
    image = Image.new("RGB", (size, size), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, size - 8, size - 8), outline=(0, 0, 0), width=4)
    draw.rectangle((26, 26, 38, 38), fill=(0, 0, 0))
    return image


def _is_running():
    with _process_lock:
        return _process is not None and _process.poll() is None


def _cleanup_process_if_needed():
    global _process, _log_handle
    with _process_lock:
        if _process is not None and _process.poll() is not None:
            _process = None
            if _log_handle:
                try:
                    _log_handle.close()
                except Exception:
                    pass
                _log_handle = None


def _tracker_env(overrides=None):
    env = os.environ.copy()
    env.setdefault("LOG_FILE", str(LOG_PATH))
    if overrides:
        env.update(overrides)
    return env


def _start_tracker(_=None):
    if _runtime_monitor_only:
        return
    global _process, _log_handle
    with _process_lock:
        if _process is not None and _process.poll() is None:
            return
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _log_handle = open(LOG_PATH, "a", encoding="utf-8")
        _process = subprocess.Popen(
            [sys.executable, "-u", "main.py"],
            cwd=str(ROOT_DIR),
            env=_tracker_env(),
            stdout=_log_handle,
            stderr=_log_handle,
        )


def _stop_tracker(_=None):
    if _runtime_monitor_only:
        return
    global _process, _log_handle
    with _process_lock:
        if _process is None or _process.poll() is not None:
            _cleanup_process_if_needed()
            return
        _process.terminate()
        try:
            _process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _process.kill()
        _process = None
        if _log_handle:
            try:
                _log_handle.close()
            except Exception:
                pass
            _log_handle = None


def _run_login_only(_=None):
    if _runtime_monitor_only:
        return
    if _is_running():
        return
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = open(LOG_PATH, "a", encoding="utf-8")
    env = _tracker_env({"LOGIN_ONLY_MODE": "true", "HEADLESS_MODE": "false"})
    proc = subprocess.Popen(
        [sys.executable, "-u", "main.py"],
        cwd=str(ROOT_DIR),
        env=env,
        stdout=handle,
        stderr=handle,
    )

    def _wait_and_close():
        try:
            proc.wait()
        finally:
            try:
                handle.close()
            except Exception:
                pass

    threading.Thread(target=_wait_and_close, daemon=True).start()


def _open_path(path: Path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


def _open_log(_=None):
    if not LOG_PATH.exists():
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.touch()
    _open_path(LOG_PATH)


def _open_folder(_=None):
    _open_path(ROOT_DIR)


def _open_gui(_=None):
    try:
        subprocess.Popen(
            [sys.executable, "-u", "gui_app.py"],
            cwd=str(ROOT_DIR),
            env=_tracker_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _read_last_run():
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=1)
        try:
            row = conn.execute(
                "SELECT run_started_at, run_finished_at, status "
                "FROM run_history ORDER BY run_started_at DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        started_at = _parse_dt(row[0])
        finished_at = _parse_dt(row[1])
        status = row[2]
        return {"started_at": started_at, "finished_at": finished_at, "status": status}
    except Exception:
        return None


def _format_dt(dt_value):
    if not dt_value:
        return "unknown"
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    dt_value = dt_value.astimezone()
    return dt_value.strftime("%Y-%m-%d %H:%M:%S")


def _ensure_reports_dir():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _report_time_range():
    end = datetime.now(timezone.utc).replace(microsecond=0).replace(tzinfo=None)
    start = (end - timedelta(days=REPORT_DAYS)).replace(microsecond=0)
    return start.isoformat(), end.isoformat()


def _run_report_to_file(args, output_name):
    def _worker():
        _ensure_reports_dir()
        output_path = REPORTS_DIR / output_name
        with open(output_path, "w", encoding="utf-8") as handle:
            subprocess.run(
                [sys.executable, "-u", "report.py", *args],
                cwd=str(ROOT_DIR),
                env=_tracker_env(),
                stdout=handle,
                stderr=handle,
            )
        _open_path(output_path)

    threading.Thread(target=_worker, daemon=True).start()


def _run_report_list_csv(list_type):
    def _worker():
        _ensure_reports_dir()
        output_path = REPORTS_DIR / f"current_{list_type}.csv"
        subprocess.run(
            [sys.executable, "-u", "report.py", "list", "--type", list_type, "--out-csv", str(output_path)],
            cwd=str(ROOT_DIR),
            env=_tracker_env(),
        )
        _open_path(output_path)

    threading.Thread(target=_worker, daemon=True).start()


def _report_current_followers(_=None):
    _run_report_list_csv("followers")


def _report_current_followings(_=None):
    _run_report_list_csv("followings")


def _report_current_both(_=None):
    _run_report_list_csv("both")


def _report_summary(_=None):
    _run_report_to_file(["summary", "--days", str(REPORT_DAYS)], f"summary_{REPORT_DAYS}d.txt")


def _report_new(_=None):
    start, end = _report_time_range()
    _run_report_to_file(
        ["new", "--from", start, "--to", end, "--type", "both"],
        f"new_{REPORT_DAYS}d.txt",
    )


def _report_lost(_=None):
    start, end = _report_time_range()
    _run_report_to_file(
        ["lost", "--from", start, "--to", end, "--type", "both"],
        f"lost_{REPORT_DAYS}d.txt",
    )


def _report_snapshot(_=None):
    at = datetime.now(timezone.utc).replace(microsecond=0).replace(tzinfo=None).isoformat()
    _run_report_to_file(["snapshot", "--at", at, "--type", "both"], "snapshot_now.txt")


def _report_daily_counts(_=None):
    _run_report_to_file(
        ["daily", "--days", str(REPORT_DAYS)],
        f"daily_{REPORT_DAYS}d.txt",
    )


def _report_day_details(date_str: str, label: str):
    _run_report_to_file(
        ["day", "--date", date_str, "--type", "both"],
        f"day_{label}_{date_str}.txt",
    )


def _report_day_today(_=None):
    date_str = datetime.now().date().isoformat()
    _report_day_details(date_str, "today")


def _report_day_yesterday(_=None):
    date_str = (datetime.now().date() - timedelta(days=1)).isoformat()
    _report_day_details(date_str, "yesterday")


def _open_reports_folder(_=None):
    _ensure_reports_dir()
    _open_path(REPORTS_DIR)


def _cookie_status():
    cookie_file = ROOT_DIR / "instagram_cookies.json"
    if not cookie_file.exists():
        return "cookie:missing"
    age_hours = (time.time() - cookie_file.stat().st_mtime) / 3600.0
    if age_hours < 24:
        return f"cookie:{age_hours:.1f}h"
    return f"cookie:{age_hours / 24.0:.1f}d"


def _last_error_short():
    if not LOG_PATH.exists():
        return "err:none"
    try:
        with open(LOG_PATH, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 16384), os.SEEK_SET)
            text = handle.read().decode("utf-8", errors="replace")
        for line in reversed([line.strip() for line in text.splitlines() if line.strip()]):
            if "[ERROR]" in line:
                return "err:yes"
    except Exception:
        pass
    return "err:none"


def _status_title():
    running = _is_running()
    last_run = _read_last_run()
    mode = "monitor" if _runtime_monitor_only else "control"
    if _runtime_monitor_only and _scheduler_detected:
        state = "External"
    else:
        state = "Running" if running else "Stopped"
    title = f"{APP_TITLE}: {state} ({mode})"
    title = f"{title} | {_cookie_status()} | {_last_error_short()}"
    if last_run:
        when = _format_dt(last_run.get("finished_at") or last_run.get("started_at"))
        status = last_run.get("status") or "unknown"
        title = f"{title} | Last: {when} ({status})"
    return title


def _update_loop(icon):
    while not _stop_event.is_set():
        _cleanup_process_if_needed()
        icon.title = _status_title()
        time.sleep(POLL_SECONDS)


def _quit_app(icon, _):
    _stop_event.set()
    _stop_tracker()
    icon.stop()


def _menu():
    reports_menu = pystray.Menu(
        pystray.MenuItem("Current followers (CSV)", _report_current_followers),
        pystray.MenuItem("Current followings (CSV)", _report_current_followings),
        pystray.MenuItem("Current both (CSV)", _report_current_both),
        pystray.MenuItem(f"Summary last {REPORT_DAYS} days", _report_summary),
        pystray.MenuItem(f"New last {REPORT_DAYS} days", _report_new),
        pystray.MenuItem(f"Lost last {REPORT_DAYS} days", _report_lost),
        pystray.MenuItem(f"Daily counts last {REPORT_DAYS} days", _report_daily_counts),
        pystray.MenuItem("Day details (today)", _report_day_today),
        pystray.MenuItem("Day details (yesterday)", _report_day_yesterday),
        pystray.MenuItem("Snapshot now", _report_snapshot),
        pystray.MenuItem("Open reports folder", _open_reports_folder),
    )
    return pystray.Menu(
        pystray.MenuItem("Start tracker", _start_tracker, enabled=lambda _: (not _runtime_monitor_only and not _is_running())),
        pystray.MenuItem("Stop tracker", _stop_tracker, enabled=lambda _: (not _runtime_monitor_only and _is_running())),
        pystray.MenuItem("Login-only (visible browser)", _run_login_only, enabled=lambda _: (not _runtime_monitor_only and not _is_running())),
        pystray.MenuItem("Reports", reports_menu),
        pystray.MenuItem("Open GUI", _open_gui),
        pystray.MenuItem("Open log", _open_log),
        pystray.MenuItem("Open folder", _open_folder),
        pystray.MenuItem("Exit", _quit_app),
    )


def main():
    global _runtime_monitor_only, _scheduler_detected
    _scheduler_detected = _detect_scheduler_tracker()
    if AUTO_MONITOR_ON_SCHEDULER and _scheduler_detected:
        _runtime_monitor_only = True

    icon = pystray.Icon("ig-tracker", _create_image(), APP_TITLE, menu=_menu())
    threading.Thread(target=_update_loop, args=(icon,), daemon=True).start()
    if AUTO_START and not _runtime_monitor_only:
        _start_tracker()
    icon.run()


if __name__ == "__main__":
    main()
