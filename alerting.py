import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib import request


_last_sent = {}
_state_file = Path(os.getenv("ALERT_STATE_FILE", "alerts_state.json"))


def _channels():
    raw = os.getenv("ALERT_CHANNELS", "webhook,desktop")
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _enabled():
    return os.getenv("ALERTS_ENABLED", "false").lower() == "true"


def _cooldown_seconds():
    try:
        return int(os.getenv("ALERT_COOLDOWN_SECONDS", "1800"))
    except ValueError:
        return 1800


def _load_state():
    if _last_sent:
        return
    if not _state_file.exists():
        return
    try:
        _last_sent.update(json.loads(_state_file.read_text(encoding="utf-8")))
    except Exception:
        logging.exception("Failed to read alert state file")


def _save_state():
    try:
        _state_file.write_text(json.dumps(_last_sent), encoding="utf-8")
    except Exception:
        logging.exception("Failed to write alert state file")


def _should_send(event_key):
    _load_state()
    now = int(time.time())
    last = int(_last_sent.get(event_key, 0))
    if now - last < _cooldown_seconds():
        return False
    _last_sent[event_key] = now
    _save_state()
    return True


def _send_webhook(title, message, level):
    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return
    payload = json.dumps(
        {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": int(time.time()),
        }
    ).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as resp:
        resp.read()


def _send_desktop(title, message):
    try:
        if sys.platform.startswith("win"):
            # Best effort, works in interactive user sessions.
            safe_title = title.replace("'", "''")
            safe_message = message.replace("'", "''")
            script = (
                "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
                f"[System.Windows.Forms.MessageBox]::Show('{safe_message}','{safe_title}')"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        elif sys.platform == "darwin":
            safe_title = title.replace('"', "'")
            safe_message = message.replace('"', "'")
            subprocess.run(
                ["osascript", "-e", f'display notification "{safe_message}" with title "{safe_title}"'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        else:
            subprocess.run(
                ["notify-send", title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
    except Exception:
        logging.exception("Desktop alert failed")


def send_alert(event_key, title, message, level="error"):
    if not _enabled():
        return
    if not _should_send(event_key):
        logging.info("Alert suppressed by cooldown for event: %s", event_key)
        return

    channels = _channels()
    if "webhook" in channels:
        try:
            _send_webhook(title, message, level)
        except Exception:
            logging.exception("Webhook alert failed")

    if "desktop" in channels:
        _send_desktop(title, message)
