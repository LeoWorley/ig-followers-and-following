# Architecture

## Context

This project tracks follower/following changes for a target Instagram account and stores history in SQLite.

The web dashboard introduces a private mobile read-only interface without changing tracker write flows.

## Components

1. `main.py` (tracker loop)
   - handles login/session/cookies
   - scrapes followers/followings
   - writes run history and changes into SQLite
2. `instagram_tracker.db` (single source of truth)
   - `targets`
   - `run_history`
   - `followers_followings`
   - `counts`
3. `report.py`, `db_tools.py`
   - reporting and database maintenance/exports
4. `web_app.py`
   - FastAPI read-only API
   - Basic Auth gate
   - serves mobile dashboard static UI
5. `web/static/*`
   - vanilla JS client consuming `/api/v1/*`

## Data Flow

1. Tracker writes snapshots and change timestamps to SQLite.
2. Web API reads SQLite with filtered queries and timezone projection.
3. Mobile UI requests API and renders:
   - health
   - overview
   - daily series
   - day detail
   - current snapshot

No write operations are exposed in web endpoints.

## Security Boundaries

1. Network boundary: private Tailnet.
2. Application boundary: HTTP Basic Auth.
3. Source control boundary: secrets/data/log artifacts excluded by `.gitignore`.

## Operational Boundaries

1. SQLite is local and single-node.
2. Tracker and web are independent processes.
3. Dashboard is intentionally read-only for lower risk.

## Scalability Notes

Current architecture is optimized for local reliability and low maintenance.

Future-ready choices:
1. API layer separates presentation from storage.
2. Query endpoints can be reused behind reverse proxy/cloud ingress.
3. Read-only contract simplifies migration to managed DB replicas or service split.
