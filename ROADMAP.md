# Roadmap – Instagram Follower/Following Tracker

## Goals
- Run as a background service (hourly) with minimal manual intervention.
- Capture when a follower/following was first seen (discovery time) and estimate when it was added/removed between runs.
- Provide easy reporting: current lists with timestamps, new/lost within a date range, and per-run change summaries.

## Near-term tasks
1) **Service scheduling**
   - Add an env var `RUN_INTERVAL_MINUTES` (default 60) to `main.py` instead of fixed 8am/8pm.
   - Optionally add a small random jitter to each run to reduce detection risk.
   - Provide a `systemd` unit example (Linux) and a `launchd` plist snippet (macOS) in the README for long-running usage.

2) **Per-run snapshots with timestamps (ground truth)**
   - Record run metadata (`run_id`, `run_started_at`, `run_finished_at`, `status`).
   - For each username per run, store `first_seen_run_at` (when first present) and `last_seen_run_at` (when last present).
   - When a record moves from present → absent, set `lost_at_run_at` to that run’s timestamp.

3) **Optional midpoint estimates (mark as derived)**
   - For a newly discovered user: `estimated_added_at = midpoint(last_run_without, first_run_with)`.
   - For removals: `estimated_removed_at = midpoint(last_run_with, first_run_without)`.
   - Keep estimates in separate nullable columns so reports can show both exact run times and fuzzy estimates.

4) **Change estimation logic (built on run data)**
   - Use the run-based timestamps above as truth; compute midpoint estimates only if desired.
   - Persist `run_history` table: `id`, `run_started_at`, `run_finished_at`, `status`, counts collected.

5) **Reporting CLI**
   - Add a new script `report.py` with subcommands:
     - `report.py new --from 2026-01-01 --to 2026-01-07` → list followers/followings first-seen in range.
     - `report.py lost --from ... --to ...`
     - `report.py snapshot --at 2026-01-23T12:00` → show state as of a run.
     - `report.py summary --days 7` → totals added/lost per day.
   - Output as pretty table; optional `--json` for machine use.
   - Add a friendly TUI/CLI menu (`python report.py --menu`) using e.g. `questionary`/`inquirer` to select common actions without remembering flags.

6) **README improvements**
   - Document the service mode, env vars (`RUN_INTERVAL_MINUTES`, `HEADLESS_MODE`, `LOGIN_ONLY_MODE`).
   - Add a “Usage examples” section for the new report commands.

7) **Resilience & observability**
   - Add structured logging (JSON or key/value) with run id; log counts scraped vs expected.
   - Retry scrape of modal if fewer than expected items collected (e.g., < 80% of visible count).
   - Add a `--dry-run` flag to skip DB writes during testing.

8) **Time & data hygiene**
   - Store all timestamps in UTC; allow report CLI to format in local time with a `--tz` option.
   - Add DB indexes on `first_seen_run_at`, `last_seen_run_at`, and `run_started_at` for fast range queries.
   - Add a retention/cleanup command to prune old `run_history` rows beyond N days while keeping the latest per-user state.
   - Note cookie/credential handling: keep `.env` and `instagram_cookies.json` out of git; document refresh steps.

## Nice-to-have
- Export CSV of new/lost within a range.
- Simple web dashboard (Flask/FastAPI) to browse changes.
- Slack/webhook notifier for each run summary.

## Implementation order
1) Scheduling + run_history table.
2) Timestamp fields & midpoint estimation.
3) Reporting CLI.
4) README/service docs.
5) Resilience/logging polish.
