# Instagram Follower/Following Tracker

Track changes in followers and following over time, store history in SQLite, and inspect changes using CLI reports, a tray app, or a GUI.

## Highlights

- Headless background tracking with cookie-based login reuse.
- Login-only mode for first-time login/2FA cookie capture.
- Run history + daily counts + new/lost/snapshot reports.
- GUI and tray monitor apps for non-CLI usage.
- DB export/merge utilities for moving data across machines.

## Docs map

- `docs/QUICK_START.md` - fastest setup path.
- `docs/TROUBLESHOOTING.md` - common issues and fixes.
- `docs/ADVANCED.md` - runtime tuning, db tools, packaging.
- `docs/MOBILE_DASHBOARD.md` - mobile web dashboard via Tailscale.
- `docs/CADDY_DUCKDNS.md` - DuckDNS HTTPS access for Jellyfin and the web dashboard.
- `docs/OPERATIONS.md` - local operations runbook.
- `docs/ARCHITECTURE.md` - system architecture and boundaries.
- `docs/CLOUD_MIGRATION.md` - migration path from local to cloud.
- `docs/MANUAL_TESTS.md` - manual validation scenarios.

## Quick Start (recommended)

### Windows (installer EXE, easiest for non-technical users)

Use this path if you want to install and run the app without Python/venv.

1. Download installer from Releases:
   - `ig-tracker-setup-vX.Y.Z.exe`
2. Run installer and complete wizard.
   - Default install path: `%LOCALAPPDATA%\Programs\IG Tracker`
   - Recommended installer task: "Offer background tracking setup after first login"
   - Optional tray task: "Run tray monitor at Windows startup"
3. Open Start Menu:
   - `IG Tracker GUI`
4. In the GUI wizard, enter:
   - Instagram username
   - Instagram password
   - Account to track
5. Click `Save account settings`.
6. Click `Run login-only now`, complete IG login/2FA in browser, wait until cookie is saved.
7. Click `Run setup checks` and confirm required checks are healthy.
8. Click `Enable background tracking`.
   - The GUI creates a per-user Windows Task Scheduler entry named `IG Tracker`.
   - GUI/tray switch to monitor-only mode after background tracking is enabled.
9. Optional monitor app:
   - Start Menu -> `IG Tracker Tray`

If IG password/session changes later, run `Run login-only now` again to refresh cookies.

### Windows (from source repo)

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
.\login_once.ps1
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
./login_once.sh
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
  - `SCRAPE_MIN_COVERAGE_FOR_LOST` (default 0.9, skips lost marking on low-coverage scrapes)
  - `SCRAPE_MIN_REFERENCE_COUNT_FOR_LOST` (default 100)
- Authentication safety:
  - `STOP_ON_AUTH_FAILURE` (default `true`, exits loop when auth fails)
  - `DELETE_INVALID_COOKIE_ON_FAIL` (default `true`, removes stale cookie file)
- Optional SQLite maintenance:
  - `DB_INTEGRITY_CHECK_EVERY_RUNS` (0 disables)
  - `DB_VACUUM_EVERY_RUNS` (0 disables)
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
  - time since last successful run
- Responsive layout for smaller screens (optimized for 1366x768):
  - tabbed sections: `Overview`, `Reports`, `Daily Compare`, `DB Tools`, `Output`
  - vertical scrolling inside tabs to avoid clipped controls
  - compact multi-row forms (no horizontal form scrolling)
- In-app reports rendered directly (with optional "Save output").
- Daily compare view from DB (no file export required):
  - per-day new/lost counts (followers + followings)
  - selectable day details showing new/lost usernames
  - export selected day details to CSV
- DB tools in GUI:
  - preview merge from another `.db`
  - apply merge
  - preview/apply invalid target cleanup
  - integrity check and vacuum actions

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
- Tray menu includes "Open GUI" for full report and DB tools access.
- Optional Windows startup shortcut:
  - install: `.\register_tray_startup.ps1`
  - remove: `.\register_tray_startup.ps1 -Remove`

## Mobile Web Dashboard (`web_app.py`)

Private, read-only dashboard for phone access to tracker data.

- Security model:
  - Access from Tailnet only (recommended).
  - HTTP Basic Auth in app (`WEB_AUTH_USER` / `WEB_AUTH_PASS`).
- Default bind:
  - `WEB_HOST=0.0.0.0`
  - `WEB_PORT=8088`
- Start scripts:
  - Windows: `.\start_web.ps1`
  - macOS/Linux: `./start_web.sh`
- Open from phone:
  - `http://<tailscale-ip>:8088`

API endpoints:
- `GET /api/v1/health`
- `GET /api/v1/targets`
- `GET /api/v1/overview`
- `GET /api/v1/daily`
- `GET /api/v1/day`
- `GET /api/v1/current`

Profile links:
- usernames in web day details and current snapshot are clickable
- selected target can be opened via `Open target profile`
- GUI daily detail tables support opening profile on username double-click

## Packaging (standalone binaries)

Build standalone executables with PyInstaller (`--onefile`):

- Windows:
  - `.\build_apps.ps1`
- macOS/Linux:
  - `./build_apps.sh`

Use skip-install mode if PyInstaller is already installed:
- PowerShell: `.\build_apps.ps1 -SkipInstall`
- Bash: `./build_apps.sh --skip-install`

Generated executables:
- `dist\ig-tracker-gui.exe`
- `dist\ig-tracker-tray.exe`
- `dist\ig-tracker-cli.exe`
- `dist\ig-tracker-report.exe`
- `dist\ig-tracker-db-tools.exe`

### Windows installer + release artifacts

1. Install Inno Setup 6 (for installer EXE):
   - https://jrsoftware.org/isdl.php
2. Build release artifacts:
```powershell
.\build_windows_release.ps1 -Version 1.0.0
```
3. Outputs:
   - portable zip: `release\windows\ig-tracker-windows-v1.0.0-portable.zip`
   - installer exe (if Inno Setup found): `release\windows\ig-tracker-setup-v1.0.0.exe`

If you only want the portable zip:
```powershell
.\build_windows_release.ps1 -Version 1.0.0 -NoInstaller
```

### Publish first GitHub release (Windows EXE)

1. Push commits/tags:
```powershell
git tag v1.0.0
git push origin main --tags
```
2. Create release on GitHub and upload:
   - `release\windows\ig-tracker-setup-v1.0.0.exe`
   - `release\windows\ig-tracker-windows-v1.0.0-portable.zip`

## DevOps (GitHub Actions)

This repo includes lightweight CI/CD automation:

- CI workflow: `.github/workflows/ci.yml`
  - triggers on `push` to `main` and every `pull_request`
  - installs dependencies from `requirements.txt`
  - compiles all Python files (`py_compile`) to catch syntax/import-time issues early
  - runs CLI smoke checks:
    - `python report.py --help`
    - `python db_tools.py --help`
- Release workflow: `.github/workflows/release.yml`
  - triggers on tags like `v1.0.1`
  - builds Windows binaries and release artifacts (`.exe` + portable `.zip`)
  - uploads artifacts to the workflow run
  - publishes assets to the GitHub Release automatically
- Dependency automation: `.github/dependabot.yml`
  - weekly update PRs for Python packages and GitHub Actions

### CI usage

Open a PR to `main`; checks run automatically. Merge only when CI is green.

### CD usage (automatic release by tag)

```powershell
git add .
git commit -m "chore(release): v1.0.1"
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin main
git push origin v1.0.1
```

After the tag push:

- GitHub Actions builds the Windows artifacts.
- A GitHub Release for `v1.0.1` is created/updated with:
  - `ig-tracker-setup-v1.0.1.exe`
  - `ig-tracker-windows-v1.0.1-portable.zip`

### Manual fallback

If Actions is unavailable, you can still build and publish locally using:

- `.\build_windows_release.ps1 -Version X.Y.Z`
- then upload files from `release\windows\` in the GitHub Releases UI.

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

DB integrity check:
```bash
python db_tools.py integrity-check --dest instagram_tracker.db
```

DB vacuum:
```bash
python db_tools.py vacuum --dest instagram_tracker.db
```

Rollback lost flags from a bad run (preview):
```bash
python db_tools.py rollback-lost --run-started-at "2026-02-08 18:29:36.780107"
```

Apply rollback:
```bash
python db_tools.py rollback-lost --run-started-at "2026-02-08 18:29:36.780107" --apply
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
STOP_ON_AUTH_FAILURE=true
SCRAPE_MIN_COVERAGE_FOR_LOST=0.9
```

## Troubleshooting

### "Saved cookies are invalid or expired"

Run login-only again with visible browser:

```bash
LOGIN_ONLY_MODE=true HEADLESS_MODE=false python main.py
```

If scheduler mode is enabled, auth failure now stops the loop by default (`STOP_ON_AUTH_FAILURE=true`) and sends alert events. This prevents accidental mass updates from bad sessions.

### Unexpected mass "lost" entries after a bad run

Use scrape safety guard to prevent marking all items as lost when Instagram returns partial/blocked lists:

```env
SCRAPE_MIN_COVERAGE_FOR_LOST=0.9
SCRAPE_MIN_REFERENCE_COUNT_FOR_LOST=100
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
