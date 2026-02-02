# Roadmap - Instagram Follower/Following Tracker

## Product direction
- Make setup and daily use easy for non-technical users.
- Keep background tracking reliable on Windows/macOS.
- Make reporting easy to understand without command-line knowledge.

## What is already done
- Background loop with interval/jitter and login-only mode.
- Cookie reuse flow for 2FA accounts.
- Logging to rotating log files.
- Report CLI with new/lost/snapshot/summary/daily/day/list.
- Tray app and cross-platform GUI app.
- DB export and merge workflow.

## Next priorities (user-friendly first)

1) One-click setup and launch
- Add `setup.ps1` / `setup.sh` scripts:
  - create venv
  - install deps
  - create `.env` template
  - run login-only first-time flow
- Add one-click launchers for:
  - tracker
  - tray monitor
  - GUI monitor

2) Guided first-run wizard (inside GUI)
- Add a "First Run" wizard:
  - check Python/dependencies/Chrome
  - check `.env` required values
  - run login-only and confirm cookie saved
  - validate DB write + test report
- Show clear pass/fail checklist with fix buttons.

3) Monitor-only mode by default for non-technical users
- In GUI/tray, detect if Task Scheduler/launchd is active and suggest monitor-only.
- Add clear status chips:
  - tracker running/stopped
  - last successful run
  - last error
  - cookie status

4) Better in-app reporting UX (no CLI needed)
- Add built-in report tabs in GUI:
  - Daily counts chart
  - New/Lost lists
  - Snapshot viewer
- Add filters with dropdowns only (target/date/type).
- Add "Export current view" button (CSV/JSON/TXT).

5) Alerts and health checks
- Add optional notifications for:
  - login failed / cookie expired
  - run failed
  - no data updated for N hours
- Optional channels:
  - desktop toast
  - email
  - webhook

6) Safer data and merge tools
- Add GUI "Import DB" + "Merge preview":
  - show rows to insert/update before applying
  - auto-backup destination DB
- Add "Data cleanup" tools:
  - remove invalid targets
  - dedupe existing rows

7) Packaging for non-technical users
- Build standalone app packages:
  - Windows executable bundle
  - macOS app bundle
- Include auto-generated launcher shortcuts.

## Reliability improvements
- Add run lock file to prevent accidental parallel runs.
- Add explicit scrape timeout per modal phase.
- Add retry strategy when collected count is far below profile count.
- Add periodic DB integrity check and compact option.

## Documentation improvements
- Split README into:
  - Quick Start (5 minutes)
  - Troubleshooting
  - Advanced/Developer
- Add screenshot-based guide for:
  - first login
  - Task Scheduler setup
  - GUI report usage

## Suggested implementation order
1) One-click setup scripts + README Quick Start rewrite.
2) GUI first-run wizard + monitor-only defaults.
3) In-app report tabs and export buttons.
4) Alerts/health checks.
5) Packaging and installer-level polish.
