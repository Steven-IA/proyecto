# security-assessment Specification

## Purpose

Evaluates device security conditions to produce risk inputs for classification and recommendations.

## Requirements

### Requirement: Security condition inputs
The system SHALL collect and evaluate firewall state, antivirus state, pending updates, OS age, outdated software, vulnerable app count, excessive permissions, unnecessary services, and unverified signatures.

#### Scenario: Collect inputs
- **WHEN** a security assessment runs
- **THEN** all available security inputs are recorded

### Requirement: Unsigned software handling
Software without a verified signature SHALL be classified as requiring verification, not as malware.

#### Scenario: Unsigned software
- **WHEN** software has no verified signature
- **THEN** it is marked as requiring verification
