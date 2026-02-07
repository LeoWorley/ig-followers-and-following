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
