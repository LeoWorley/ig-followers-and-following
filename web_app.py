import os
import secrets
import sqlite3
import base64
import hashlib
import hmac
import json
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pytz


ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
load_dotenv(ROOT_DIR / ".env")

WEB_ENABLED = os.getenv("WEB_ENABLED", "true").lower() == "true"
WEB_DB_PATH = Path(os.getenv("WEB_DB_PATH") or (ROOT_DIR / "instagram_tracker.db"))
WEB_TZ = os.getenv("WEB_TZ", "America/Hermosillo")
WEB_AUTH_MODE = os.getenv("WEB_AUTH_MODE", "session").strip().lower()
WEB_AUTH_USER = os.getenv("WEB_AUTH_USER", "admin")
WEB_AUTH_PASS = os.getenv("WEB_AUTH_PASS")
WEB_AUTH_PASSWORD_HASH = os.getenv("WEB_AUTH_PASSWORD_HASH", "")
WEB_SESSION_SECRET = os.getenv("WEB_SESSION_SECRET", "")
WEB_SESSION_COOKIE_NAME = os.getenv("WEB_SESSION_COOKIE_NAME", "ig_tracker_session")
WEB_SESSION_COOKIE_SECURE = os.getenv("WEB_SESSION_COOKIE_SECURE", "false").lower() == "true"
WEB_SESSION_TTL_SECONDS = int(os.getenv("WEB_SESSION_TTL_SECONDS", "43200"))
WEB_LOGIN_RATE_LIMIT_ATTEMPTS = int(os.getenv("WEB_LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
WEB_LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("WEB_LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
LOCK_FILE = Path(os.getenv("LOCK_FILE", "tracker.lock"))
if not LOCK_FILE.is_absolute():
    LOCK_FILE = ROOT_DIR / LOCK_FILE

app = FastAPI(title="IG Tracker Web", version="0.2.0")
VALID_TYPES = {"followers", "followings", "both"}
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}

if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


def _resolve_tz(tz_name: Optional[str]) -> tzinfo:
    value = (tz_name or WEB_TZ).strip()
    if value.lower() in {"local", ""}:
        return datetime.now().astimezone().tzinfo
    try:
        return ZoneInfo(value)
    except Exception:
        try:
            return pytz.timezone(value)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid timezone: {value}") from exc


def _normalize_type(list_type: str) -> str:
    value = (list_type or "both").strip().lower()
    if value not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {list_type}")
    return value


def _b64_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _verify_password_hash(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, digest = stored_hash.split("$", 3)
        iterations = int(iterations_raw)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256" or iterations < 100000:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return secrets.compare_digest(_b64_encode(candidate), digest)


def _password_ok(password: str) -> bool:
    if WEB_AUTH_PASSWORD_HASH:
        return _verify_password_hash(password, WEB_AUTH_PASSWORD_HASH)
    if WEB_AUTH_PASS:
        return secrets.compare_digest(password, WEB_AUTH_PASS)
    return False


def _session_secret() -> bytes:
    if WEB_SESSION_SECRET:
        return WEB_SESSION_SECRET.encode("utf-8")
    fallback = f"{WEB_AUTH_USER}:{WEB_AUTH_PASSWORD_HASH or WEB_AUTH_PASS or 'change_this_now'}"
    return fallback.encode("utf-8")


def _sign_payload(payload: str) -> str:
    signature = hmac.new(_session_secret(), payload.encode("ascii"), hashlib.sha256).digest()
    return _b64_encode(signature)


def _create_session_cookie(username: str) -> str:
    now = int(time.time())
    payload = _b64_encode(
        json.dumps(
            {
                "u": username,
                "iat": now,
                "exp": now + WEB_SESSION_TTL_SECONDS,
                "nonce": secrets.token_urlsafe(12),
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return f"{payload}.{_sign_payload(payload)}"


def _read_session_cookie(request: Request) -> Optional[str]:
    raw = request.cookies.get(WEB_SESSION_COOKIE_NAME)
    if not raw or "." not in raw:
        return None
    payload, signature = raw.rsplit(".", 1)
    if not secrets.compare_digest(_sign_payload(payload), signature):
        return None
    try:
        data = json.loads(_b64_decode(payload))
    except Exception:
        return None
    if int(data.get("exp", 0)) < int(time.time()):
        return None
    username = str(data.get("u", ""))
    if not secrets.compare_digest(username, WEB_AUTH_USER):
        return None
    return username


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def _rate_limited(ip_address: str) -> bool:
    now = time.time()
    window_start = now - WEB_LOGIN_RATE_LIMIT_WINDOW_SECONDS
    attempts = [ts for ts in _LOGIN_ATTEMPTS.get(ip_address, []) if ts >= window_start]
    _LOGIN_ATTEMPTS[ip_address] = attempts
    return len(attempts) >= WEB_LOGIN_RATE_LIMIT_ATTEMPTS


def _record_failed_login(ip_address: str):
    _LOGIN_ATTEMPTS.setdefault(ip_address, []).append(time.time())


def _clear_failed_logins(ip_address: str):
    _LOGIN_ATTEMPTS.pop(ip_address, None)


def _require_api_user(request: Request):
    username = _read_session_cookie(request)
    if username:
        return username
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")


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


def _to_tz_iso(value, tz: tzinfo) -> Optional[str]:
    dt_value = _parse_db_dt(value)
    if dt_value is None:
        return None
    return dt_value.astimezone(tz).isoformat(timespec="seconds")


def _to_tz_day(value, tz: tzinfo) -> Optional[str]:
    dt_value = _parse_db_dt(value)
    if dt_value is None:
        return None
    return dt_value.astimezone(tz).date().isoformat()


def _day_bounds_utc_naive(day_value: date, tz: tzinfo):
    start_local = datetime.combine(day_value, dt_time.min, tzinfo=tz)
    end_local = datetime.combine(day_value, dt_time.max, tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _ensure_iso_date(day_str: str) -> date:
    try:
        return datetime.fromisoformat(day_str).date()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {day_str} (expected YYYY-MM-DD)") from exc


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if _read_session_cookie(request):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {"error": None, "username": WEB_AUTH_USER})


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    ip_address = _client_ip(request)
    if _rate_limited(ip_address):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Too many failed attempts. Try again in a few minutes.", "username": WEB_AUTH_USER},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    body = (await request.body()).decode("utf-8")
    form = parse_qs(body, keep_blank_values=True)
    username = form.get("username", [""])[0].strip()
    password = form.get("password", [""])[0]

    if not secrets.compare_digest(username, WEB_AUTH_USER) or not _password_ok(password):
        _record_failed_login(ip_address)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid username or password.", "username": username or WEB_AUTH_USER},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    _clear_failed_logins(ip_address)
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        WEB_SESSION_COOKIE_NAME,
        _create_session_cookie(username),
        max_age=WEB_SESSION_TTL_SECONDS,
        httponly=True,
        secure=WEB_SESSION_COOKIE_SECURE,
        samesite="lax",
    )
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(WEB_SESSION_COOKIE_NAME, secure=WEB_SESSION_COOKIE_SECURE, samesite="lax")
    return response


@app.get("/", response_class=HTMLResponse)
def index(request: Request, _enabled: None = Depends(_ensure_enabled)):
    if not _read_session_cookie(request):
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"default_tz": WEB_TZ},
    )


@app.get("/api/v1/health")
def api_health(
    tz: Optional[str] = Query(default=None),
    _enabled: None = Depends(_ensure_enabled),
    _user: str = Depends(_require_api_user),
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
    _user: str = Depends(_require_api_user),
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
    _user: str = Depends(_require_api_user),
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


@app.get("/api/v1/daily")
def api_daily(
    days: int = Query(default=30, ge=1, le=365),
    target: str = Query(default=""),
    type: str = Query(default="both"),
    tz: Optional[str] = Query(default=None),
    _enabled: None = Depends(_ensure_enabled),
    _user: str = Depends(_require_api_user),
):
    tzinfo = _resolve_tz(tz)
    target = target.strip()
    list_type = _normalize_type(type)

    end_local_day = datetime.now(tzinfo).date()
    start_local_day = end_local_day - timedelta(days=days - 1)
    start_utc, _ = _day_bounds_utc_naive(start_local_day, tzinfo)
    _, end_utc = _day_bounds_utc_naive(end_local_day, tzinfo)

    with _open_db() as conn:
        new_rows = conn.execute(
            """
            SELECT ff.first_seen_run_at, ff.is_follower
            FROM followers_followings ff
            JOIN targets t ON t.id = ff.target_id
            WHERE ff.first_seen_run_at IS NOT NULL
              AND ff.first_seen_run_at >= ?
              AND ff.first_seen_run_at <= ?
              AND (? = '' OR t.username = ?)
              AND (
                ? = 'both'
                OR (? = 'followers' AND ff.is_follower = 1)
                OR (? = 'followings' AND ff.is_follower = 0)
              )
            """,
            (start_utc, end_utc, target, target, list_type, list_type, list_type),
        ).fetchall()
        lost_rows = conn.execute(
            """
            SELECT ff.lost_at_run_at, ff.is_follower
            FROM followers_followings ff
            JOIN targets t ON t.id = ff.target_id
            WHERE ff.lost_at_run_at IS NOT NULL
              AND ff.lost_at_run_at >= ?
              AND ff.lost_at_run_at <= ?
              AND (? = '' OR t.username = ?)
              AND (
                ? = 'both'
                OR (? = 'followers' AND ff.is_follower = 1)
                OR (? = 'followings' AND ff.is_follower = 0)
              )
            """,
            (start_utc, end_utc, target, target, list_type, list_type, list_type),
        ).fetchall()

    buckets = {}
    cursor_day = start_local_day
    while cursor_day <= end_local_day:
        buckets[cursor_day.isoformat()] = {
            "new_followers": 0,
            "lost_followers": 0,
            "new_followings": 0,
            "lost_followings": 0,
        }
        cursor_day = cursor_day + timedelta(days=1)

    for row in new_rows:
        day_key = _to_tz_day(row["first_seen_run_at"], tzinfo)
        if day_key not in buckets:
            continue
        if int(row["is_follower"]) == 1:
            buckets[day_key]["new_followers"] += 1
        else:
            buckets[day_key]["new_followings"] += 1

    for row in lost_rows:
        day_key = _to_tz_day(row["lost_at_run_at"], tzinfo)
        if day_key not in buckets:
            continue
        if int(row["is_follower"]) == 1:
            buckets[day_key]["lost_followers"] += 1
        else:
            buckets[day_key]["lost_followings"] += 1

    rows = []
    for day_key in sorted(buckets.keys(), reverse=True):
        entry = buckets[day_key]
        if list_type == "followers":
            entry["new_followings"] = None
            entry["lost_followings"] = None
        elif list_type == "followings":
            entry["new_followers"] = None
            entry["lost_followers"] = None
        rows.append({"day": day_key, **entry})

    return {
        "target": target or None,
        "type": list_type,
        "days": days,
        "rows": rows,
        "tz_used": str(tzinfo),
    }


@app.get("/api/v1/day")
def api_day(
    date: str = Query(...),
    target: str = Query(default=""),
    type: str = Query(default="both"),
    tz: Optional[str] = Query(default=None),
    _enabled: None = Depends(_ensure_enabled),
    _user: str = Depends(_require_api_user),
):
    tzinfo = _resolve_tz(tz)
    target = target.strip()
    list_type = _normalize_type(type)
    day_value = _ensure_iso_date(date)
    start_utc, end_utc = _day_bounds_utc_naive(day_value, tzinfo)

    with _open_db() as conn:
        new_rows = conn.execute(
            """
            SELECT
              t.username AS target_username,
              ff.follower_following_username,
              ff.is_follower,
              ff.first_seen_run_at AS ts
            FROM followers_followings ff
            JOIN targets t ON t.id = ff.target_id
            WHERE ff.first_seen_run_at IS NOT NULL
              AND ff.first_seen_run_at >= ?
              AND ff.first_seen_run_at <= ?
              AND (? = '' OR t.username = ?)
              AND (
                ? = 'both'
                OR (? = 'followers' AND ff.is_follower = 1)
                OR (? = 'followings' AND ff.is_follower = 0)
              )
            ORDER BY ff.first_seen_run_at ASC, ff.follower_following_username ASC
            """,
            (start_utc, end_utc, target, target, list_type, list_type, list_type),
        ).fetchall()
        lost_rows = conn.execute(
            """
            SELECT
              t.username AS target_username,
              ff.follower_following_username,
              ff.is_follower,
              ff.lost_at_run_at AS ts
            FROM followers_followings ff
            JOIN targets t ON t.id = ff.target_id
            WHERE ff.lost_at_run_at IS NOT NULL
              AND ff.lost_at_run_at >= ?
              AND ff.lost_at_run_at <= ?
              AND (? = '' OR t.username = ?)
              AND (
                ? = 'both'
                OR (? = 'followers' AND ff.is_follower = 1)
                OR (? = 'followings' AND ff.is_follower = 0)
              )
            ORDER BY ff.lost_at_run_at ASC, ff.follower_following_username ASC
            """,
            (start_utc, end_utc, target, target, list_type, list_type, list_type),
        ).fetchall()

    def _shape(rows):
        payload = []
        for row in rows:
            payload.append(
                {
                    "target": row["target_username"],
                    "username": row["follower_following_username"],
                    "type": "follower" if int(row["is_follower"]) == 1 else "following",
                    "timestamp_local": _to_tz_iso(row["ts"], tzinfo),
                }
            )
        return payload

    return {
        "date": day_value.isoformat(),
        "target": target or None,
        "type": list_type,
        "new": _shape(new_rows),
        "lost": _shape(lost_rows),
        "tz_used": str(tzinfo),
    }


@app.get("/api/v1/current")
def api_current(
    target: str = Query(default=""),
    type: str = Query(default="both"),
    limit: int = Query(default=5000, ge=1, le=20000),
    tz: Optional[str] = Query(default=None),
    _enabled: None = Depends(_ensure_enabled),
    _user: str = Depends(_require_api_user),
):
    tzinfo = _resolve_tz(tz)
    target = target.strip()
    list_type = _normalize_type(type)

    list_sql = ""
    if list_type == "followers":
        list_sql = " AND ff.is_follower = 1"
    elif list_type == "followings":
        list_sql = " AND ff.is_follower = 0"

    with _open_db() as conn:
        rows = conn.execute(
            f"""
            SELECT
              t.username AS target_username,
              ff.follower_following_username,
              ff.is_follower,
              ff.first_seen_run_at,
              ff.last_seen_run_at
            FROM followers_followings ff
            JOIN targets t ON t.id = ff.target_id
            WHERE ff.is_lost = 0
              AND (? = '' OR t.username = ?)
              {list_sql}
            ORDER BY ff.follower_following_username ASC
            LIMIT ?
            """,
            (target, target, limit),
        ).fetchall()

    payload = []
    for row in rows:
        payload.append(
            {
                "target": row["target_username"],
                "username": row["follower_following_username"],
                "type": "follower" if int(row["is_follower"]) == 1 else "following",
                "first_seen_local": _to_tz_iso(row["first_seen_run_at"], tzinfo),
                "last_seen_local": _to_tz_iso(row["last_seen_run_at"], tzinfo),
            }
        )

    return {
        "target": target or None,
        "type": list_type,
        "limit": limit,
        "rows": payload,
        "tz_used": str(tzinfo),
    }


@app.exception_handler(HTTPException)
def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )
