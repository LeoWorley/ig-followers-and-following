# Troubleshooting

## Login/cookie issues

- Symptom: saved cookie is invalid or expired.
- Fix: run login-only mode again with a visible browser:
```bash
LOGIN_ONLY_MODE=true HEADLESS_MODE=false python main.py
```

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

- Check `tracker.log` and `run_history` status in DB.
- Enable alerts:
```env
ALERTS_ENABLED=true
ALERT_CHANNELS=webhook,desktop
ALERT_STALE_SUCCESS_HOURS=6
```

## Unicode decode error in GUI output

- Already handled with fallback decoding.
- Update to latest code if you still see decode exceptions.
