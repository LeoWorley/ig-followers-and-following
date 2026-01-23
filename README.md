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
# RUN_INTERVAL_MINUTES=60
# RUN_JITTER_SECONDS=120
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

**Login-only helper (when headless keeps refreshing):** set `LOGIN_ONLY_MODE=true` and `HEADLESS_MODE=false`, then run `python main.py`. It opens a visible browser so you can complete 2FA, saves `instagram_cookies.json`, and exits without scraping. Set `LOGIN_ONLY_MODE` back to false afterward.

**Quick start for 2FA users**
- Do one visible run (`HEADLESS_MODE=false`, `LOGIN_ONLY_MODE=true`) to generate `instagram_cookies.json`.
- Then schedule/run normally with `HEADLESS_MODE=true`, `LOGIN_ONLY_MODE=false`; the service will reuse the cookie on each run.
- If you ever change password or the cookie expires, repeat the visible login step.

### Running as a service

- Control frequency with `RUN_INTERVAL_MINUTES` (default 60) and optional `RUN_JITTER_SECONDS` to add a small random delay each cycle.
- The script now runs in an endless loop; use a process manager (systemd/launchd/supervisor) to keep it alive.
- **macOS (launchd):** create `~/Library/LaunchAgents/com.instagram.tracker.plist` that runs `cd /Users/<you>/dev/ig-follwers-and-following && source venv/bin/activate && set -a; source .env; set +a; caffeinate -dims python3 main.py >> /tmp/instagram-tracker.log 2>&1`, set `RunAtLoad` and `KeepAlive` to true, then `launchctl load ~/Library/LaunchAgents/com.instagram.tracker.plist`. Keep the lid closed but prevent sleep with `caffeinate -dims` (or `sudo pmset -a disablesleep 1`).
- **Windows (Task Scheduler):** create a task that runs hourly, even when locked: `powershell -NoProfile -ExecutionPolicy Bypass -Command "cd C:\\path\\to\\ig-follwers-and-following; .\\venv\\Scripts\\Activate.ps1; setx IG_USERNAME '...'; setx IG_PASSWORD '...'; setx TARGET_ACCOUNT '...'; python main.py >> C:\\path\\to\\tracker.log 2>&1"`. Set “Run whether user is logged on or not” and disable sleep in Power Options.

### Reporting

After data is collected you can query it with `python report.py`:

- `python report.py new --from 2026-01-01T00:00:00 --to 2026-01-07T23:59:59 --type followers`
- `python report.py lost --from 2026-01-01T00:00:00 --to 2026-01-07T23:59:59 --type followings`
- `python report.py snapshot --at 2026-01-23T12:00:00`
- `python report.py summary --days 7`
- `python report.py list --type both --out-csv current.csv` (current followers/followings, export optional)
- Or interactive menu: `python report.py --menu`

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
