# Spec Delta

## Purpose

Discovers devices within an explicitly authorized local subnet and records their technical attributes for inventory and security assessment.

## ADDED Requirements

### Requirement: Authorized subnet discovery
The system SHALL discover devices only within an explicitly authorized subnet and SHALL reject any request to scan outside it.

#### Scenario: Discover in authorized subnet
- **WHEN** an authorized discovery is started
- **THEN** devices in the authorized subnet are discovered and persisted

#### Scenario: Reject out-of-subnet scan
- **WHEN** a scan target outside the authorized subnet is requested
- **THEN** the request is rejected with an error

### Requirement: Device attribute collection
The system SHALL collect IP, MAC, vendor, hostname, estimated type, state, first seen, and last seen when technically possible, using "No disponible" or "Desconocido" for missing data.

#### Scenario: Missing attribute
- **WHEN** a device does not expose its hostname
- **THEN** the UI shows "No disponible" instead of an invented value

### Requirement: Device categorization
The system SHALL classify discovered devices into computers, servers, phones, tablets, printers, smart TVs, IoT, or unknown.

#### Scenario: Classify printer
- **WHEN** a printer is discovered
- **THEN** it is categorized as a printer

### Requirement: Information provenance
The system SHALL distinguish discovered, responding, unresponsive, agent-provided, and inferred information.

#### Scenario: Agent-provided data
- **WHEN** data arrives from the Windows agent
- **THEN** it is marked as agent-provided

### Requirement: Discovery controls
The system SHALL provide explicit actions to start discovery and refresh results, and optional authorized port scanning only when enabled.

#### Scenario: Refresh results
- **WHEN** refresh is requested
- **THEN** latest results replace stale ones without duplicating records