# Cloud Migration Path

This document defines a staged migration from local host runtime to cloud while preserving current behavior.

## Current Baseline (Local)

1. Tracker + web app run on same machine.
2. SQLite file in project root.
3. Access through Tailscale.

## Target State (Cloud-Ready)

1. Containerized tracker and API.
2. Managed relational database (PostgreSQL preferred).
3. Reverse proxy with TLS and identity-aware access.
4. Separate environments: dev/staging/prod.

## Migration Stages

### Stage 1: Local hardening (now)

1. Keep read-only web API contract stable.
2. Keep env-driven configuration.
3. Document operations and incident procedures.

### Stage 2: Packaging

1. Add Dockerfile for web API.
2. Add optional Docker Compose for local parity.
3. Externalize DB path and credentials by environment.

### Stage 3: Database transition

1. Introduce SQLAlchemy-backed repository layer for web API.
2. Maintain compatibility adapters:
   - SQLite local adapter
   - PostgreSQL cloud adapter
3. Run dual-read tests to verify parity.

### Stage 4: Cloud deployment

1. Deploy API behind managed ingress (`HTTPS` only).
2. Enforce identity provider access (OIDC/SAML) instead of Basic Auth.
3. Move scheduled tracker runtime to:
   - VM cron/systemd
   - or container scheduler (ECS/Fly/Render/Kubernetes)

### Stage 5: Observability and SLOs

1. Central logs for tracker and API.
2. Health checks and uptime alerting.
3. Backup and restore drills with RPO/RTO targets.

## Compatibility Constraints

1. Keep API response shape stable during migration.
2. Preserve timezone behavior (`tz` query + `tz_used`).
3. Keep read-only public contract for dashboard endpoints.

## Risks and Mitigations

1. Data consistency during DB migration
   - use controlled cutover and validation scripts.
2. Auth regressions
   - keep Tailscale/private ingress during transition.
3. Cost drift
   - start with smallest VM/service tier and profile usage before scaling.
