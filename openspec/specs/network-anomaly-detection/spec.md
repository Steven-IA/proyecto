# network-anomaly-detection Specification

## Purpose

Detects anomalous network behavior using an in-house Transformer model trained within the project.

## Requirements

### Requirement: In-house Transformer
The system SHALL implement a PyTorch Transformer Encoder trained within the project without pretrained or downloaded models.

#### Scenario: Train model
- **WHEN** training is executed
- **THEN** metrics and a confusion matrix are produced and weights are saved

### Requirement: Anomaly features
The model SHALL use connection count, frequency, ports used, bytes sent and received, duration, activity variance, and communication frequency.

#### Scenario: Feature input
- **WHEN** network features are submitted
- **THEN** they are validated and normalized before inference

### Requirement: Anomaly output
The model SHALL output normal or anomalous classification, an anomaly score, and contributing features.

#### Scenario: Inference
- **WHEN** network features are submitted
- **THEN** an anomaly score and contributing features are returned

### Requirement: Model persistence
Trained weights SHALL be saved to models/network_transformer.pth and loaded by the backend.

#### Scenario: Load weights
- **WHEN** backend starts with valid weights
- **THEN** the model loads without retraining
