import os
import sys
import time
import sqlite3
import threading
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog

from dotenv import load_dotenv

try:
    from tkcalendar import Calendar
except Exception:
    Calendar = None

ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

APP_TITLE = os.getenv("GUI_APP_TITLE") or os.getenv("TRAY_APP_TITLE", "IG Tracker")
LOG_PATH = Path(os.getenv("GUI_LOG_PATH") or os.getenv("TRAY_LOG_PATH") or str(ROOT_DIR / "tracker.log"))
DB_PATH = Path(os.getenv("GUI_DB_PATH") or os.getenv("TRAY_DB_PATH") or str(ROOT_DIR / "instagram_tracker.db"))
REPORTS_DIR = Path(os.getenv("GUI_REPORTS_DIR") or os.getenv("TRAY_REPORTS_DIR") or str(ROOT_DIR / "reports"))
REPORT_DAYS = int(os.getenv("GUI_REPORT_DAYS") or os.getenv("TRAY_REPORT_DAYS") or "7")
POLL_SECONDS = int(os.getenv("GUI_STATUS_POLL_SECONDS") or os.getenv("TRAY_STATUS_POLL_SECONDS") or "5")
OPTIONS_POLL_SECONDS = int(os.getenv("GUI_OPTIONS_POLL_SECONDS", "30"))
AUTO_START = os.getenv("GUI_AUTO_START", "false").lower() == "true"
MONITOR_ONLY = os.getenv("GUI_MONITOR_ONLY", os.getenv("TRAY_MONITOR_ONLY", "false")).lower() == "true"

_process_lock = threading.Lock()
_process = None
_log_handle = None


def _tracker_env(overrides=None):
    env = os.environ.copy()
    if overrides:
        env.update(overrides)
    return env


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


def _start_tracker():
    if MONITOR_ONLY:
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


def _stop_tracker():
    if MONITOR_ONLY:
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


def _run_login_only():
    if MONITOR_ONLY:
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


def _open_log():
    if not LOG_PATH.exists():
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.touch()
    _open_path(LOG_PATH)


def _open_folder():
    _open_path(ROOT_DIR)


def _open_reports_folder():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _open_path(REPORTS_DIR)


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


def _format_dt(dt_value):
    if not dt_value:
        return "unknown"
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    dt_value = dt_value.astimezone()
    return dt_value.strftime("%Y-%m-%d %H:%M:%S")


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


def _report_time_range(days: int):
    end = datetime.utcnow().replace(microsecond=0)
    start = (end - timedelta(days=days)).replace(microsecond=0)
    return start.isoformat(), end.isoformat()


def _timestamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _run_report_to_file(args, output_name, message_cb=None):
    def _worker():
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / output_name
        with open(output_path, "w", encoding="utf-8") as handle:
            subprocess.run(
                [sys.executable, "-u", "report.py", *args],
                cwd=str(ROOT_DIR),
                env=_tracker_env(),
                stdout=handle,
                stderr=handle,
            )
        if message_cb:
            message_cb(f"Report saved: {output_path}")
        _open_path(output_path)

    threading.Thread(target=_worker, daemon=True).start()


def _run_report_list_csv(list_type, target, message_cb=None):
    def _worker():
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / f"current_{list_type}_{_timestamp()}.csv"
        args = ["list", "--type", list_type, "--out-csv", str(output_path)]
        if target:
            args += ["--target", target]
        subprocess.run(
            [sys.executable, "-u", "report.py", *args],
            cwd=str(ROOT_DIR),
            env=_tracker_env(),
        )
        if message_cb:
            message_cb(f"Report saved: {output_path}")
        _open_path(output_path)

    threading.Thread(target=_worker, daemon=True).start()


def _run_report_list_json(list_type, target, message_cb=None):
    def _worker():
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / f"current_{list_type}_{_timestamp()}.json"
        args = ["list", "--type", list_type, "--out-json", str(output_path)]
        if target:
            args += ["--target", target]
        subprocess.run(
            [sys.executable, "-u", "report.py", *args],
            cwd=str(ROOT_DIR),
            env=_tracker_env(),
        )
        if message_cb:
            message_cb(f"Report saved: {output_path}")
        _open_path(output_path)

    threading.Thread(target=_worker, daemon=True).start()


class TrackerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.status_var = tk.StringVar(value="Status: unknown")
        self.message_var = tk.StringVar(value="")
        self.last_output = ""

        self.available_dates = []
        self.available_targets = []
        self.available_run_times = []
        self.days_var = tk.StringVar(value=str(REPORT_DAYS))
        self.range_from_var = tk.StringVar(value="")
        self.range_to_var = tk.StringVar(value="")
        self.range_type_var = tk.StringVar(value="both")
        self.range_target_var = tk.StringVar(value="")

        self.day_var = tk.StringVar(value=datetime.now().date().isoformat())
        self.day_type_var = tk.StringVar(value="both")
        self.day_target_var = tk.StringVar(value="")

        self.snapshot_var = tk.StringVar(value="")
        self.snapshot_type_var = tk.StringVar(value="both")
        self.snapshot_target_var = tk.StringVar(value="")

        self.list_type_var = tk.StringVar(value="both")
        self.list_target_var = tk.StringVar(value="")

        self._load_available_dates()
        self._last_options_refresh = time.time()
        self._build_ui()
        self._update_status()
        if AUTO_START and not MONITOR_ONLY:
            _start_tracker()

    def _build_ui(self):
        padding = {"padx": 8, "pady": 6}

        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", **padding)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left")

        controls = ttk.Frame(self.root)
        controls.pack(fill="x", **padding)
        start_btn = ttk.Button(controls, text="Start tracker", command=self._start_tracker_clicked)
        stop_btn = ttk.Button(controls, text="Stop tracker", command=self._stop_tracker_clicked)
        login_btn = ttk.Button(controls, text="Login-only", command=self._login_only_clicked)
        log_btn = ttk.Button(controls, text="Open log", command=_open_log)
        folder_btn = ttk.Button(controls, text="Open folder", command=_open_folder)
        reports_btn = ttk.Button(controls, text="Open reports", command=_open_reports_folder)

        start_btn.pack(side="left", padx=4)
        stop_btn.pack(side="left", padx=4)
        login_btn.pack(side="left", padx=4)
        log_btn.pack(side="left", padx=4)
        folder_btn.pack(side="left", padx=4)
        reports_btn.pack(side="left", padx=4)

        if MONITOR_ONLY:
            start_btn.configure(state="disabled")
            stop_btn.configure(state="disabled")
            login_btn.configure(state="disabled")

        quick_frame = ttk.LabelFrame(self.root, text="Quick reports")
        quick_frame.pack(fill="x", **padding)

        ttk.Label(quick_frame, text="Days:").pack(side="left", padx=4)
        ttk.Entry(quick_frame, textvariable=self.days_var, width=5).pack(side="left")

        ttk.Button(quick_frame, text="Summary", command=self._summary_report).pack(side="left", padx=4)
        ttk.Button(quick_frame, text="New", command=self._new_report).pack(side="left", padx=4)
        ttk.Button(quick_frame, text="Lost", command=self._lost_report).pack(side="left", padx=4)
        ttk.Button(quick_frame, text="Daily counts", command=self._daily_report).pack(side="left", padx=4)
        ttk.Button(quick_frame, text="Snapshot now", command=self._snapshot_now).pack(side="left", padx=4)

        list_frame = ttk.LabelFrame(self.root, text="Current list export")
        list_frame.pack(fill="x", **padding)
        ttk.Label(list_frame, text="Type:").pack(side="left", padx=4)
        ttk.Combobox(list_frame, textvariable=self.list_type_var, values=["both", "followers", "followings"], width=12).pack(side="left")
        ttk.Label(list_frame, text="Target (optional):").pack(side="left", padx=4)
        self.list_target_cb = ttk.Combobox(
            list_frame,
            textvariable=self.list_target_var,
            values=self.available_targets,
            width=18,
            state="readonly",
        )
        self.list_target_cb.pack(side="left")
        ttk.Button(list_frame, text="Export CSV", command=self._list_csv).pack(side="left", padx=4)
        ttk.Button(list_frame, text="Export JSON", command=self._list_json).pack(side="left", padx=4)

        range_frame = ttk.LabelFrame(self.root, text="New/Lost in range (UTC)")
        range_frame.pack(fill="x", **padding)
        ttk.Label(range_frame, text="From (date):").pack(side="left", padx=4)
        self.range_from_cb = ttk.Combobox(
            range_frame,
            textvariable=self.range_from_var,
            values=self.available_dates,
            width=12,
            state="readonly",
        )
        self.range_from_cb.pack(side="left")
        ttk.Button(range_frame, text="Pick", command=self._pick_from_date).pack(side="left", padx=4)
        ttk.Label(range_frame, text="To (date):").pack(side="left", padx=4)
        self.range_to_cb = ttk.Combobox(
            range_frame,
            textvariable=self.range_to_var,
            values=self.available_dates,
            width=12,
            state="readonly",
        )
        self.range_to_cb.pack(side="left")
        ttk.Button(range_frame, text="Pick", command=self._pick_to_date).pack(side="left", padx=4)
        ttk.Label(range_frame, text="Type:").pack(side="left", padx=4)
        ttk.Combobox(range_frame, textvariable=self.range_type_var, values=["both", "followers", "followings"], width=10).pack(side="left")
        ttk.Label(range_frame, text="Target:").pack(side="left", padx=4)
        self.range_target_cb = ttk.Combobox(
            range_frame,
            textvariable=self.range_target_var,
            values=self.available_targets,
            width=14,
            state="readonly",
        )
        self.range_target_cb.pack(side="left")
        ttk.Button(range_frame, text="New", command=self._new_in_range).pack(side="left", padx=4)
        ttk.Button(range_frame, text="Lost", command=self._lost_in_range).pack(side="left", padx=4)

        day_frame = ttk.LabelFrame(self.root, text="Day details (UTC day)")
        day_frame.pack(fill="x", **padding)
        ttk.Label(day_frame, text="Date:").pack(side="left", padx=4)
        self.day_cb = ttk.Combobox(
            day_frame,
            textvariable=self.day_var,
            values=self.available_dates,
            width=12,
            state="readonly",
        )
        self.day_cb.pack(side="left")
        ttk.Button(day_frame, text="Pick", command=self._pick_day_date).pack(side="left", padx=4)
        ttk.Label(day_frame, text="Type:").pack(side="left", padx=4)
        ttk.Combobox(day_frame, textvariable=self.day_type_var, values=["both", "followers", "followings"], width=10).pack(side="left")
        ttk.Label(day_frame, text="Target:").pack(side="left", padx=4)
        self.day_target_cb = ttk.Combobox(
            day_frame,
            textvariable=self.day_target_var,
            values=self.available_targets,
            width=14,
            state="readonly",
        )
        self.day_target_cb.pack(side="left")
        ttk.Button(day_frame, text="Run day details", command=self._day_details).pack(side="left", padx=4)

        snap_frame = ttk.LabelFrame(self.root, text="Snapshot at time (UTC)")
        snap_frame.pack(fill="x", **padding)
        ttk.Label(snap_frame, text="At (date or ISO):").pack(side="left", padx=4)
        self.snapshot_cb = ttk.Combobox(
            snap_frame,
            textvariable=self.snapshot_var,
            values=self.available_run_times,
            width=20,
            state="readonly",
        )
        self.snapshot_cb.pack(side="left")
        ttk.Button(snap_frame, text="Pick", command=self._pick_snapshot_date).pack(side="left", padx=4)
        ttk.Label(snap_frame, text="Type:").pack(side="left", padx=4)
        ttk.Combobox(snap_frame, textvariable=self.snapshot_type_var, values=["both", "followers", "followings"], width=10).pack(side="left")
        ttk.Label(snap_frame, text="Target:").pack(side="left", padx=4)
        self.snapshot_target_cb = ttk.Combobox(
            snap_frame,
            textvariable=self.snapshot_target_var,
            values=self.available_targets,
            width=14,
            state="readonly",
        )
        self.snapshot_target_cb.pack(side="left")
        ttk.Button(snap_frame, text="Snapshot", command=self._snapshot_custom).pack(side="left", padx=4)

        message_frame = ttk.Frame(self.root)
        message_frame.pack(fill="x", **padding)
        ttk.Label(message_frame, textvariable=self.message_var, foreground="#444").pack(side="left")

        refresh_frame = ttk.Frame(self.root)
        refresh_frame.pack(fill="x", **padding)
        ttk.Button(refresh_frame, text="Refresh options from DB", command=self._refresh_dates_clicked).pack(side="left")

        output_frame = ttk.LabelFrame(self.root, text="Report output")
        output_frame.pack(fill="both", expand=True, **padding)
        self.output_text = tk.Text(output_frame, height=16, wrap="none")
        y_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        x_scroll = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output_text.xview)
        self.output_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        output_controls = ttk.Frame(self.root)
        output_controls.pack(fill="x", **padding)
        ttk.Button(output_controls, text="Save output", command=self._save_output).pack(side="left")
        ttk.Button(output_controls, text="Clear output", command=self._clear_output).pack(side="left", padx=6)

    def _set_message(self, text):
        self.message_var.set(text)

    def _set_output(self, text):
        self.last_output = text
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("end", text)
        self.output_text.configure(state="disabled")

    def _append_output(self, text):
        self.last_output += text
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text)
        self.output_text.configure(state="disabled")

    def _save_output(self):
        if not self.last_output:
            self._set_message("No output to save yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Save report output",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.last_output)
            self._set_message(f"Output saved: {path}")
        except Exception:
            self._set_message("Failed to save output.")

    def _clear_output(self):
        self._set_output("")

    def _load_available_dates(self):
        dates = []
        targets = []
        run_times = []
        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(str(DB_PATH), timeout=1)
                try:
                    rows = conn.execute(
                        "SELECT DISTINCT date(timestamp) AS day FROM counts ORDER BY day DESC"
                    ).fetchall()
                    if not rows:
                        rows = conn.execute(
                            "SELECT DISTINCT date(run_started_at) AS day FROM run_history ORDER BY day DESC"
                        ).fetchall()
                    target_rows = conn.execute(
                        "SELECT username FROM targets ORDER BY username"
                    ).fetchall()
                    run_rows = conn.execute(
                        "SELECT run_started_at FROM run_history ORDER BY run_started_at DESC LIMIT 200"
                    ).fetchall()
                finally:
                    conn.close()
                dates = [row[0] for row in rows if row and row[0]]
                targets = [row[0] for row in target_rows if row and row[0]]
                run_times = [row[0] for row in run_rows if row and row[0]]
            except Exception:
                dates = []
                targets = []
                run_times = []
        if not dates:
            dates = [datetime.now().date().isoformat()]
        if not targets:
            targets = [""]
        else:
            targets = [""] + targets
        if not run_times:
            run_times = [datetime.utcnow().replace(microsecond=0).isoformat()]

        self.available_dates = dates
        self.available_targets = targets
        self.available_run_times = run_times

        if not self.range_from_var.get():
            self.range_from_var.set(dates[-1] if dates else "")
        if not self.range_to_var.get():
            self.range_to_var.set(dates[0] if dates else "")
        if not self.day_var.get():
            self.day_var.set(dates[0] if dates else "")
        if not self.snapshot_var.get():
            self.snapshot_var.set(run_times[0] if run_times else "")

        if hasattr(self, "range_from_cb"):
            self.range_from_cb.configure(values=self.available_dates)
        if hasattr(self, "range_to_cb"):
            self.range_to_cb.configure(values=self.available_dates)
        if hasattr(self, "day_cb"):
            self.day_cb.configure(values=self.available_dates)
        if hasattr(self, "snapshot_cb"):
            self.snapshot_cb.configure(values=self.available_run_times)
        if hasattr(self, "range_target_cb"):
            self.range_target_cb.configure(values=self.available_targets)
        if hasattr(self, "day_target_cb"):
            self.day_target_cb.configure(values=self.available_targets)
        if hasattr(self, "snapshot_target_cb"):
            self.snapshot_target_cb.configure(values=self.available_targets)
        if hasattr(self, "list_target_cb"):
            self.list_target_cb.configure(values=self.available_targets)

    def _refresh_dates_clicked(self):
        self._load_available_dates()
        self._set_message("Options refreshed from DB.")

    def _open_calendar(self, title, initial_date, on_select):
        if Calendar is None:
            self._set_message("tkcalendar not installed. Run: pip install -r requirements.txt")
            return
        top = tk.Toplevel(self.root)
        top.title(title)
        cal = Calendar(top, selectmode="day", date_pattern="y-mm-dd")
        if initial_date:
            try:
                cal.selection_set(initial_date)
            except Exception:
                pass
        cal.pack(padx=10, pady=10)

        btns = ttk.Frame(top)
        btns.pack(pady=6)

        def _ok():
            on_select(cal.get_date())
            top.destroy()

        ttk.Button(btns, text="OK", command=_ok).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=top.destroy).pack(side="left", padx=6)

    def _extract_date_str(self, value):
        if not value:
            return datetime.now().date().isoformat()
        if "T" in value:
            return value.split("T", 1)[0]
        return value[:10]

    def _set_date_var(self, var, date_str, time_suffix=None):
        if time_suffix:
            var.set(f"{date_str}{time_suffix}")
        else:
            var.set(date_str)

    def _pick_from_date(self):
        initial = self._extract_date_str(self.range_from_var.get())
        self._open_calendar(
            "Select start date",
            initial,
            lambda date_str: self._set_date_var(self.range_from_var, date_str, "T00:00:00"),
        )

    def _pick_to_date(self):
        initial = self._extract_date_str(self.range_to_var.get())
        self._open_calendar(
            "Select end date",
            initial,
            lambda date_str: self._set_date_var(self.range_to_var, date_str, "T23:59:59"),
        )

    def _pick_day_date(self):
        initial = self._extract_date_str(self.day_var.get())
        self._open_calendar(
            "Select day",
            initial,
            lambda date_str: self._set_date_var(self.day_var, date_str),
        )

    def _pick_snapshot_date(self):
        initial = self._extract_date_str(self.snapshot_var.get())
        self._open_calendar(
            "Select snapshot date",
            initial,
            lambda date_str: self._set_date_var(self.snapshot_var, date_str, "T00:00:00"),
        )

    def _update_status(self):
        _cleanup_process_if_needed()
        if time.time() - self._last_options_refresh >= OPTIONS_POLL_SECONDS:
            self._load_available_dates()
            self._last_options_refresh = time.time()
        running = _is_running()
        last_run = _read_last_run()
        if last_run:
            when = _format_dt(last_run.get("finished_at") or last_run.get("started_at"))
            status = last_run.get("status") or "unknown"
            status_text = f"Status: {'running' if running else 'stopped'} | Last: {when} ({status})"
        else:
            status_text = f"Status: {'running' if running else 'stopped'} | Last: unknown"
        self.status_var.set(status_text)
        self.root.after(POLL_SECONDS * 1000, self._update_status)

    def _start_tracker_clicked(self):
        _start_tracker()
        self._set_message("Tracker started.")

    def _stop_tracker_clicked(self):
        _stop_tracker()
        self._set_message("Tracker stopped.")

    def _login_only_clicked(self):
        _run_login_only()
        self._set_message("Login-only started (visible browser).")

    def _summary_report(self):
        days = self._get_days()
        self._run_report_to_text(["summary", "--days", str(days)], f"Summary last {days} days")

    def _new_report(self):
        days = self._get_days()
        start, end = _report_time_range(days)
        self._run_report_to_text(
            ["new", "--from", start, "--to", end, "--type", "both"],
            f"New last {days} days",
        )

    def _lost_report(self):
        days = self._get_days()
        start, end = _report_time_range(days)
        self._run_report_to_text(
            ["lost", "--from", start, "--to", end, "--type", "both"],
            f"Lost last {days} days",
        )

    def _daily_report(self):
        days = self._get_days()
        self._run_report_to_text(["daily", "--days", str(days)], f"Daily counts last {days} days")

    def _snapshot_now(self):
        at = datetime.utcnow().replace(microsecond=0).isoformat()
        self._run_report_to_text(["snapshot", "--at", at, "--type", "both"], "Snapshot now")

    def _list_csv(self):
        list_type = self.list_type_var.get() or "both"
        target = (self.list_target_var.get() or "").strip()
        _run_report_list_csv(list_type, target, self._set_message)

    def _list_json(self):
        list_type = self.list_type_var.get() or "both"
        target = (self.list_target_var.get() or "").strip()
        _run_report_list_json(list_type, target, self._set_message)

    def _new_in_range(self):
        from_dt, to_dt = self._get_range_inputs()
        if not from_dt or not to_dt:
            self._set_message("Please fill From and To (ISO).")
            return
        rtype = self.range_type_var.get() or "both"
        target = (self.range_target_var.get() or "").strip()
        args = ["new", "--from", from_dt, "--to", to_dt, "--type", rtype]
        if target:
            args += ["--target", target]
        self._run_report_to_text(args, "New in range")

    def _lost_in_range(self):
        from_dt, to_dt = self._get_range_inputs()
        if not from_dt or not to_dt:
            self._set_message("Please fill From and To (ISO).")
            return
        rtype = self.range_type_var.get() or "both"
        target = (self.range_target_var.get() or "").strip()
        args = ["lost", "--from", from_dt, "--to", to_dt, "--type", rtype]
        if target:
            args += ["--target", target]
        self._run_report_to_text(args, "Lost in range")

    def _day_details(self):
        day = (self.day_var.get() or "").strip()
        if not day:
            self._set_message("Please enter date YYYY-MM-DD.")
            return
        rtype = self.day_type_var.get() or "both"
        target = (self.day_target_var.get() or "").strip()
        args = ["day", "--date", day, "--type", rtype]
        if target:
            args += ["--target", target]
        self._run_report_to_text(args, f"Day details {day}")

    def _snapshot_custom(self):
        at = (self.snapshot_var.get() or "").strip()
        rtype = self.snapshot_type_var.get() or "both"
        target = (self.snapshot_target_var.get() or "").strip()
        args = ["snapshot", "--type", rtype]
        if at:
            if len(at) == 10:
                at = f"{at}T00:00:00"
            args += ["--at", at]
        if target:
            args += ["--target", target]
        self._run_report_to_text(args, f"Snapshot {at or 'now'}")

    def _get_days(self):
        try:
            return int(self.days_var.get())
        except ValueError:
            return REPORT_DAYS

    def _get_range_inputs(self):
        from_dt = (self.range_from_var.get() or "").strip()
        to_dt = (self.range_to_var.get() or "").strip()
        if from_dt and len(from_dt) == 10:
            from_dt = f"{from_dt}T00:00:00"
        if to_dt and len(to_dt) == 10:
            to_dt = f"{to_dt}T23:59:59"
        return from_dt, to_dt

    def _run_report_to_text(self, args, title):
        self._set_message("Running report...")

        def _worker():
            env = _tracker_env({"RICH_COLOR_SYSTEM": "none", "TERM": "dumb"})
            result = subprocess.run(
                [sys.executable, "-u", "report.py", *args],
                cwd=str(ROOT_DIR),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            output = result.stdout or ""
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            header = f"{title} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
            text_out = header + ("-" * len(header)) + "\n" + output

            def _update():
                self._set_output(text_out)
                self._set_message("Report ready.")

            self.root.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()


def main():
    root = tk.Tk()
    TrackerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
