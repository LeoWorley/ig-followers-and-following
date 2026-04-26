# Advanced / Developer Notes

## Runtime controls

- Single-instance lock:
  - `LOCK_FILE=tracker.lock`
  - `DISABLE_RUN_LOCK=false`
- Loop timing:
  - `RUN_INTERVAL_MINUTES`
  - `RUN_JITTER_SECONDS`
- Scrape limits:
  - `SCRAPE_MODAL_WAIT_SECONDS`
  - `SCRAPE_STALL_TIMEOUT_SECONDS`
  - `SCRAPE_MAX_ITERATIONS`

## Source setup

Windows:
```powershell
.\setup.ps1
.\start_gui.ps1
```

macOS/Linux:
```bash
./setup.sh
./start_gui.sh
```

For first-time login from source, use the GUI `Run login-only now` button or run the platform `login_once` script.

## Advanced Windows services

The default installer flow uses a per-user Task Scheduler entry named `IG Tracker`.

Use the GUI `Windows Services` section only if you need a machine-level service that runs without user login. That path requires `nssm.exe` and a Windows administrator prompt.

## Remote web access

The web dashboard defaults to disabled/local-only for new installs. Generate web auth from the GUI, then review `docs/MOBILE_DASHBOARD.md`, `docs/CADDY_DUCKDNS.md`, and `docs/OPERATIONS.md` before exposing it beyond the local machine or tailnet.

## DB maintenance

- Optional runtime maintenance:
  - `DB_INTEGRITY_CHECK_EVERY_RUNS=0`
  - `DB_VACUUM_EVERY_RUNS=0`
- Manual tools:
```bash
python db_tools.py export
python db_tools.py preview-merge --src /path/to/source.db
python db_tools.py merge --src /path/to/source.db
python db_tools.py cleanup-targets --dest instagram_tracker.db
python db_tools.py cleanup-targets --dest instagram_tracker.db --apply
```

## Packaging

- Build local standalone binaries:
```powershell
.\build_apps.ps1
```
```bash
./build_apps.sh
```

- Build Windows release artifacts (portable zip + installer EXE):
```powershell
.\build_windows_release.ps1 -Version 1.0.0
```

- Build zip only (no installer):
```powershell
.\build_windows_release.ps1 -Version 1.0.0 -NoInstaller
```

## Reporting CLI

- `summary`, `daily`, `day`, `new`, `lost`, `snapshot`, `list`
- timezone display:
```bash
python report.py --tz UTC summary --days 7
python report.py --tz America/New_York day --date 2026-01-31
```
