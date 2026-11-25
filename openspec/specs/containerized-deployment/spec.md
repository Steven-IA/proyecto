# containerized-deployment Specification

## Purpose

Deploys the platform with Docker Compose, persistence, healthchecks, and portability.

## Requirements

### Requirement: Dockerfiles
Independent Dockerfiles SHALL exist for frontend and backend.

#### Scenario: Build images
- **WHEN** docker compose build runs
- **THEN** both images build successfully

### Requirement: Compose orchestration
A docker-compose.yml SHALL orchestrate frontend and backend with internal networking.

#### Scenario: Start services
- **WHEN** docker compose up -d runs
- **THEN** both services start and communicate

### Requirement: Persistent volumes
Volumes SHALL persist SQLite, models, datasets, and reports.

#### Scenario: Persist after restart
- **WHEN** containers restart
- **THEN** data and weights remain

### Requirement: Healthchecks
Both services SHALL have healthchecks and controlled restart.

#### Scenario: Health status
- **WHEN** services are running
- **THEN** healthchecks report healthy

### Requirement: No auto-retrain
Models SHALL NOT retrain automatically on startup if valid weights exist.

#### Scenario: Startup with weights
- **WHEN** backend starts with valid weights
- **THEN** models load without training

### Requirement: Portability tests
The deployment SHALL be tested for build, startup, access, communication, persistence, model loading, inference, and restart.

#### Scenario: Rebuild from scratch
- **WHEN** containers are rebuilt
- **THEN** the system initializes and loads existing models
