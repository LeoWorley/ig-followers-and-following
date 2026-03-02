# Mobile Web Dashboard (Private via Tailscale)

This dashboard adds a mobile-first web view for the existing local tracker database.

- Runtime model: tracker process and web process run independently.
- Access model: private Tailnet access + HTTP Basic Auth (second barrier).
- Data model: read-only queries against `instagram_tracker.db`.

## 1. Prerequisites

1. Tracker project already configured and running on the machine.
2. Tailscale installed and connected on:
   - host machine
   - phone/tablet
3. `.env` configured with web settings:

```env
WEB_ENABLED=true
WEB_HOST=0.0.0.0
WEB_PORT=8088
WEB_TZ=America/Hermosillo
WEB_AUTH_USER=admin
WEB_AUTH_PASS=change_this_now
```

## 2. Install dependencies

From project root:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 3. Start web dashboard

### Windows

```powershell
.\start_web.ps1
```

### Linux/macOS

```bash
./start_web.sh
```

## 4. Open from phone

Use host Tailnet IP + port:

`http://<tailscale-ip>:8088`

The browser will request Basic Auth credentials (`WEB_AUTH_USER` / `WEB_AUTH_PASS`).

## 5. Supported views

1. Health (`/api/v1/health`)
2. Overview today (`/api/v1/overview`)
3. Daily changes (`/api/v1/daily`)
4. Day detail (`/api/v1/day`)
5. Current list snapshot (`/api/v1/current`)

## 6. Profile links behavior

1. Usernames shown in web lists are clickable profile links:
   - `Selected Day New`
   - `Selected Day Lost`
   - `Current Snapshot`
2. Selected target can be opened via `Open target profile`.
3. Link format is always:
   - `https://www.instagram.com/<username>/`
4. On mobile devices, this URL usually opens the Instagram app if installed; otherwise it opens the browser.

## 7. GUI shortcut

In desktop GUI (`gui_app.py`), you can double-click usernames in:

1. `New on selected day`
2. `Lost on selected day`

This opens the same Instagram profile URL in your default browser/app handler.

## 8. Troubleshooting

1. `401 Unauthorized`
   - Validate `WEB_AUTH_USER` and `WEB_AUTH_PASS`.
2. `503 Database not found`
   - Ensure `instagram_tracker.db` exists in project root or set `WEB_DB_PATH`.
3. Phone cannot open URL
   - Confirm both devices are in Tailscale and Tailnet ACL allows access.
4. Empty data
   - Confirm tracker has completed at least one successful run.
