# Quick Start (5 minutes)

## Windows

1) Setup:
```powershell
.\setup.ps1
```

2) Edit `.env`:
```env
IG_USERNAME=your_username
IG_PASSWORD=your_password
TARGET_ACCOUNT=account_to_track
```

3) First-time login/cookie capture:
```powershell
.\login_once.ps1
```

4) Return to normal mode in `.env`:
```env
LOGIN_ONLY_MODE=false
HEADLESS_MODE=true
```

5) Start GUI or tray:
```powershell
.\start_gui.ps1
.\start_tray.ps1
```

## macOS/Linux

1) Setup:
```bash
./setup.sh
```

2) Edit `.env` with your account and target.

3) First-time login:
```bash
./login_once.sh
```

4) Return to normal mode (`LOGIN_ONLY_MODE=false`, `HEADLESS_MODE=true`).

5) Start GUI or tray:
```bash
./start_gui.sh
./start_tray.sh
```

## Recommended background mode

- Windows: run `main.py` from Task Scheduler.
- Use GUI/tray in monitor-only mode when scheduler is managing the tracker.
