# sentinelAI

Local-first enterprise cybersecurity monitoring platform (FastAPI + React/Vite + PyTorch). Runs on Windows 11; Docker is mandatory for delivery. All user-facing UI, messages, alerts, forms, PDF reports, and docs are in Spanish; technical identifiers remain in English.

## Stack
- Frontend: React, TypeScript, Vite, Tailwind, Recharts, Lucide.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, SQLite, WebSockets.
- AI: PyTorch, NumPy, Pandas, scikit-learn. Two in-house models: Network Transformer (anomaly) and Security Classifier (risk). No pretrained/downloaded models.
- Network: Scapy, Nmap (optional), ARP, ICMP, OUI lookup.

## Key paths
- `backend/app/` — API, ORM, services, discovery, vuln, reports.
- `ai/` — model definitions, training, evaluation, datasets.
- `models/` — persisted `.pth` weights + training metrics (volume-mounted).
- `data/` — datasets + vulnerability cache.
- `frontend/src/` — dashboard modules (Spanish UI).
- `agent/` — Windows host discovery agent sending results to backend API.

## Commands
- Docker build: `docker compose build`
- Run: `docker compose up -d`
- Status/logs: `docker compose ps` / `docker compose logs -f`
- Stop: `docker compose down`
- Train models (explicit): `python scripts/train_models.py` (or via backend container)
- Backend dev: `uvicorn app.main:app --reload` (from `backend/`)
- Frontend dev: `npm run dev` (from `frontend/`)

## Rules (non-negotiable)
- No simulated data presented as real; demo mode must be labeled DEMO.
- No pretrained models as substitutes; both models train in-project and persist weights.
- Do not retrain models on startup if valid weights exist.
- Discovery only on authorized subnet; no exploitation.
- Work phase-by-phase; no empty endpoints or non-functional buttons.
- Spanish for all user-facing text and docs.
- Windows PowerShell-compatible commands; avoid absolute Windows paths in Docker.