# Spec Delta

## Purpose

Classifies device security risk using an in-house PyTorch MLP trained within the project.

## ADDED Requirements

### Requirement: In-house MLP
The system SHALL implement a PyTorch MLP trained within the project without pretrained models.

#### Scenario: Train model
- **WHEN** training is executed
- **THEN** metrics and a confusion matrix are produced and weights are saved

### Requirement: Risk inputs
The model SHALL use firewall state, antivirus state, pending updates, OS age, outdated software, vulnerable app count, excessive permissions, unnecessary services, and unverified signatures.

#### Scenario: Classify device
- **WHEN** security features are submitted
- **THEN** a risk class and confidence are returned

### Requirement: Risk classes
Outputs SHALL be low, medium, or high risk.

#### Scenario: High risk
- **WHEN** multiple critical conditions are present
- **THEN** the device is classified as high risk

### Requirement: Model persistence
Weights SHALL be saved to models/security_classifier.pth and loaded by the backend.

#### Scenario: Load weights
- **WHEN** backend starts with valid weights
- **THEN** the model loads without retraining