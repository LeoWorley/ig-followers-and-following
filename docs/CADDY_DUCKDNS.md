# Caddy + DuckDNS Access

This setup exposes Jellyfin and the IG dashboard through Caddy HTTPS.

## Router

Forward only these ports to this PC:

- External TCP `443` -> this PC TCP `443`
- External TCP `80` -> this PC TCP `8080`

Do not forward the IG dashboard port `8088`. After Caddy works, avoid direct public forwarding of Jellyfin `8096` too.

## DuckDNS

Create or use two DuckDNS names pointing to your public IP:

- One for Jellyfin
- One for the IG dashboard

## Install Caddy Service

Run from an Administrator PowerShell at the repo root:

```powershell
.\setup_caddy.ps1 -JellyfinHost your-jellyfin-name -IgHost your-ig-name
```

The script accepts either short DuckDNS names or full hostnames. For example, both `myserver` and `myserver.duckdns.org` are valid.

The script installs Caddy as a Windows service through `nssm.exe`, because the Chocolatey Caddy binary used on this PC does not include Caddy's built-in `service` command.

## Web App

The dashboard is configured to listen on `127.0.0.1:8088`, so Caddy can reach it locally but it is not exposed directly on your LAN.

Start it with:

```powershell
.\start_web.ps1
```

If the dashboard is installed as the `IG Tracker Web` Windows service, update that service after changing the web config:

```powershell
.\update_web_service.ps1
```

Then open:

- `https://your-jellyfin-name.duckdns.org`
- `https://your-ig-name.duckdns.org`

To rotate the dashboard password hash and session secret:

```powershell
.\generate_web_auth.ps1 -Password "your-new-password"
```

Copy the two printed values into `.env`, replacing `WEB_AUTH_PASSWORD_HASH` and `WEB_SESSION_SECRET`.
