# availability-monitoring Specification

## Purpose

Monitors device availability over time and records status transitions for operational awareness.

## Requirements

### Requirement: ICMP availability checks
The system SHALL check device availability via ICMP or permitted TCP fallback for authorized targets.

#### Scenario: Check availability
- **WHEN** an availability check runs
- **THEN** device status is updated to active or inactive

### Requirement: Status history
The system SHALL track active and inactive transitions with timestamps.

#### Scenario: Device goes offline
- **WHEN** a device stops responding
- **THEN** its status becomes inactive and an alert may be generated
