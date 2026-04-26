# Quick Start for Windows

Use the installer path if you do not want to install Python or use PowerShell.

## 1. Install

1. Download `ig-tracker-setup-vX.Y.Z.exe` from Releases.
2. Run the installer.
3. Leave `Offer background tracking setup after first login` selected.
4. Keep `Run tray monitor at Windows startup` optional.
5. Let the installer launch `IG Tracker GUI`.

## 2. Configure

In the GUI `Overview` tab:

1. Enter your Instagram username.
2. Enter your Instagram password.
3. Enter the account you want to track.
4. Click `Save account settings`.

The GUI writes the config for you. You do not need to edit `.env`.

## 3. Login Once

1. Click `Run login-only now`.
2. Complete Instagram login and any 2FA challenge in the browser.
3. Wait for the login window to finish and save cookies.
4. Click `Run setup checks`.

If the cookie check warns or fails, run login-only again.

## 4. Enable Background Tracking

After required checks pass, click `Enable background tracking`.

The GUI creates a Windows Task Scheduler entry named `IG Tracker` for your user account. It runs after Windows login and uses the app lock file so duplicate tracker runs are avoided. The GUI and tray switch to monitor-only mode after this is enabled.

## Daily Use

- Open `IG Tracker GUI` from the Start Menu to see status and reports.
- Use `Run login-only now` again if Instagram asks you to log in later.
- Use `Open log` if a setup check reports an error.

## Optional Web Dashboard

The web dashboard is not enabled during basic setup.

To prepare local web dashboard credentials, use `Web dashboard auth (optional)` in the GUI. Keep web access local unless you intentionally configure secure remote access from the advanced docs.

## Source Setup

Developer/source setup is documented in `docs/ADVANCED.md`.
