import os
import sys
import time
import sqlite3
import threading
import subprocess
import importlib.util
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog

from dotenv import load_dotenv

try:
    from tkcalendar import Calendar
except Exception:
    Calendar = None

if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)
IS_FROZEN = getattr(sys, "frozen", False)
BIN_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else ROOT_DIR

APP_TITLE = os.getenv("GUI_APP_TITLE") or os.getenv("TRAY_APP_TITLE", "IG Tracker")
LOG_PATH = Path(os.getenv("GUI_LOG_PATH") or os.getenv("TRAY_LOG_PATH") or str(ROOT_DIR / "tracker.log"))
DB_PATH = Path(os.getenv("GUI_DB_PATH") or os.getenv("TRAY_DB_PATH") or str(ROOT_DIR / "instagram_tracker.db"))
REPORTS_DIR = Path(os.getenv("GUI_REPORTS_DIR") or os.getenv("TRAY_REPORTS_DIR") or str(ROOT_DIR / "reports"))
REPORT_DAYS = int(os.getenv("GUI_REPORT_DAYS") or os.getenv("TRAY_REPORT_DAYS") or "7")
POLL_SECONDS = int(os.getenv("GUI_STATUS_POLL_SECONDS") or os.getenv("TRAY_STATUS_POLL_SECONDS") or "5")
OPTIONS_POLL_SECONDS = int(os.getenv("GUI_OPTIONS_POLL_SECONDS", "30"))
AUTO_START = os.getenv("GUI_AUTO_START", "false").lower() == "true"
MONITOR_ONLY = os.getenv("GUI_MONITOR_ONLY", os.getenv("TRAY_MONITOR_ONLY", "false")).lower() == "true"
REQUIRED_ENV_KEYS = ("IG_USERNAME", "IG_PASSWORD", "TARGET_ACCOUNT")

_process_lock = threading.Lock()
_process = None
_log_handle = None


def _tool_cmd(script_name: str, exe_name: str):
    if IS_FROZEN:
        exe_path = BIN_DIR / exe_name
        return [str(exe_path)] if exe_path.exists() else None
    return [sys.executable, "-u", script_name]


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _tracker_env(overrides=None):
    env = os.environ.copy()
    env.setdefault("LOG_FILE", str(LOG_PATH))
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
    cmd = _tool_cmd("main.py", "ig-tracker-cli.exe")
    if not cmd:
        return
    with _process_lock:
        if _process is not None and _process.poll() is None:
            return
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _log_handle = open(LOG_PATH, "a", encoding="utf-8")
        _process = subprocess.Popen(
            cmd,
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
    cmd = _tool_cmd("main.py", "ig-tracker-cli.exe")
    if not cmd:
        return
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = open(LOG_PATH, "a", encoding="utf-8")
    env = _tracker_env({"LOGIN_ONLY_MODE": "true", "HEADLESS_MODE": "false"})
    proc = subprocess.Popen(
        cmd,
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


def _parse_db_utc_dt(value):
    dt_value = _parse_dt(value)
    if not dt_value:
        return None
    if dt_value.tzinfo is None:
        # DB values are stored in UTC; treat naive timestamps as UTC.
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value


def _local_tz():
    return datetime.now().astimezone().tzinfo


def _to_local_day(value):
    dt_value = _parse_db_utc_dt(value)
    if not dt_value:
        return None
    return dt_value.astimezone().date().isoformat()


def _to_local_iso_datetime(value):
    dt_value = _parse_db_utc_dt(value)
    if not dt_value:
        return None
    return dt_value.astimezone().strftime("%Y-%m-%dT%H:%M:%S")


def _local_iso_to_utc_naive(value: str):
    dt_value = _parse_dt(value)
    if not dt_value:
        return None
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=_local_tz())
    return dt_value.astimezone(timezone.utc).replace(tzinfo=None)


def _local_day_to_utc_range(day_str: str):
    day_local = datetime.fromisoformat(day_str).date()
    start_local = datetime.combine(day_local, datetime.min.time(), tzinfo=_local_tz())
    end_local = datetime.combine(day_local, datetime.max.time(), tzinfo=_local_tz())
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return (
        start_utc.strftime("%Y-%m-%d %H:%M:%S.%f"),
        end_utc.strftime("%Y-%m-%d %H:%M:%S.%f"),
    )


def _format_dt(dt_value):
    if not dt_value:
        return "unknown"
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    dt_value = dt_value.astimezone()
    return dt_value.strftime("%Y-%m-%d %H:%M:%S")


def _parse_log_timestamp(line: str):
    if not line or len(line) < 23:
        return None
    # Python logging default here: "YYYY-MM-DD HH:MM:SS,mmm ..."
    stamp = line[:23]
    try:
        return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S,%f").replace(tzinfo=_local_tz())
    except ValueError:
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


def _read_last_success_run():
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=1)
        try:
            row = conn.execute(
                "SELECT run_started_at, run_finished_at "
                "FROM run_history WHERE status = 'success' "
                "ORDER BY run_started_at DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        started_at = _parse_dt(row[0])
        finished_at = _parse_dt(row[1])
        return {"started_at": started_at, "finished_at": finished_at}
    except Exception:
        return None


def _report_time_range(days: int):
    end_local = datetime.now().astimezone().replace(microsecond=0)
    start_local = (end_local - timedelta(days=days)).replace(microsecond=0)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc.isoformat(), end_utc.isoformat()


def _timestamp():
    return _utcnow_naive().strftime("%Y%m%d_%H%M%S")


def _run_report_to_file(args, output_name, message_cb=None):
    def _worker():
        cmd = _tool_cmd("report.py", "ig-tracker-report.exe")
        if not cmd:
            return
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / output_name
        with open(output_path, "w", encoding="utf-8") as handle:
            subprocess.run(
                [*cmd, *args],
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
        cmd = _tool_cmd("report.py", "ig-tracker-report.exe")
        if not cmd:
            return
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / f"current_{list_type}_{_timestamp()}.csv"
        args = ["list", "--type", list_type, "--out-csv", str(output_path)]
        if target:
            args += ["--target", target]
        subprocess.run(
            [*cmd, *args],
            cwd=str(ROOT_DIR),
            env=_tracker_env(),
        )
        if message_cb:
            message_cb(f"Report saved: {output_path}")
        _open_path(output_path)

    threading.Thread(target=_worker, daemon=True).start()


def _run_report_list_json(list_type, target, message_cb=None):
    def _worker():
        cmd = _tool_cmd("report.py", "ig-tracker-report.exe")
        if not cmd:
            return
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / f"current_{list_type}_{_timestamp()}.json"
        args = ["list", "--type", list_type, "--out-json", str(output_path)]
        if target:
            args += ["--target", target]
        subprocess.run(
            [*cmd, *args],
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
        self._configure_window()
        self.status_var = tk.StringVar(value="Status: unknown")
        self.message_var = tk.StringVar(value="")
        self.last_output = ""
        self.wizard_summary_var = tk.StringVar(value="Run checks to verify first-time setup.")
        self.cookie_status_var = tk.StringVar(value="Cookie: unknown")
        self.error_status_var = tk.StringVar(value="Last error: none")
        self.stale_status_var = tk.StringVar(value="Freshness: unknown")
        self.session_monitor_only = tk.BooleanVar(value=MONITOR_ONLY)
        self._auto_mode_applied = False

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
        self.daily_target_var = tk.StringVar(value="(all)")
        self.daily_type_var = tk.StringVar(value="both")
        self._suppress_daily_select = False

        self._load_available_dates()
        self._last_options_refresh = time.time()
        self._build_ui()
        self._run_wizard_checks()
        self._load_daily_compare(show_message=False)
        self._update_status()
        if AUTO_START and not MONITOR_ONLY:
            _start_tracker()

    def _configure_window(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(1280, max(980, screen_w - 80))
        height = min(860, max(640, screen_h - 120))
        if screen_w <= 1366:
            width = min(width, screen_w - 40)
        if screen_h <= 768:
            height = min(height, screen_h - 80)
        pos_x = max(0, (screen_w - width) // 2)
        pos_y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.root.minsize(920, 620)

    def _create_notebook(self):
        notebook = ttk.Notebook(self.root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
        return notebook

    def _create_scrollable_tab(self, title):
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=title)
        tab_frame.rowconfigure(0, weight=1)
        tab_frame.columnconfigure(0, weight=1)

        canvas = tk.Canvas(tab_frame, highlightthickness=0, borderwidth=0)
        scroll = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        body = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_body_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        def _on_mousewheel(event):
            if event.delta == 0:
                return
            step = int(-event.delta / 120)
            if step == 0:
                step = -1 if event.delta > 0 else 1
            canvas.yview_scroll(step, "units")

        def _on_linux_scroll(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind_scroll(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_linux_scroll)
            canvas.bind_all("<Button-5>", _on_linux_scroll)

        def _unbind_scroll(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        body.bind("<Configure>", _on_body_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<Enter>", _bind_scroll)
        canvas.bind("<Leave>", _unbind_scroll)
        body.bind("<Enter>", _bind_scroll)
        body.bind("<Leave>", _unbind_scroll)
        return body

    def _build_form_row(self, parent, row, widgets, max_cols=8):
        cur_row = row
        cur_col = 0
        for widget in widgets:
            if widget is None:
                continue
            widget.grid(row=cur_row, column=cur_col, sticky="w", padx=4, pady=4)
            cur_col += 1
            if cur_col >= max_cols:
                cur_col = 0
                cur_row += 1
        return cur_row

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header_frame = ttk.Frame(self.root)
        header_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        header_frame.columnconfigure(0, weight=1)
        ttk.Label(header_frame, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        health_frame = ttk.Frame(header_frame)
        health_frame.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        health_frame.columnconfigure(1, weight=1)
        ttk.Label(health_frame, textvariable=self.cookie_status_var).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(health_frame, textvariable=self.error_status_var).grid(row=0, column=1, sticky="w")
        ttk.Label(health_frame, textvariable=self.stale_status_var).grid(row=0, column=2, sticky="w", padx=(12, 0))

        self.notebook = self._create_notebook()
        overview_tab = self._create_scrollable_tab("Overview")
        reports_tab = self._create_scrollable_tab("Reports")
        daily_tab = self._create_scrollable_tab("Daily Compare")
        db_tools_tab = self._create_scrollable_tab("DB Tools")
        output_tab = ttk.Frame(self.notebook)
        self.notebook.add(output_tab, text="Output")

        self._build_overview_tab(overview_tab)
        self._build_reports_tab(reports_tab)
        self._build_daily_tab(daily_tab)
        self._build_db_tools_tab(db_tools_tab)
        self._build_output_tab(output_tab)

        message_frame = ttk.Frame(self.root)
        message_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        message_frame.columnconfigure(0, weight=1)
        ttk.Label(message_frame, textvariable=self.message_var, foreground="#444").grid(row=0, column=0, sticky="w")



    def _build_overview_tab(self, parent):
        parent.columnconfigure(0, weight=1)

        controls = ttk.LabelFrame(parent, text="Tracker controls")
        controls.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self.start_btn = ttk.Button(controls, text="Start tracker", command=self._start_tracker_clicked)
        self.stop_btn = ttk.Button(controls, text="Stop tracker", command=self._stop_tracker_clicked)
        self.login_btn = ttk.Button(controls, text="Login-only", command=self._login_only_clicked)
        log_btn = ttk.Button(controls, text="Open log", command=_open_log)
        folder_btn = ttk.Button(controls, text="Open folder", command=_open_folder)
        reports_btn = ttk.Button(controls, text="Open reports", command=_open_reports_folder)
        self._build_form_row(
            controls,
            0,
            [self.start_btn, self.stop_btn, self.login_btn, log_btn, folder_btn, reports_btn],
            max_cols=4,
        )
        ttk.Checkbutton(
            controls,
            text="Monitor-only session",
            variable=self.session_monitor_only,
            command=self._apply_control_mode,
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=4, pady=(2, 6))
        self._apply_control_mode()

        wizard_frame = ttk.LabelFrame(parent, text="First-run wizard")
        wizard_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        wizard_frame.columnconfigure(0, weight=1)
        wizard_controls = ttk.Frame(wizard_frame)
        wizard_controls.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 2))
        self._build_form_row(
            wizard_controls,
            0,
            [
                ttk.Button(wizard_controls, text="Run setup checks", command=self._run_wizard_checks),
                ttk.Button(wizard_controls, text="Open .env", command=self._open_env_file),
                ttk.Button(wizard_controls, text="Run login-only now", command=self._login_only_clicked),
            ],
            max_cols=3,
        )
        ttk.Label(wizard_frame, textvariable=self.wizard_summary_var).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))

        wizard_table = ttk.Frame(wizard_frame)
        wizard_table.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        wizard_table.columnconfigure(0, weight=1)
        wizard_table.rowconfigure(0, weight=1)
        self.wizard_tree = ttk.Treeview(
            wizard_table,
            columns=("check", "status", "details"),
            show="headings",
            height=6,
        )
        self.wizard_tree.heading("check", text="Check")
        self.wizard_tree.heading("status", text="Status")
        self.wizard_tree.heading("details", text="Details")
        self.wizard_tree.column("check", width=170, anchor="w")
        self.wizard_tree.column("status", width=90, anchor="center")
        self.wizard_tree.column("details", width=520, anchor="w", stretch=True)
        wizard_scroll = ttk.Scrollbar(wizard_table, orient="vertical", command=self.wizard_tree.yview)
        self.wizard_tree.configure(yscrollcommand=wizard_scroll.set)
        self.wizard_tree.grid(row=0, column=0, sticky="nsew")
        wizard_scroll.grid(row=0, column=1, sticky="ns")

    def _build_reports_tab(self, parent):
        parent.columnconfigure(0, weight=1)

        quick_frame = ttk.LabelFrame(parent, text="Quick reports")
        quick_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self._build_form_row(
            quick_frame,
            0,
            [
                ttk.Label(quick_frame, text="Days:"),
                ttk.Entry(quick_frame, textvariable=self.days_var, width=6),
                ttk.Button(quick_frame, text="Summary", command=self._summary_report),
                ttk.Button(quick_frame, text="New", command=self._new_report),
                ttk.Button(quick_frame, text="Lost", command=self._lost_report),
                ttk.Button(quick_frame, text="Daily counts", command=self._daily_report),
                ttk.Button(quick_frame, text="Snapshot now", command=self._snapshot_now),
            ],
            max_cols=5,
        )

        list_frame = ttk.LabelFrame(parent, text="Current list export")
        list_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        ttk.Label(list_frame, text="Type:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            list_frame,
            textvariable=self.list_type_var,
            values=["both", "followers", "followings"],
            width=12,
            state="readonly",
        ).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(list_frame, text="Target (optional):").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.list_target_cb = ttk.Combobox(
            list_frame,
            textvariable=self.list_target_var,
            values=self.available_targets,
            width=22,
            state="readonly",
        )
        self.list_target_cb.grid(row=0, column=3, sticky="w", padx=4, pady=4)
        ttk.Button(list_frame, text="Export CSV", command=self._list_csv).grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))
        ttk.Button(list_frame, text="Export JSON", command=self._list_json).grid(row=1, column=1, sticky="w", padx=4, pady=(0, 4))

        range_frame = ttk.LabelFrame(parent, text="New/Lost in range (local time)")
        range_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=4)
        ttk.Label(range_frame, text="From (date):").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.range_from_cb = ttk.Combobox(
            range_frame,
            textvariable=self.range_from_var,
            values=self.available_dates,
            width=14,
            state="readonly",
        )
        self.range_from_cb.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Button(range_frame, text="Pick", command=self._pick_from_date).grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Label(range_frame, text="To (date):").grid(row=0, column=3, sticky="w", padx=4, pady=4)
        self.range_to_cb = ttk.Combobox(
            range_frame,
            textvariable=self.range_to_var,
            values=self.available_dates,
            width=14,
            state="readonly",
        )
        self.range_to_cb.grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Button(range_frame, text="Pick", command=self._pick_to_date).grid(row=0, column=5, sticky="w", padx=4, pady=4)
        ttk.Label(range_frame, text="Type:").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            range_frame,
            textvariable=self.range_type_var,
            values=["both", "followers", "followings"],
            width=12,
            state="readonly",
        ).grid(row=1, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(range_frame, text="Target:").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        self.range_target_cb = ttk.Combobox(
            range_frame,
            textvariable=self.range_target_var,
            values=self.available_targets,
            width=22,
            state="readonly",
        )
        self.range_target_cb.grid(row=1, column=3, sticky="w", padx=4, pady=4)
        ttk.Button(range_frame, text="New", command=self._new_in_range).grid(row=2, column=0, sticky="w", padx=4, pady=(0, 4))
        ttk.Button(range_frame, text="Lost", command=self._lost_in_range).grid(row=2, column=1, sticky="w", padx=4, pady=(0, 4))

        day_frame = ttk.LabelFrame(parent, text="Day details (local day)")
        day_frame.grid(row=3, column=0, sticky="ew", padx=4, pady=4)
        ttk.Label(day_frame, text="Date:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.day_cb = ttk.Combobox(
            day_frame,
            textvariable=self.day_var,
            values=self.available_dates,
            width=14,
            state="readonly",
        )
        self.day_cb.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Button(day_frame, text="Pick", command=self._pick_day_date).grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Label(day_frame, text="Type:").grid(row=0, column=3, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            day_frame,
            textvariable=self.day_type_var,
            values=["both", "followers", "followings"],
            width=12,
            state="readonly",
        ).grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Label(day_frame, text="Target:").grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))
        self.day_target_cb = ttk.Combobox(
            day_frame,
            textvariable=self.day_target_var,
            values=self.available_targets,
            width=22,
            state="readonly",
        )
        self.day_target_cb.grid(row=1, column=1, columnspan=2, sticky="w", padx=4, pady=(0, 4))
        ttk.Button(day_frame, text="Run day details", command=self._day_details).grid(row=1, column=3, sticky="w", padx=4, pady=(0, 4))

        snap_frame = ttk.LabelFrame(parent, text="Snapshot at time (local)")
        snap_frame.grid(row=4, column=0, sticky="ew", padx=4, pady=4)
        ttk.Label(snap_frame, text="At (date or ISO):").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.snapshot_cb = ttk.Combobox(
            snap_frame,
            textvariable=self.snapshot_var,
            values=self.available_run_times,
            width=22,
            state="readonly",
        )
        self.snapshot_cb.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Button(snap_frame, text="Pick", command=self._pick_snapshot_date).grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Label(snap_frame, text="Type:").grid(row=0, column=3, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            snap_frame,
            textvariable=self.snapshot_type_var,
            values=["both", "followers", "followings"],
            width=12,
            state="readonly",
        ).grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Label(snap_frame, text="Target:").grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))
        self.snapshot_target_cb = ttk.Combobox(
            snap_frame,
            textvariable=self.snapshot_target_var,
            values=self.available_targets,
            width=22,
            state="readonly",
        )
        self.snapshot_target_cb.grid(row=1, column=1, columnspan=2, sticky="w", padx=4, pady=(0, 4))
        ttk.Button(snap_frame, text="Snapshot", command=self._snapshot_custom).grid(row=1, column=3, sticky="w", padx=4, pady=(0, 4))

        refresh_frame = ttk.Frame(parent)
        refresh_frame.grid(row=5, column=0, sticky="ew", padx=4, pady=(2, 4))
        ttk.Button(refresh_frame, text="Refresh options from DB", command=self._refresh_dates_clicked).grid(
            row=0, column=0, sticky="w"
        )

    def _build_daily_tab(self, parent):
        parent.columnconfigure(0, weight=1)

        daily_frame = ttk.LabelFrame(parent, text="Daily compare (DB live)")
        daily_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        daily_frame.columnconfigure(0, weight=1)

        daily_controls = ttk.Frame(daily_frame)
        daily_controls.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        ttk.Label(daily_controls, text="Target:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.daily_target_cb = ttk.Combobox(
            daily_controls,
            textvariable=self.daily_target_var,
            values=self.available_targets,
            width=22,
            state="readonly",
        )
        self.daily_target_cb.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(daily_controls, text="Type:").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            daily_controls,
            textvariable=self.daily_type_var,
            values=["both", "followers", "followings"],
            width=12,
            state="readonly",
        ).grid(row=0, column=3, sticky="w", padx=4, pady=4)
        ttk.Button(daily_controls, text="Load daily table", command=self._load_daily_compare).grid(
            row=0, column=4, sticky="w", padx=6, pady=4
        )
        ttk.Button(daily_controls, text="Load selected day details", command=self._load_selected_day_details).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 4)
        )
        ttk.Button(daily_controls, text="Export selected day CSV", command=self._export_selected_day_csv).grid(
            row=1, column=2, columnspan=2, sticky="w", padx=4, pady=(0, 4)
        )

        daily_table_frame = ttk.Frame(daily_frame)
        daily_table_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 4))
        daily_table_frame.columnconfigure(0, weight=1)
        daily_table_frame.rowconfigure(0, weight=1)
        self.daily_tree = ttk.Treeview(
            daily_table_frame,
            columns=("day", "new_followers", "lost_followers", "new_followings", "lost_followings"),
            show="headings",
            height=7,
        )
        for col, label, width in [
            ("day", "Day", 110),
            ("new_followers", "New followers", 120),
            ("lost_followers", "Lost followers", 120),
            ("new_followings", "New followings", 130),
            ("lost_followings", "Lost followings", 130),
        ]:
            self.daily_tree.heading(col, text=label)
            self.daily_tree.column(col, width=width, anchor="center", stretch=True)
        daily_y_scroll = ttk.Scrollbar(daily_table_frame, orient="vertical", command=self.daily_tree.yview)
        daily_x_scroll = ttk.Scrollbar(daily_table_frame, orient="horizontal", command=self.daily_tree.xview)
        self.daily_tree.configure(yscrollcommand=daily_y_scroll.set, xscrollcommand=daily_x_scroll.set)
        self.daily_tree.grid(row=0, column=0, sticky="nsew")
        daily_y_scroll.grid(row=0, column=1, sticky="ns")
        daily_x_scroll.grid(row=1, column=0, sticky="ew")
        self.daily_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_daily_select())

        daily_detail_frame = ttk.Frame(daily_frame)
        daily_detail_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        daily_detail_frame.columnconfigure(0, weight=1)
        daily_detail_frame.columnconfigure(1, weight=1)

        new_box = ttk.LabelFrame(daily_detail_frame, text="New on selected day")
        new_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        new_box.columnconfigure(0, weight=1)
        new_box.rowconfigure(0, weight=1)
        self.daily_new_tree = ttk.Treeview(new_box, columns=("type", "username", "at"), show="headings", height=8)
        self.daily_new_tree.heading("type", text="Type")
        self.daily_new_tree.heading("username", text="Username")
        self.daily_new_tree.heading("at", text="Seen at (local)")
        self.daily_new_tree.column("type", width=85, anchor="center")
        self.daily_new_tree.column("username", width=210, anchor="w", stretch=True)
        self.daily_new_tree.column("at", width=165, anchor="center")
        daily_new_scroll = ttk.Scrollbar(new_box, orient="vertical", command=self.daily_new_tree.yview)
        self.daily_new_tree.configure(yscrollcommand=daily_new_scroll.set)
        self.daily_new_tree.grid(row=0, column=0, sticky="nsew")
        daily_new_scroll.grid(row=0, column=1, sticky="ns")

        lost_box = ttk.LabelFrame(daily_detail_frame, text="Lost on selected day")
        lost_box.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        lost_box.columnconfigure(0, weight=1)
        lost_box.rowconfigure(0, weight=1)
        self.daily_lost_tree = ttk.Treeview(lost_box, columns=("type", "username", "at"), show="headings", height=8)
        self.daily_lost_tree.heading("type", text="Type")
        self.daily_lost_tree.heading("username", text="Username")
        self.daily_lost_tree.heading("at", text="Lost at (local)")
        self.daily_lost_tree.column("type", width=85, anchor="center")
        self.daily_lost_tree.column("username", width=210, anchor="w", stretch=True)
        self.daily_lost_tree.column("at", width=165, anchor="center")
        daily_lost_scroll = ttk.Scrollbar(lost_box, orient="vertical", command=self.daily_lost_tree.yview)
        self.daily_lost_tree.configure(yscrollcommand=daily_lost_scroll.set)
        self.daily_lost_tree.grid(row=0, column=0, sticky="nsew")
        daily_lost_scroll.grid(row=0, column=1, sticky="ns")

    def _build_db_tools_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        db_tools_frame = ttk.LabelFrame(parent, text="Database maintenance")
        db_tools_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        db_tools_frame.columnconfigure(0, weight=1)
        db_tools_frame.columnconfigure(1, weight=1)
        buttons = [
            ("Preview merge from DB...", self._db_preview_merge),
            ("Merge from DB...", self._db_apply_merge),
            ("Preview cleanup targets", self._db_cleanup_preview),
            ("Apply cleanup targets", self._db_cleanup_apply),
            ("DB integrity check", self._db_integrity_check),
            ("DB vacuum", self._db_vacuum),
        ]
        for idx, (label, command) in enumerate(buttons):
            row = idx // 2
            col = idx % 2
            ttk.Button(db_tools_frame, text=label, command=command).grid(
                row=row, column=col, sticky="ew", padx=4, pady=4
            )

    def _build_output_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        output_controls = ttk.Frame(parent)
        output_controls.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ttk.Button(output_controls, text="Save output", command=self._save_output).grid(row=0, column=0, sticky="w")
        ttk.Button(output_controls, text="Clear output", command=self._clear_output).grid(row=0, column=1, sticky="w", padx=6)

        output_frame = ttk.LabelFrame(parent, text="Report output")
        output_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.output_text = tk.Text(output_frame, height=20, wrap="none")
        y_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        x_scroll = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output_text.xview)
        self.output_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

    def _set_message(self, text):
        self.message_var.set(text)

    def _is_monitor_mode(self):
        return bool(self.session_monitor_only.get())

    def _apply_control_mode(self):
        if not hasattr(self, "start_btn"):
            return
        state = "disabled" if self._is_monitor_mode() else "normal"
        self.start_btn.configure(state=state)
        self.stop_btn.configure(state=state)
        self.login_btn.configure(state=state)

    def _cookie_health_text(self):
        cookie_file = ROOT_DIR / "instagram_cookies.json"
        if not cookie_file.exists():
            return "Cookie: missing"
        age_hours = (time.time() - cookie_file.stat().st_mtime) / 3600.0
        if age_hours < 24:
            return f"Cookie: present ({age_hours:.1f}h old)"
        return f"Cookie: present ({age_hours / 24.0:.1f}d old)"

    def _last_error_text(self):
        if not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0:
            return "Last error: none"
        try:
            with open(LOG_PATH, "rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - 65536), os.SEEK_SET)
                data = handle.read().decode("utf-8", errors="replace")
            lines = [line.strip() for line in data.splitlines() if line.strip()]
            for line in reversed(lines):
                if "[ERROR]" in line:
                    if len(line) > 140:
                        line = line[:137] + "..."
                    return f"Last error: {line}"
        except Exception:
            pass
        return "Last error: none"

    def _recent_login_issue(self):
        if not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0:
            return None
        try:
            with open(LOG_PATH, "rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - 131072), os.SEEK_SET)
                text = handle.read().decode("utf-8", errors="replace")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            fail_tokens = (
                "Saved cookies are invalid or expired",
                "Failed to login, aborting",
                "Reason: login_failed",
                "Reason: login_failed_after_cookie_invalid",
            )
            success_tokens = (
                "Successfully logged in using saved cookies!",
                "Successfully logged in!",
            )
            fail_line = None
            fail_ts = None
            success_ts = None
            for line in lines:
                line_ts = _parse_log_timestamp(line)
                if any(token in line for token in fail_tokens):
                    fail_line = line
                    fail_ts = line_ts
                if any(token in line for token in success_tokens):
                    success_ts = line_ts
            if fail_line:
                return {
                    "line": fail_line,
                    "fail_ts": fail_ts,
                    "success_ts": success_ts,
                }
        except Exception:
            return None
        return None

    def _freshness_text(self):
        last_success = _read_last_success_run()
        if not last_success:
            return "Freshness: no successful runs yet"
        ts = last_success.get("finished_at") or last_success.get("started_at")
        if not ts:
            return "Freshness: unknown"
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds() / 3600.0
        if age_hours < 1:
            return f"Freshness: {age_hours * 60:.0f} min since success"
        return f"Freshness: {age_hours:.1f} h since success"

    def _open_env_file(self):
        _open_path(ENV_PATH)

    def _env_value_configured(self, key):
        value = (os.getenv(key, "") or "").strip()
        if not value:
            return False
        if value.lower().startswith("your_"):
            return False
        if value in {"account_to_track", "your_username", "your_password"}:
            return False
        return True

    def _run_wizard_checks(self):
        checks = []

        env_exists = ENV_PATH.exists()
        checks.append(("Env file", "PASS" if env_exists else "FAIL", str(ENV_PATH)))

        missing_keys = [k for k in REQUIRED_ENV_KEYS if not self._env_value_configured(k)]
        if missing_keys:
            checks.append(("Required config", "FAIL", f"Missing/placeholder: {', '.join(missing_keys)}"))
        else:
            checks.append(("Required config", "PASS", "IG_USERNAME / IG_PASSWORD / TARGET_ACCOUNT configured"))

        has_selenium = importlib.util.find_spec("selenium") is not None
        has_wdm = importlib.util.find_spec("webdriver_manager") is not None
        dep_ok = has_selenium and has_wdm
        checks.append(("Dependencies", "PASS" if dep_ok else "FAIL", "selenium + webdriver_manager"))

        cookie_path = ROOT_DIR / "instagram_cookies.json"
        cookie_ok = cookie_path.exists() and cookie_path.stat().st_size > 10
        login_issue = self._recent_login_issue()
        if not cookie_ok:
            checks.append(("Cookie file", "WARN", "Run login-only once if missing"))
        else:
            warn_message = None
            if login_issue:
                fail_line = login_issue.get("line")
                fail_ts = login_issue.get("fail_ts")
                success_ts = login_issue.get("success_ts")
                cookie_mtime = datetime.fromtimestamp(cookie_path.stat().st_mtime).astimezone()
                has_unresolved_fail = fail_ts and (not success_ts or fail_ts > success_ts)
                if has_unresolved_fail and cookie_mtime <= fail_ts.astimezone():
                    warn_message = f"Present but login failed recently: {fail_line}"
            if warn_message:
                checks.append(("Cookie file", "WARN", warn_message))
            else:
                checks.append(("Cookie file", "PASS", "Present and no active login failures found"))

        db_exists = DB_PATH.exists()
        run_count = 0
        if db_exists:
            try:
                conn = sqlite3.connect(str(DB_PATH), timeout=1)
                try:
                    run_count = conn.execute("SELECT COUNT(1) FROM run_history").fetchone()[0]
                finally:
                    conn.close()
            except Exception:
                pass
        checks.append(("Database", "PASS" if db_exists else "WARN", f"{DB_PATH} | runs: {run_count}"))

        task_detected = False
        task_note = "Not detected"
        if sys.platform.startswith("win"):
            try:
                result = subprocess.run(
                    ["schtasks", "/Query", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=8,
                )
                text = (result.stdout or "").lower()
                if (
                    "main.py" in text
                    or "ig-tracker-cli.exe" in text
                    or "ig-followers-and-following" in text
                ):
                    task_detected = True
                    task_note = "Task Scheduler entry detected"
            except Exception:
                task_note = "Could not query Task Scheduler"
        checks.append(("Scheduler", "PASS" if task_detected else "WARN", task_note))

        if task_detected and not MONITOR_ONLY:
            checks.append(("Monitor-only mode", "WARN", "Set GUI_MONITOR_ONLY=true to avoid double runs"))
            if not self._auto_mode_applied:
                self.session_monitor_only.set(True)
                self._apply_control_mode()
                self._auto_mode_applied = True
        else:
            checks.append(("Monitor-only mode", "PASS", "Current mode is safe"))

        self._render_wizard_checks(checks)

    def _render_wizard_checks(self, checks):
        for row in self.wizard_tree.get_children():
            self.wizard_tree.delete(row)
        fail_count = 0
        warn_count = 0
        for check_name, status, details in checks:
            if status == "FAIL":
                fail_count += 1
            elif status == "WARN":
                warn_count += 1
            self.wizard_tree.insert("", "end", values=(check_name, status, details))

        if fail_count:
            self.wizard_summary_var.set(f"{fail_count} check(s) failed, {warn_count} warning(s). Fix failures first.")
        elif warn_count:
            self.wizard_summary_var.set(f"All required checks passed with {warn_count} warning(s).")
        else:
            self.wizard_summary_var.set("All checks passed. Tracker is ready.")

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
                    run_rows = conn.execute(
                        "SELECT run_started_at FROM run_history ORDER BY run_started_at DESC LIMIT 5000"
                    ).fetchall()
                    if not run_rows:
                        run_rows = conn.execute(
                            "SELECT timestamp FROM counts ORDER BY timestamp DESC LIMIT 5000"
                        ).fetchall()
                    target_rows = conn.execute(
                        "SELECT username FROM targets ORDER BY username"
                    ).fetchall()
                    snapshot_rows = conn.execute(
                        "SELECT run_started_at FROM run_history ORDER BY run_started_at DESC LIMIT 200"
                    ).fetchall()
                finally:
                    conn.close()
                day_values = []
                for row in run_rows:
                    if not row or not row[0]:
                        continue
                    day_value = _to_local_day(row[0])
                    if day_value:
                        day_values.append(day_value)
                dates = sorted(set(day_values), reverse=True)
                targets = [row[0] for row in target_rows if row and row[0]]
                run_times = []
                for row in snapshot_rows:
                    if not row or not row[0]:
                        continue
                    local_ts = _to_local_iso_datetime(row[0])
                    if local_ts:
                        run_times.append(local_ts)
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
            run_times = [datetime.now().replace(microsecond=0).isoformat()]

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
        if hasattr(self, "daily_target_cb"):
            daily_values = ["(all)"] + [value for value in self.available_targets if value]
            self.daily_target_cb.configure(values=daily_values)
            if not self.daily_target_var.get():
                self.daily_target_var.set("(all)")

    def _refresh_dates_clicked(self):
        self._load_available_dates()
        self._load_daily_compare(show_message=False)
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
            self._load_daily_compare(show_message=False)
            self._last_options_refresh = time.time()
        self.cookie_status_var.set(self._cookie_health_text())
        self.error_status_var.set(self._last_error_text())
        self.stale_status_var.set(self._freshness_text())
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
        if self._is_monitor_mode():
            self._set_message("Monitor-only mode enabled; tracker controls are disabled.")
            return
        _start_tracker()
        self._set_message("Tracker started.")

    def _stop_tracker_clicked(self):
        if self._is_monitor_mode():
            self._set_message("Monitor-only mode enabled; tracker controls are disabled.")
            return
        _stop_tracker()
        self._set_message("Tracker stopped.")

    def _login_only_clicked(self):
        if self._is_monitor_mode():
            self._set_message("Monitor-only mode enabled; tracker controls are disabled.")
            return
        _run_login_only()
        self._set_message("Login-only started (visible browser).")

    def _clear_tree(self, tree):
        for row in tree.get_children():
            tree.delete(row)

    def _query_daily_rows(self, target_name, list_type):
        if not DB_PATH.exists():
            return []
        conn = sqlite3.connect(str(DB_PATH), timeout=2)
        try:
            new_rows = conn.execute(
                """
                SELECT ff.first_seen_run_at,
                       ff.is_follower
                FROM followers_followings ff
                JOIN targets t ON t.id = ff.target_id
                WHERE ff.first_seen_run_at IS NOT NULL
                  AND (? = '' OR t.username = ?)
                """,
                (target_name, target_name),
            ).fetchall()
            lost_rows = conn.execute(
                """
                SELECT ff.lost_at_run_at,
                       ff.is_follower
                FROM followers_followings ff
                JOIN targets t ON t.id = ff.target_id
                WHERE ff.lost_at_run_at IS NOT NULL
                  AND (? = '' OR t.username = ?)
                """,
                (target_name, target_name),
            ).fetchall()
        finally:
            conn.close()

        daily = {}
        for ts_value, is_follower in new_rows:
            day = _to_local_day(ts_value)
            if not day:
                continue
            entry = daily.setdefault(day, {"new_followers": 0, "lost_followers": 0, "new_followings": 0, "lost_followings": 0})
            if int(is_follower) == 1:
                entry["new_followers"] += 1
            else:
                entry["new_followings"] += 1
        for ts_value, is_follower in lost_rows:
            day = _to_local_day(ts_value)
            if not day:
                continue
            entry = daily.setdefault(day, {"new_followers": 0, "lost_followers": 0, "new_followings": 0, "lost_followings": 0})
            if int(is_follower) == 1:
                entry["lost_followers"] += 1
            else:
                entry["lost_followings"] += 1

        ordered_days = sorted(daily.keys())
        result = []
        for day in ordered_days:
            row = daily[day]
            if list_type == "followers":
                row["new_followings"] = None
                row["lost_followings"] = None
            elif list_type == "followings":
                row["new_followers"] = None
                row["lost_followers"] = None
            result.append({"day": day, **row})

        days_limit = self._get_days()
        if days_limit > 0:
            result = result[-days_limit:]
        result.reverse()
        return result

    def _query_day_changes(self, day_str, target_name, list_type, event_type):
        if not DB_PATH.exists():
            return []
        ts_col = "first_seen_run_at" if event_type == "new" else "lost_at_run_at"
        type_sql = ""
        if list_type == "followers":
            type_sql = " AND ff.is_follower = 1"
        elif list_type == "followings":
            type_sql = " AND ff.is_follower = 0"
        start_utc, end_utc = _local_day_to_utc_range(day_str)

        conn = sqlite3.connect(str(DB_PATH), timeout=2)
        try:
            rows = conn.execute(
                f"""
                SELECT ff.follower_following_username, ff.is_follower, ff.{ts_col}
                FROM followers_followings ff
                JOIN targets t ON t.id = ff.target_id
                WHERE ff.{ts_col} IS NOT NULL
                  AND ff.{ts_col} >= ?
                  AND ff.{ts_col} <= ?
                  AND (? = '' OR t.username = ?)
                  {type_sql}
                ORDER BY ff.{ts_col} ASC, ff.follower_following_username ASC
                """,
                (start_utc, end_utc, target_name, target_name),
            ).fetchall()
        finally:
            conn.close()
        return rows

    def _load_daily_compare(self, show_message=True):
        prev_day = self._selected_daily_day() or (self.day_var.get() or "").strip()
        self._clear_tree(self.daily_tree)
        self._clear_tree(self.daily_new_tree)
        self._clear_tree(self.daily_lost_tree)
        target_name = (self.daily_target_var.get() or "").strip()
        if target_name == "(all)":
            target_name = ""
        list_type = self.daily_type_var.get() or "both"
        try:
            rows = self._query_daily_rows(target_name, list_type)
        except Exception as e:
            self._set_message(f"Daily compare failed: {e}")
            return
        if not rows:
            if show_message:
                self._set_message("No daily counts found in DB.")
            return

        for row in rows:
            new_followers = "-" if row["new_followers"] is None else str(row["new_followers"])
            lost_followers = "-" if row["lost_followers"] is None else str(row["lost_followers"])
            new_followings = "-" if row["new_followings"] is None else str(row["new_followings"])
            lost_followings = "-" if row["lost_followings"] is None else str(row["lost_followings"])
            self.daily_tree.insert(
                "",
                "end",
                values=(row["day"], new_followers, lost_followers, new_followings, lost_followings),
            )

        self._suppress_daily_select = True
        try:
            selected_item = None
            if prev_day:
                for item in self.daily_tree.get_children():
                    values = self.daily_tree.item(item, "values")
                    if values and str(values[0]) == prev_day:
                        selected_item = item
                        break
            if selected_item is None:
                children = self.daily_tree.get_children()
                if children:
                    selected_item = children[0]
            if selected_item is not None:
                self.daily_tree.selection_set(selected_item)
        finally:
            self._suppress_daily_select = False

        if self.daily_tree.selection():
            self._load_selected_day_details()
        if show_message:
            self._set_message("Daily compare loaded from DB.")

    def _selected_daily_day(self):
        selected = self.daily_tree.selection()
        if not selected:
            return None
        values = self.daily_tree.item(selected[0], "values")
        if not values:
            return None
        return str(values[0])

    def _on_daily_select(self):
        if self._suppress_daily_select:
            return
        day = self._selected_daily_day()
        if day:
            self.day_var.set(day)
            self._load_selected_day_details()

    def _load_selected_day_details(self):
        day = self._selected_daily_day()
        if not day:
            self._set_message("Select a day from Daily compare first.")
            return
        target_name = (self.daily_target_var.get() or "").strip()
        if target_name == "(all)":
            target_name = ""
        list_type = self.daily_type_var.get() or "both"
        try:
            new_rows = self._query_day_changes(day, target_name, list_type, "new")
            lost_rows = self._query_day_changes(day, target_name, list_type, "lost")
        except Exception as e:
            self._set_message(f"Day detail query failed: {e}")
            return

        self._clear_tree(self.daily_new_tree)
        self._clear_tree(self.daily_lost_tree)

        for username, is_follower, ts in new_rows:
            ff_type = "follower" if int(is_follower) == 1 else "following"
            self.daily_new_tree.insert("", "end", values=(ff_type, username, _format_dt(_parse_db_utc_dt(ts))))
        for username, is_follower, ts in lost_rows:
            ff_type = "follower" if int(is_follower) == 1 else "following"
            self.daily_lost_tree.insert("", "end", values=(ff_type, username, _format_dt(_parse_db_utc_dt(ts))))

        self._set_message(f"Day {day}: {len(new_rows)} new, {len(lost_rows)} lost.")

    def _export_selected_day_csv(self):
        day = self._selected_daily_day()
        if not day:
            self._set_message("Select a day from Daily compare first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export selected day details",
            initialfile=f"day_details_{day}.csv",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["event", "type", "username", "timestamp"])
                for item in self.daily_new_tree.get_children():
                    ff_type, username, ts = self.daily_new_tree.item(item, "values")
                    writer.writerow(["new", ff_type, username, ts])
                for item in self.daily_lost_tree.get_children():
                    ff_type, username, ts = self.daily_lost_tree.item(item, "values")
                    writer.writerow(["lost", ff_type, username, ts])
            self._set_message(f"Exported selected day to: {path}")
        except Exception as e:
            self._set_message(f"Export failed: {e}")

    def _run_db_tool(self, args, title, on_success=None):
        self._set_message("Running DB tool...")

        def _worker():
            cmd = _tool_cmd("db_tools.py", "ig-tracker-db-tools.exe")
            if not cmd:
                self.root.after(0, lambda: self._set_message("DB tool executable not found."))
                return
            result = subprocess.run(
                [*cmd, *args],
                cwd=str(ROOT_DIR),
                env=_tracker_env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            output = (result.stdout or "").strip()
            if result.stderr:
                output += ("\n\n[stderr]\n" + result.stderr.strip())
            if not output:
                output = "(no output)"
            header = f"{title} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
            text_out = header + ("-" * len(header)) + "\n" + output + "\n"

            def _update():
                self._set_output(text_out)
                if result.returncode == 0:
                    self._set_message("DB tool completed.")
                    self._load_available_dates()
                    self._load_daily_compare(show_message=False)
                    if on_success:
                        on_success()
                else:
                    self._set_message(f"DB tool failed with code {result.returncode}.")

            self.root.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()

    def _select_source_db(self):
        return filedialog.askopenfilename(
            title="Select source DB to merge",
            filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")],
            initialdir=str(ROOT_DIR),
        )

    def _db_preview_merge(self):
        src = self._select_source_db()
        if not src:
            self._set_message("Merge preview cancelled.")
            return
        self._run_db_tool(
            ["preview-merge", "--src", src, "--dest", str(DB_PATH)],
            "DB merge preview",
        )

    def _db_apply_merge(self):
        src = self._select_source_db()
        if not src:
            self._set_message("Merge cancelled.")
            return
        self._run_db_tool(
            ["merge", "--src", src, "--dest", str(DB_PATH)],
            "DB merge apply",
        )

    def _db_cleanup_preview(self):
        self._run_db_tool(
            ["cleanup-targets", "--dest", str(DB_PATH)],
            "Cleanup targets preview",
        )

    def _db_cleanup_apply(self):
        self._run_db_tool(
            ["cleanup-targets", "--dest", str(DB_PATH), "--apply"],
            "Cleanup targets apply",
        )

    def _db_integrity_check(self):
        self._run_db_tool(
            ["integrity-check", "--dest", str(DB_PATH)],
            "DB integrity check",
        )

    def _db_vacuum(self):
        self._run_db_tool(
            ["vacuum", "--dest", str(DB_PATH)],
            "DB vacuum",
        )

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
        at_utc = datetime.now().astimezone().astimezone(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat()
        self._run_report_to_text(["snapshot", "--at", at_utc, "--type", "both"], "Snapshot now")

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
        from_utc = _local_iso_to_utc_naive(from_dt)
        to_utc = _local_iso_to_utc_naive(to_dt)
        if not from_utc or not to_utc:
            self._set_message("Invalid local date/time format.")
            return
        rtype = self.range_type_var.get() or "both"
        target = (self.range_target_var.get() or "").strip()
        args = ["new", "--from", from_utc.isoformat(), "--to", to_utc.isoformat(), "--type", rtype]
        if target:
            args += ["--target", target]
        self._run_report_to_text(args, "New in range")

    def _lost_in_range(self):
        from_dt, to_dt = self._get_range_inputs()
        if not from_dt or not to_dt:
            self._set_message("Please fill From and To (ISO).")
            return
        from_utc = _local_iso_to_utc_naive(from_dt)
        to_utc = _local_iso_to_utc_naive(to_dt)
        if not from_utc or not to_utc:
            self._set_message("Invalid local date/time format.")
            return
        rtype = self.range_type_var.get() or "both"
        target = (self.range_target_var.get() or "").strip()
        args = ["lost", "--from", from_utc.isoformat(), "--to", to_utc.isoformat(), "--type", rtype]
        if target:
            args += ["--target", target]
        self._run_report_to_text(args, "Lost in range")

    def _day_details(self):
        day = (self.day_var.get() or "").strip()
        if not day:
            self._set_message("Please enter date YYYY-MM-DD.")
            return
        try:
            from_utc, to_utc = _local_day_to_utc_range(day)
        except ValueError:
            self._set_message("Invalid date format. Use YYYY-MM-DD.")
            return
        rtype = self.day_type_var.get() or "both"
        target = (self.day_target_var.get() or "").strip()
        self._run_local_day_details_report(day, from_utc, to_utc, rtype, target)

    def _snapshot_custom(self):
        at = (self.snapshot_var.get() or "").strip()
        rtype = self.snapshot_type_var.get() or "both"
        target = (self.snapshot_target_var.get() or "").strip()
        args = ["snapshot", "--type", rtype]
        if at:
            if len(at) == 10:
                at = f"{at}T00:00:00"
            at_utc = _local_iso_to_utc_naive(at)
            if not at_utc:
                self._set_message("Invalid local date/time for snapshot.")
                return
            args += ["--at", at_utc.isoformat()]
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
            cmd = _tool_cmd("report.py", "ig-tracker-report.exe")
            if not cmd:
                self.root.after(0, lambda: self._set_message("Report executable not found."))
                return
            env = _tracker_env({"RICH_COLOR_SYSTEM": "none", "TERM": "dumb"})
            run_args = ["--tz", "local", *args] if "--tz" not in args else args
            result = subprocess.run(
                [*cmd, *run_args],
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

    def _run_local_day_details_report(self, local_day, from_utc, to_utc, rtype, target):
        self._set_message("Running local day report...")

        def _worker():
            cmd = _tool_cmd("report.py", "ig-tracker-report.exe")
            if not cmd:
                self.root.after(0, lambda: self._set_message("Report executable not found."))
                return
            env = _tracker_env({"RICH_COLOR_SYSTEM": "none", "TERM": "dumb"})
            sections = []
            for label, command in [
                (
                    f"New on local day {local_day}",
                    ["new", "--from", from_utc, "--to", to_utc, "--type", rtype],
                ),
                (
                    f"Lost on local day {local_day}",
                    ["lost", "--from", from_utc, "--to", to_utc, "--type", rtype],
                ),
            ]:
                if target:
                    command += ["--target", target]
                command = ["--tz", "local", *command]
                result = subprocess.run(
                    [*cmd, *command],
                    cwd=str(ROOT_DIR),
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                section_text = result.stdout or ""
                if result.stderr:
                    section_text += "\n[stderr]\n" + result.stderr
                sections.append((label, section_text.strip(), result.returncode))

            header = f"Local day details {local_day} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
            text_out = header + ("-" * len(header)) + "\n"
            max_code = 0
            for label, section_text, code in sections:
                max_code = max(max_code, code)
                text_out += f"\n[{label}]\n{section_text}\n"

            def _update():
                self._set_output(text_out)
                if max_code == 0:
                    self._set_message("Local day report ready.")
                else:
                    self._set_message("Local day report finished with errors.")

            self.root.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()


def main():
    root = tk.Tk()
    TrackerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
