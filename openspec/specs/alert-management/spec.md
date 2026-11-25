# alert-management Specification

## Purpose

Manages security alerts generated from anomalies, risks, and vulnerabilities.

## Requirements

### Requirement: Alert ordering
Alerts SHALL be ordered by date, severity, and device.

#### Scenario: List alerts
- **WHEN** alerts are retrieved
- **THEN** they are sorted by date, severity, and device

### Requirement: Alert persistence
Alerts SHALL be persisted and retrievable after restart.

#### Scenario: Persist alerts
- **WHEN** an alert is created
- **THEN** it remains available after restart

### Requirement: Alert resolution
The system SHALL allow marking alerts as resolved or acknowledged.

#### Scenario: Resolve alert
- **WHEN** an alert is marked resolved
- **THEN** its status updates accordingly
