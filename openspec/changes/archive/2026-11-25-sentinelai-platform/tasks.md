# Tasks

## Phase 1 — Architecture and structure

- [x] 1.1 Create directory tree (backend, frontend, ai, agent, scripts, models, data).
- [x] 1.2 Add `backend/requirements.txt`, `frontend/package.json`, Dockerfiles, `docker-compose.yml`, `.env.example`, `.dockerignore`.
- [x] 1.3 Configure Vite, Tailwind, TypeScript, FastAPI skeleton, SQLAlchemy models, DB init script.
- [x] 1.4 Write README in Spanish with install/run/portability instructions.
- Acceptance: project builds; `docker compose build` succeeds; DB initializes.

## Phase 2 — Backend

- [x] 2.1 Implement SQLAlchemy models and Pydantic schemas.
- [x] 2.2 Implement discovery engine (ARP/ICMP/OUI) with authorized subnet validation.
- [x] 2.3 Implement device CRUD, history, availability endpoints.
- [x] 2.4 Add automated tests for endpoints and discovery validation.
- Acceptance: endpoints documented and tested; devices persisted.

## Phase 3 — Frontend

- [x] 3.1 Scaffold Vite React TS with Tailwind.
- [x] 3.2 Implement layout, sidebar, and nine modules in Spanish.
- [x] 3.3 Implement API client and real data binding; loading/error/empty states.
- [x] 3.4 Add manual verification of navigation and data flow.
- Acceptance: dashboard runs and consumes real backend data.

## Phase 4 — AI models

- [x] 4.1 Build documented datasets (synthetic/lab labeled).
- [x] 4.2 Implement Network Transformer and training/evaluation script.
- [x] 4.3 Implement Security Classifier MLP and training/evaluation script.
- [x] 4.4 Save weights and metrics; document limitations.
- Acceptance: both models trained, metrics and confusion matrices available, weights load.

## Phase 5 — Integration

- [x] 5.1 Load models in backend; add inference endpoints.
- [x] 5.2 Connect dashboard AI module to inference endpoints.
- [x] 5.3 Add tests for inference and model loading.
- Acceptance: inference works end-to-end and is displayed.

## Phase 6 — Vulnerabilities and reports

- [x] 6.1 Implement NVD/OSV client with cache and offline tolerance.
- [x] 6.2 Implement CVE matching and verification levels.
- [x] 6.3 Implement alerts and PDF reports in Spanish.
- [x] 6.4 Add tests for vuln matching and report generation.
- Acceptance: vulns distinguished; reports generated.

## Phase 7 — Final tests

- [ ] 7.1 Docker build/up, persistence, model loading, inference tests.
- [x] 7.2 Windows agent build and end-to-end communication test.
- [x] 7.3 Portability documentation and manual verification.
- [x] 7.4 Fix all critical errors before completion.
- Acceptance: all acceptance criteria met; no critical errors.

## Phase 8 — MVP completion

- [x] 8.1 Implement real network topology view from discovered devices.
- [x] 8.2 Implement event history with filters and search.
- [x] 8.3 Implement functional settings screen with validation and persistence.
- [x] 8.4 Fix AI data leakage (scaler fit on train only) and document split.
- [x] 8.5 Add viable software inventory collection in Windows agent.
- [x] 8.6 Update vulnerability scan to use software inventory.
- [ ] 8.7 Docker build/up and persistence tests (pending: no Docker daemon).
- Acceptance: new modules consume real backend data and pass smoke tests.