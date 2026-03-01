# Operations Runbook

This runbook focuses on local operation (single host) with private mobile access.

## Services

1. Tracker service: collects Instagram data and writes to SQLite.
2. Web service: serves read-only API/UI over `instagram_tracker.db`.

Keep both services as separate processes.

## Daily checks

1. Confirm tracker health in mobile dashboard (`Health` section).
2. Verify `minutes_since_success` is within expected interval.
3. Confirm no auth failures in `tracker.log`.

## Start/Stop procedures

### Tracker

- Start: `.\start_tracker.ps1`
- Stop: terminate tracker process from Task Manager or scheduler action.

### Web dashboard

- Start: `.\start_web.ps1`
- Stop: terminate `uvicorn` process.

## Backup routine

Recommended daily DB export:

```powershell
.\venv\Scripts\python.exe db_tools.py export
```

Generated exports are ignored by git and safe to sync to private storage.

## Incident response

1. `login_failed` / `auth` alerts:
   - Run login-only flow and refresh cookie.
2. stale success:
   - Check tracker lock/process and `tracker.log` errors.
3. DB integrity warnings:
   - Run `db_tools.py integrity-check`.
   - Restore latest backup if needed.

## Security checklist

1. Keep `WEB_AUTH_PASS` strong and private.
2. Never expose web service directly to public internet.
3. Access only over Tailscale.
4. Keep `.env`, cookies, DB files and logs out of git.

## Capacity notes

Current model is SQLite single-node local runtime.

For cloud migration strategy, see `docs/CLOUD_MIGRATION.md`.
