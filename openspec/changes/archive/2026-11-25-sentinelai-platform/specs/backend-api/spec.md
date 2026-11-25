# Spec Delta

## Purpose

Exposes a documented FastAPI interface for all platform capabilities.

## ADDED Requirements

### Requirement: REST endpoints
FastAPI SHALL expose documented endpoints for system status, discovery, devices, details, history, security analysis, model inference, vulnerabilities, alerts, training metrics, and reports.

#### Scenario: Call endpoint
- **WHEN** a valid request is made
- **THEN** a documented response is returned

### Requirement: WebSockets
WebSockets SHALL be used where real-time updates are needed.

#### Scenario: Real-time update
- **WHEN** a discovery completes
- **THEN** connected clients receive an update

### Requirement: Input validation
All inputs SHALL be validated via Pydantic and errors handled gracefully.

#### Scenario: Invalid input
- **WHEN** invalid parameters are submitted
- **THEN** a validation error in Spanish is returned