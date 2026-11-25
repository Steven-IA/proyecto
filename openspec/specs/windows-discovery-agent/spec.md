# windows-discovery-agent Specification

## Purpose

Provides a Windows host agent that discovers the LAN and uploads results to the Dockerized backend.

## Requirements

### Requirement: Lightweight agent
A lightweight Windows agent SHALL discover interfaces, authorized subnet, devices (IP and MAC), and availability.

#### Scenario: Discover devices
- **WHEN** the agent runs
- **THEN** authorized subnet devices are discovered

### Requirement: Authenticated upload
The agent SHALL send results to the backend via an authenticated API.

#### Scenario: Upload results
- **WHEN** discovery completes
- **THEN** results are uploaded and appear in the backend

### Requirement: Authorized scope
The agent SHALL NOT scan outside the authorized subnet.

#### Scenario: Reject out-of-scope
- **WHEN** an out-of-subnet target is configured
- **THEN** it is rejected

### Requirement: End-to-end test
A real end-to-end test SHALL verify Docker backend communication, discovery, and authenticated upload.

#### Scenario: E2E communication
- **WHEN** agent runs against Docker backend
- **THEN** results appear in the dashboard
