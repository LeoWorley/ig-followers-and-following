# Instagram Follower/Following Tracker

This project tracks daily changes in Instagram followers and following lists for a specified account. It maintains historical data and generates daily reports of changes.

## Features

- Daily monitoring of followers and following lists
- Tracks new followers and unfollowers
- Tracks new and removed following accounts
- Historical data storage
- Daily change reports
- View followers/following lists sorted by date added

## Setup

You can run this project either using a virtual environment or Docker.

### Option 1: Virtual Environment

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Instagram credentials:
```
IG_USERNAME=your_username
IG_PASSWORD=your_password
TARGET_ACCOUNT=account_to_track
# Optional:
# HEADLESS_MODE=true
# LOGIN_ONLY_MODE=false
# LOGIN_ONLY_TIMEOUT_SECONDS=600
# RUN_INTERVAL_MINUTES=60
# RUN_JITTER_SECONDS=120
# TRAY_AUTO_START=false
# TRAY_MONITOR_ONLY=false
# TRAY_LOG_PATH=tracker.log
# TRAY_REPORTS_DIR=reports
# TRAY_REPORT_DAYS=7
# TRAY_STATUS_POLL_SECONDS=5
# GUI_AUTO_START=false
# GUI_MONITOR_ONLY=false
# GUI_LOG_PATH=tracker.log
# GUI_REPORTS_DIR=reports
# GUI_REPORT_DAYS=7
# GUI_STATUS_POLL_SECONDS=5
# GUI_OPTIONS_POLL_SECONDS=30
```

4. Run the tracker:
```bash
python main.py
```

### Handling 2FA (recommended first run)

If your Instagram account has two‑factor auth turned on:

1. Set `HEADLESS_MODE=false` in your `.env` (or export it in the shell) so a visible Chrome window opens.
2. Run `python main.py` and log in; enter the 6‑digit 2FA code when Instagram prompts you.
3. On successful login the script saves a session to `instagram_cookies.json`.
4. Switch back to headless by removing `HEADLESS_MODE` (or setting it to `true`) for scheduled runs; the saved cookies will be reused.

If cookies expire (password change, new device/IP, etc.), repeat the headful steps above to refresh them.

**Login-only helper (when headless keeps refreshing):** set `LOGIN_ONLY_MODE=true` and `HEADLESS_MODE=false`, then run `python main.py`. It opens a visible browser so you can complete 2FA, waits for login to finish, saves `instagram_cookies.json`, and exits without scraping. You can press Enter in the terminal after you finish login/2FA to save cookies, or let it auto-detect the login. Set `LOGIN_ONLY_MODE` back to false afterward. Use `LOGIN_ONLY_TIMEOUT_SECONDS` (optional) to stop waiting after a set time.

**Quick start for 2FA users**
- Do one visible run (`HEADLESS_MODE=false`, `LOGIN_ONLY_MODE=true`) to generate `instagram_cookies.json`.
- Then schedule/run normally with `HEADLESS_MODE=true`, `LOGIN_ONLY_MODE=false`; the service will reuse the cookie on each run.
- If you ever change password or the cookie expires, repeat the visible login step.

### Running as a service

- Control frequency with `RUN_INTERVAL_MINUTES` (default 60) and optional `RUN_JITTER_SECONDS` to add a small random delay each cycle.
- The script now runs in an endless loop; use a process manager (systemd/launchd/supervisor) to keep it alive.
- **macOS (launchd):** create `~/Library/LaunchAgents/com.instagram.tracker.plist` that runs `cd /Users/<you>/dev/ig-follwers-and-following && source venv/bin/activate && set -a; source .env; set +a; caffeinate -dims python3 main.py >> /tmp/instagram-tracker.log 2>&1`, set `RunAtLoad` and `KeepAlive` to true, then `launchctl load ~/Library/LaunchAgents/com.instagram.tracker.plist`. Keep the lid closed but prevent sleep with `caffeinate -dims` (or `sudo pmset -a disablesleep 1`).
- **Windows (Task Scheduler, recommended):**
  1. Open Task Scheduler -> Create Task (not Basic Task).
  2. General tab: set Run whether user is logged on or not.
  3. Triggers tab: add your schedule (e.g., every 1 hour).
  4. Actions tab -> New:
     - Program/script: `C:\ig-followers-and-following\venv\Scripts\python.exe`
     - Add arguments: `main.py`
     - Start in: `C:\ig-followers-and-following`
  5. Conditions tab: optional, but make sure the PC won't sleep.
  6. Settings tab: enable Run task as soon as possible after a scheduled start is missed.

  Notes:
  - Make sure `.env` and `instagram_cookies.json` are in the project folder.
  - For scheduled runs, use `HEADLESS_MODE=true` and `LOGIN_ONLY_MODE=false`.
  - If you need 2FA, run one login-only session interactively first: set `LOGIN_ONLY_MODE=true`, `HEADLESS_MODE=false`, run `python main.py` in a normal terminal, complete login, then set `LOGIN_ONLY_MODE=false`.

### Tray app (Windows, optional)

Use this if you want a small tray icon that starts/stops the tracker directly.

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the tray app:
```bash
python tray_app.py
```

3. Run the tray app in background (no terminal):
```powershell
.\start_tray.ps1
```

Notes:
- The tray app only runs while you are logged in. If you need it running while logged off, use Task Scheduler instead.
- Closing the tray app will stop the tracker process.
- You can auto-start the tracker from the tray by setting `TRAY_AUTO_START=true`.
- If Task Scheduler is running the tracker, set `TRAY_MONITOR_ONLY=true` to avoid double runs.
- `TRAY_LOG_PATH` controls where logs are written (default `tracker.log`).
- `TRAY_REPORTS_DIR` controls where tray-generated reports are saved (default `reports`).
- `TRAY_REPORT_DAYS` controls the date range for the tray reports (default 7).
- `TRAY_STATUS_POLL_SECONDS` controls how often the tray tooltip updates.

### GUI app (Windows/macOS)

Use this if you want a full window with all report options (new/lost ranges, daily counts, day details, snapshot, exports).

1. Run the GUI app:
```bash
python gui_app.py
```

Notes:
- The GUI app can start/stop the tracker like the tray.
- If Task Scheduler is running the tracker, set `GUI_MONITOR_ONLY=true` to avoid double runs.
- You can auto-start the tracker from the GUI by setting `GUI_AUTO_START=true`.
- Report outputs are saved to `GUI_REPORTS_DIR` (default `reports`).
- The date picker uses `tkcalendar` (included in `requirements.txt`). Date/target/time dropdowns are populated from your DB.
- GUI options refresh automatically every `GUI_OPTIONS_POLL_SECONDS` (default 30), or via the refresh button.
- Reports now render inside the GUI; use "Save output" if you want to export a report to a file.

### Reporting

After data is collected you can query it with `python report.py`:

- `python report.py new --from 2026-01-01T00:00:00 --to 2026-01-07T23:59:59 --type followers`
- `python report.py lost --from 2026-01-01T00:00:00 --to 2026-01-07T23:59:59 --type followings`
- `python report.py snapshot --at 2026-01-23T12:00:00`
- `python report.py summary --days 7`
- `python report.py daily --days 7` (daily followers/followings counts)
- `python report.py day --date 2026-01-31` (counts + new/lost for a specific day)
- `python report.py list --type both --out-csv current.csv` (current followers/followings, export optional)
- Or interactive menu: `python report.py --menu`

### Database export/import (merge)

Use this when you want to move or merge data between machines (e.g., export from macOS and merge into Windows).

Export current DB:
```bash
python db_tools.py export
```

Merge another DB into the local one:
```bash
python db_tools.py merge --src /path/to/instagram_tracker.db
```

Notes:
- Merge creates a backup of your local DB by default (use `--no-backup` to skip).
- The merge prefers the earliest "first seen" date and the latest "last seen" date for each username/type.

### Option 2: Docker

1. Create a `.env` file with your Instagram credentials (same as above).

2. Build the Docker image:
```bash
docker build -t instagram-tracker .
```

3. Run the tracker in Docker:
```bash
docker run -it \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/instagram_cookies.json:/app/instagram_cookies.json \
  -v $(pwd)/instagram_tracker.db:/app/instagram_tracker.db \
  instagram-tracker
```

To run in background mode, add the `-d` flag:
```bash
docker run -d \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/instagram_cookies.json:/app/instagram_cookies.json \
  -v $(pwd)/instagram_tracker.db:/app/instagram_tracker.db \
  instagram-tracker
```

To view logs when running in background:
```bash
docker ps  # get the container ID
docker logs -f <container-id>
```

## Viewing Statistics

You can view your followers and following lists sorted by date added using the `show_stats.py` script:

### Using Virtual Environment:
```bash
python show_stats.py
```

### Using Docker:
```bash
docker run -it \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/instagram_tracker.db:/app/instagram_tracker.db \
  instagram-tracker python show_stats.py
```

This will display:
- All current followers, sorted by newest first
- Total number of followers
- All accounts you're following, sorted by newest first
- Total number of accounts you're following

## Configuration

The tracker runs daily at a specified time. You can modify the schedule in `main.py`.

## Data Storage

All data is stored in a SQLite database (`instagram_tracker.db`) with the following information:
- Daily follower snapshots
- Daily following snapshots
- Change logs

## Security Note

Please keep your `.env` file secure and never commit it to version control.

## License

This project is licensed under the [MIT License](LICENSE).
