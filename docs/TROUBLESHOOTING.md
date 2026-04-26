# Troubleshooting

## Login/cookie issues

- Symptom: saved cookie is invalid or expired.
- Fix from installer GUI: open `IG Tracker GUI`, then click `Run login-only now`.
- Fix from source: run login-only mode again with a visible browser:
```bash
LOGIN_ONLY_MODE=true HEADLESS_MODE=false python main.py
```

If Instagram shows a 2FA or security challenge, complete it in the browser and wait until the tracker saves `instagram_cookies.json`.

## Chrome stays in Task Manager

- Keep `FORCE_KILL_CHROME=true`.
- In Task Scheduler set: **If already running -> Do not start a new instance**.
- Check `tracker.log` for `Script finished`.

## GUI/tray looks stale

- Click refresh in GUI.
- Lower polling interval in `.env`:
```env
GUI_OPTIONS_POLL_SECONDS=15
TRAY_STATUS_POLL_SECONDS=5
```

## Task Scheduler runs but no fresh data

- In the GUI, click `Run setup checks` and confirm `Background task` is detected.
- Open Windows Task Scheduler and look for a task named `IG Tracker`.
- Check `tracker.log` and `run_history` status in DB.
- If you see duplicate-run messages, keep GUI/tray in monitor-only mode.
- Enable alerts:
```env
ALERTS_ENABLED=true
ALERT_CHANNELS=webhook,desktop
ALERT_STALE_SUCCESS_HOURS=6
```

## Background setup fails in GUI

- Confirm required setup checks pass before enabling background tracking.
- The cookie file must exist before background tracking is enabled.
- Reinstall or repair the app if the GUI says `ig-tracker-cli.exe` is missing.
- The default background task is per-user and runs after Windows login. Use the advanced Windows service path only if it must run before login.

## Unicode decode error in GUI output

- Already handled with fallback decoding.
- Update to latest code if you still see decode exceptions.
