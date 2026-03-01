import os
import secrets
import sqlite3
from datetime import date, datetime, time as dt_time, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

WEB_ENABLED = os.getenv("WEB_ENABLED", "true").lower() == "true"
WEB_DB_PATH = Path(os.getenv("WEB_DB_PATH") or (ROOT_DIR / "instagram_tracker.db"))
WEB_TZ = os.getenv("WEB_TZ", "America/Hermosillo")
WEB_AUTH_USER = os.getenv("WEB_AUTH_USER", "admin")
WEB_AUTH_PASS = os.getenv("WEB_AUTH_PASS", "change_this_now")
LOCK_FILE = Path(os.getenv("LOCK_FILE", "tracker.lock"))
if not LOCK_FILE.is_absolute():
    LOCK_FILE = ROOT_DIR / LOCK_FILE

security = HTTPBasic()
app = FastAPI(title="IG Tracker Web", version="0.2.0")


def _resolve_tz(tz_name: Optional[str]) -> ZoneInfo:
    value = (tz_name or WEB_TZ).strip()
    try:
        return ZoneInfo(value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timezone: {value}") from exc


def _auth(credentials: HTTPBasicCredentials = Depends(security)):
    username_ok = secrets.compare_digest(credentials.username, WEB_AUTH_USER)
    password_ok = secrets.compare_digest(credentials.password, WEB_AUTH_PASS)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _ensure_enabled():
    if not WEB_ENABLED:
        raise HTTPException(status_code=503, detail="Web dashboard is disabled (WEB_ENABLED=false)")


def _open_db() -> sqlite3.Connection:
    if not WEB_DB_PATH.exists():
        raise HTTPException(status_code=503, detail=f"Database not found: {WEB_DB_PATH}")
    conn = sqlite3.connect(str(WEB_DB_PATH), timeout=2)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_db_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    dt_value = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def _to_tz_iso(value, tz: ZoneInfo) -> Optional[str]:
    dt_value = _parse_db_dt(value)
    if dt_value is None:
        return None
    return dt_value.astimezone(tz).isoformat(timespec="seconds")


def _day_bounds_utc_naive(day_value: date, tz: ZoneInfo):
    start_local = datetime.combine(day_value, dt_time.min, tzinfo=tz)
    end_local = datetime.combine(day_value, dt_time.max, tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


@app.get("/", response_class=HTMLResponse)
def index(_enabled: None = Depends(_ensure_enabled), _user: str = Depends(_auth)):
    return """
    <!doctype html>
    <html lang="en">
      <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
      <body>
        <h1>IG Tracker Web</h1>
        <p>API is active. UI will be enabled in the next iteration.</p>
      </body>
    </html>
    """


@app.get("/api/v1/health")
def api_health(
    tz: Optional[str] = Query(default=None),
    _enabled: None = Depends(_ensure_enabled),
    _user: str = Depends(_auth),
):
    tzinfo = _resolve_tz(tz)
    result = {
        "db_ok": False,
        "tracker_running_guess": LOCK_FILE.exists(),
        "last_run_started_at": None,
        "last_run_finished_at": None,
        "last_run_status": None,
        "last_success_at": None,
        "minutes_since_success": None,
        "server_time_local": datetime.now(tzinfo).isoformat(timespec="seconds"),
        "tz_used": str(tzinfo),
    }

    with _open_db() as conn:
        conn.execute("SELECT 1").fetchone()
        result["db_ok"] = True

        last_run = conn.execute(
            """
            SELECT run_started_at, run_finished_at, status
            FROM run_history
            ORDER BY run_started_at DESC
            LIMIT 1
            """
        ).fetchone()
        if last_run:
            result["last_run_started_at"] = _to_tz_iso(last_run["run_started_at"], tzinfo)
            result["last_run_finished_at"] = _to_tz_iso(last_run["run_finished_at"], tzinfo)
            result["last_run_status"] = last_run["status"]

        last_success = conn.execute(
            """
            SELECT run_finished_at, run_started_at
            FROM run_history
            WHERE status = 'success'
            ORDER BY run_started_at DESC
            LIMIT 1
            """
        ).fetchone()
        if last_success:
            success_at = last_success["run_finished_at"] or last_success["run_started_at"]
            success_dt = _parse_db_dt(success_at)
            result["last_success_at"] = _to_tz_iso(success_at, tzinfo)
            if success_dt:
                delta = datetime.now(timezone.utc) - success_dt
                result["minutes_since_success"] = int(delta.total_seconds() // 60)

    return result


@app.get("/api/v1/targets")
def api_targets(
    tz: Optional[str] = Query(default=None),
    _enabled: None = Depends(_ensure_enabled),
    _user: str = Depends(_auth),
):
    tzinfo = _resolve_tz(tz)
    with _open_db() as conn:
        rows = conn.execute("SELECT username FROM targets ORDER BY username ASC").fetchall()
    return {"targets": [row["username"] for row in rows], "tz_used": str(tzinfo)}


@app.get("/api/v1/overview")
def api_overview(
    target: str = Query(default=""),
    tz: Optional[str] = Query(default=None),
    _enabled: None = Depends(_ensure_enabled),
    _user: str = Depends(_auth),
):
    tzinfo = _resolve_tz(tz)
    target = target.strip()
    start_utc, end_utc = _day_bounds_utc_naive(datetime.now(tzinfo).date(), tzinfo)

    with _open_db() as conn:
        current = conn.execute(
            """
            SELECT
              SUM(CASE WHEN ff.is_follower = 1 AND ff.is_lost = 0 THEN 1 ELSE 0 END) AS current_followers,
              SUM(CASE WHEN ff.is_follower = 0 AND ff.is_lost = 0 THEN 1 ELSE 0 END) AS current_followings
            FROM followers_followings ff
            JOIN targets t ON t.id = ff.target_id
            WHERE (? = '' OR t.username = ?)
            """,
            (target, target),
        ).fetchone()

        new_today = conn.execute(
            """
            SELECT
              SUM(CASE WHEN ff.is_follower = 1 THEN 1 ELSE 0 END) AS new_today_followers,
              SUM(CASE WHEN ff.is_follower = 0 THEN 1 ELSE 0 END) AS new_today_followings
            FROM followers_followings ff
            JOIN targets t ON t.id = ff.target_id
            WHERE ff.first_seen_run_at IS NOT NULL
              AND ff.first_seen_run_at >= ?
              AND ff.first_seen_run_at <= ?
              AND (? = '' OR t.username = ?)
            """,
            (start_utc, end_utc, target, target),
        ).fetchone()

        lost_today = conn.execute(
            """
            SELECT
              SUM(CASE WHEN ff.is_follower = 1 THEN 1 ELSE 0 END) AS lost_today_followers,
              SUM(CASE WHEN ff.is_follower = 0 THEN 1 ELSE 0 END) AS lost_today_followings
            FROM followers_followings ff
            JOIN targets t ON t.id = ff.target_id
            WHERE ff.lost_at_run_at IS NOT NULL
              AND ff.lost_at_run_at >= ?
              AND ff.lost_at_run_at <= ?
              AND (? = '' OR t.username = ?)
            """,
            (start_utc, end_utc, target, target),
        ).fetchone()

    return {
        "target": target or None,
        "current_followers": int(current["current_followers"] or 0),
        "current_followings": int(current["current_followings"] or 0),
        "new_today_followers": int(new_today["new_today_followers"] or 0),
        "lost_today_followers": int(lost_today["lost_today_followers"] or 0),
        "new_today_followings": int(new_today["new_today_followings"] or 0),
        "lost_today_followings": int(lost_today["lost_today_followings"] or 0),
        "tz_used": str(tzinfo),
    }


@app.exception_handler(HTTPException)
def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
