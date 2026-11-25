# data-persistence Specification

## Purpose

Persists all platform data in SQLite with reliable initialization and Docker volume support.

## Requirements

### Requirement: SQLite persistence
The system SHALL use SQLite via SQLAlchemy for persistence.

#### Scenario: Store device
- **WHEN** a device is discovered
- **THEN** it is stored in SQLite

### Requirement: Stored entities
The system SHALL persist devices, history, analyses, alerts, vulnerabilities, AI results, and training info.

#### Scenario: Persist AI results
- **WHEN** an inference is performed
- **THEN** the result is persisted

### Requirement: Database initialization
The system SHALL initialize the database on startup and create schema as needed.

#### Scenario: First startup
- **WHEN** the backend starts with an empty database
- **THEN** schema is created automatically

### Requirement: Docker persistence
SQLite data SHALL be stored in a persistent Docker volume.

#### Scenario: Restart persistence
- **WHEN** containers restart
- **THEN** all data remains available
