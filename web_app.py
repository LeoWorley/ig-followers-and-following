import os
import secrets
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

WEB_ENABLED = os.getenv("WEB_ENABLED", "true").lower() == "true"
WEB_DB_PATH = Path(os.getenv("WEB_DB_PATH") or (ROOT_DIR / "instagram_tracker.db"))
WEB_TZ = os.getenv("WEB_TZ", "America/Hermosillo")
WEB_AUTH_USER = os.getenv("WEB_AUTH_USER", "admin")
WEB_AUTH_PASS = os.getenv("WEB_AUTH_PASS", "change_this_now")

security = HTTPBasic()
app = FastAPI(title="IG Tracker Web", version="0.1.0")


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


def _open_db() -> sqlite3.Connection:
    if not WEB_DB_PATH.exists():
        raise HTTPException(status_code=503, detail=f"Database not found: {WEB_DB_PATH}")
    conn = sqlite3.connect(str(WEB_DB_PATH), timeout=2)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/", response_class=HTMLResponse)
def index(_user: str = Depends(_auth)):
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


@app.get("/api/v1/info")
def info(_user: str = Depends(_auth)):
    return {"service": "ig-tracker-web", "web_enabled": WEB_ENABLED, "tz_used": WEB_TZ}


@app.exception_handler(HTTPException)
def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
