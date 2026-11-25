# Design

## Architecture

SentinelAI is a local-first platform with three runtime parts:

1. **Frontend** (React + Vite + Tailwind + Recharts + Lucide) served as static assets.
2. **Backend** (FastAPI + SQLAlchemy + SQLite) exposing REST and WebSockets.
3. **AI runtime** (PyTorch models loaded from persisted weights) invoked by backend endpoints.

On Windows with Docker Desktop, the backend container cannot directly access the physical LAN. A **Windows discovery agent** runs on the host and pushes results to the backend via an authenticated API.

## Module boundaries

- `backend/app/routers/*`: thin HTTP/WebSocket handlers.
- `backend/app/services/*`: orchestration (discovery, assessment, inference, reports).
- `backend/app/discovery/*`: ARP/ICMP/OUI/port scanning logic.
- `backend/app/vuln/*`: CVE matching and NVD/OSV clients with cache.
- `backend/app/reports/*`: PDF generation.
- `ai/*`: model definitions, datasets, training, evaluation.
- `models/*`: persisted weights and metrics (Docker volume).
- `frontend/src/*`: pages, components, hooks, API client.

## Data flow

1. Discovery (backend or agent) → persist devices.
2. Availability checks → update status + history.
3. Security assessment → risk inputs.
4. Model inference → anomaly + risk scores.
5. Vulnerability scan → CVEs + verification level.
6. Alerts generated from conditions.
7. Reports aggregate all data.

## Spanish-first UX

All user-facing text (UI, messages, alerts, forms, PDF, README) is in Spanish. Technical identifiers remain in English.

## Real data policy

- Frontend consumes only real backend endpoints.
- No mock data to simulate completed features.
- Demo mode, if any, must be explicitly labeled "DEMO" and separated from real discovery.

## AI training policy

- Both models trained in-project via reproducible scripts.
- Datasets documented (origin, license, synthetic/lab labeling).
- Train/val/test split, metrics, confusion matrices stored.
- Limitations documented; no real threat-detection claims from synthetic data.

## Docker deployment

- Services: `frontend`, `backend`.
- Volumes: `sqlite_data`, `models`, `datasets`, `reports`, `vuln_cache`.
- Healthchecks on both; restart policy `unless-stopped`.
- No auto-retrain on startup if valid weights exist.

## Windows agent

- Python script packageable with PyInstaller.
- Detects interfaces, authorized subnet, performs controlled discovery.
- Sends results via authenticated API (API key or JWT).
- Tested end-to-end against Docker backend.

## Acceptance and testing

Each phase has verifiable acceptance criteria, automated tests, and manual checks where needed. No task marked complete without execution and verification.