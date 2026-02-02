# Instagram Follower/Following Tracker

Track changes in followers and following over time, store history in SQLite, and inspect changes using CLI reports, a tray app, or a GUI.

## Highlights

- Headless background tracking with cookie-based login reuse.
- Login-only mode for first-time login/2FA cookie capture.
- Run history + daily counts + new/lost/snapshot reports.
- GUI and tray monitor apps for non-CLI usage.
- DB export/merge utilities for moving data across machines.

## Quick Start (recommended)

### Windows

1. Run one-click setup:
```powershell
.\setup.ps1
```

2. Edit `.env` with real values:
```env
IG_USERNAME=your_username
IG_PASSWORD=your_password
TARGET_ACCOUNT=account_to_track
```

3. First-time login/2FA cookie capture:
```powershell
$env:LOGIN_ONLY_MODE="true"
$env:HEADLESS_MODE="false"
.\venv\Scripts\python.exe .\main.py
```

4. Set back to normal mode in `.env`:
```env
LOGIN_ONLY_MODE=false
HEADLESS_MODE=true
```

5. Launch the GUI monitor:
```powershell
.\start_gui.ps1
```

### macOS/Linux

1. Run one-click setup:
```bash
./setup.sh
```

2. Edit `.env` (same keys as Windows).
3. Run login-only once:
```bash
LOGIN_ONLY_MODE=true HEADLESS_MODE=false ./venv/bin/python main.py
```
4. Return to normal mode in `.env` (`LOGIN_ONLY_MODE=false`, `HEADLESS_MODE=true`).
5. Start GUI:
```bash
./start_gui.sh
```

## Running Modes

### Main tracker (`main.py`)

- Runs in an endless loop.
- Sleeps between runs using:
  - `RUN_INTERVAL_MINUTES` (default 60)
  - `RUN_JITTER_SECONDS` (default 120)
- Scrape safety limits:
  - `SCRAPE_MODAL_WAIT_SECONDS` (default 10)
  - `SCRAPE_STALL_TIMEOUT_SECONDS` (default 15)
  - `SCRAPE_MAX_ITERATIONS` (default 500)
- Uses a single-instance lock to avoid accidental parallel runs:
  - `LOCK_FILE` (default `tracker.lock`)
  - `DISABLE_RUN_LOCK` (default `false`)

### Login-only mode

Use when you need visible login/2FA and cookie refresh:

```env
LOGIN_ONLY_MODE=true
HEADLESS_MODE=false
```

The script waits for successful login, saves `instagram_cookies.json`, and exits.

### Logging

- Rotating file logs:
  - `LOG_FILE=tracker.log`
  - `LOG_LEVEL=INFO`
  - `LOG_MAX_BYTES=5242880`
  - `LOG_BACKUP_COUNT=3`
  - `LOG_CONSOLE=true`
- Optional Chrome process cleanup after each run:
  - `FORCE_KILL_CHROME=true`
- Optional alerting:
  - `ALERTS_ENABLED=true`
  - `ALERT_CHANNELS=webhook,desktop`
  - `ALERT_WEBHOOK_URL=https://your-endpoint.example/alerts`
  - `ALERT_COOLDOWN_SECONDS=1800`
  - `ALERT_STALE_SUCCESS_HOURS=6` (0 disables stale-run alert)
  - `ALERT_ON_SUCCESS=false`

## Background Service Setup

### Windows (Task Scheduler, recommended)

Create a task (not Basic Task):

- **General**
  - Run whether user is logged on or not
  - If task is already running: **Do not start a new instance**
- **Triggers**
  - At startup (recommended for endless-loop mode)
- **Actions**
  - Program/script: `C:\ig-followers-and-following\venv\Scripts\python.exe`
  - Add arguments: `main.py`
  - Start in: `C:\ig-followers-and-following`

If you use GUI/tray while Task Scheduler runs the tracker, use monitor-only:

```env
GUI_MONITOR_ONLY=true
TRAY_MONITOR_ONLY=true
```

### macOS (launchd)

Use a `LaunchAgent` to run `./venv/bin/python main.py` with your project as working directory.

## GUI App (`gui_app.py`)

The GUI is designed for non-technical users:

- First-run wizard checks:
  - `.env` exists
  - required vars are configured
  - dependencies available
  - cookie present
  - DB and scheduler status
- Monitor-only toggle for safe use with scheduler-managed runs.
- Health indicators:
  - cookie age
  - latest error from log
- In-app reports rendered directly (with optional "Save output").
- Daily compare view from DB (no file export required):
  - per-day followers/followings totals
  - per-day deltas
  - selectable day details showing new/lost usernames
- DB tools in GUI:
  - preview merge from another `.db`
  - apply merge
  - preview/apply invalid target cleanup

Run directly:
```bash
python gui_app.py
```

Or use launchers:
- Windows: `.\start_gui.ps1`
- macOS/Linux: `./start_gui.sh`

## Tray App (`tray_app.py`)

Small monitor/controller with report shortcuts.

- Windows launcher: `.\start_tray.ps1`
- macOS/Linux launcher: `./start_tray.sh`
- Auto monitor mode on Windows when Task Scheduler is detected:
  - `TRAY_AUTO_MONITOR_ON_SCHEDULER=true`

## Reports (`report.py`)

Examples:

```bash
python report.py summary --days 7
python report.py daily --days 7
python report.py day --date 2026-01-31
python report.py --tz UTC day --date 2026-01-31
python report.py --tz America/New_York summary --days 7
python report.py new --from 2026-01-01T00:00:00 --to 2026-01-07T23:59:59 --type both
python report.py lost --from 2026-01-01T00:00:00 --to 2026-01-07T23:59:59 --type both
python report.py snapshot --at 2026-01-23T12:00:00 --type both
python report.py list --type both --out-csv current.csv
python report.py --menu
```

## DB Export / Merge (`db_tools.py`)

Export:
```bash
python db_tools.py export
```

Preview merge (no changes):
```bash
python db_tools.py preview-merge --src /path/to/instagram_tracker.db
```

Merge:
```bash
python db_tools.py merge --src /path/to/instagram_tracker.db
```

Cleanup invalid targets (preview):
```bash
python db_tools.py cleanup-targets --dest instagram_tracker.db
```

Cleanup invalid targets (apply):
```bash
python db_tools.py cleanup-targets --dest instagram_tracker.db --apply
```

Custom target cleanup list:
```bash
python db_tools.py cleanup-targets --dest instagram_tracker.db --usernames followers following bogus_target --apply
```

## Environment Template

Use `.env.example` as a base. Common keys:

```env
IG_USERNAME=your_username
IG_PASSWORD=your_password
TARGET_ACCOUNT=account_to_track
HEADLESS_MODE=true
LOGIN_ONLY_MODE=false
RUN_INTERVAL_MINUTES=60
RUN_JITTER_SECONDS=120
TRAY_AUTO_MONITOR_ON_SCHEDULER=true
```

## Troubleshooting

### "Saved cookies are invalid or expired"

Run login-only again with visible browser:

```bash
LOGIN_ONLY_MODE=true HEADLESS_MODE=false python main.py
```

### Chrome remains in Task Manager after run

- Keep `FORCE_KILL_CHROME=true`.
- Ensure Task Scheduler is not launching parallel instances.
- Check `tracker.log` for `Script finished`.

### GUI shows stale options

Use "Refresh options from DB" or lower:

```env
GUI_OPTIONS_POLL_SECONDS=15
```

### Unicode decode errors in GUI report output

Already handled by decode fallback (`errors=replace`) in GUI report runner.

## Security Notes

- Never commit `.env`, `instagram_cookies.json`, `tracker.log`, or DB files.
- Rotate credentials if they were ever pushed.
- Keep local backups before running destructive cleanup operations.

## License

MIT
