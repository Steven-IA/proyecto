# asset-inventory Specification

## Purpose

Maintains a persistent, queryable inventory of discovered technology assets for the organization.

## Requirements

### Requirement: Persistent inventory
Discovered devices SHALL be persisted in SQLite and remain available after backend restart.

#### Scenario: Persist after restart
- **WHEN** the backend restarts
- **THEN** previously discovered devices remain available

### Requirement: Inventory querying
The inventory SHALL support filtering, search, sorting, and pagination by IP, MAC, name, vendor, type, status, and risk.

#### Scenario: Filter by status
- **WHEN** filtering by inactive
- **THEN** only inactive devices are returned

### Requirement: Device detail
The system SHALL provide a detail view with attributes, status history, assessments, vulnerabilities, and AI results.

#### Scenario: View device detail
- **WHEN** a device is selected
- **THEN** its full detail is displayed
