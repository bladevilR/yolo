## ADDED Requirements

### Requirement: Human-reviewed labels gate
The system SHALL only promote PPE training samples into an acceptance-oriented retraining dataset when their labels have been reviewed by a human and marked as complete.

#### Scenario: Promote confirmed reviewed sample
- **WHEN** a sample has corrected `person`, `helmet`, and visible `vest` labels and its review status is `done`
- **THEN** the sample is eligible for the acceptance-oriented retraining dataset

#### Scenario: Reject draft-only sample
- **WHEN** a sample only has pseudo labels, Codex draft labels, or Codex visual triage without human completion
- **THEN** the sample MUST NOT be promoted as human-reviewed training data

### Requirement: Visible-object class scope
The retraining dataset SHALL contain detection labels only for visible `person`, `helmet`, and `vest` classes.

#### Scenario: Convert reviewed labels
- **WHEN** reviewed source labels contain `person`, `helmet`, and visible `vest`
- **THEN** the promoted YOLO dataset SHALL map them to the three detector classes

#### Scenario: Exclude absence classes
- **WHEN** labels or review notes mention `no_helmet`, `no_vest`, or uncertain PPE state
- **THEN** the promoted detector labels MUST NOT create `no_helmet` or `no_vest` object classes

### Requirement: Hard-negative coverage
The retraining dataset SHALL include reviewed hard-negative samples for known false-person sources.

#### Scenario: Include hard-negative image
- **WHEN** a reviewed sample contains bags, covers, pipes, extinguishers, materials, or clutter previously detected as a person
- **THEN** the sample SHALL be included as a hard negative with no false `person` box

#### Scenario: Bound hard-negative ratio
- **WHEN** a retraining split is generated
- **THEN** hard negatives SHALL be counted separately so they can be bounded and reported instead of silently dominating normal validation metrics

### Requirement: Stratified split policy
The retraining dataset SHALL separate normal train/validation/test splits from hard-negative stress-test samples.

#### Scenario: Generate normal splits
- **WHEN** a human-reviewed dataset is promoted
- **THEN** train, validation, and test splits SHALL be stratified by source video, scene profile, camera view, and sample type where possible

#### Scenario: Generate stress split
- **WHEN** samples are tagged as `many_boxes`, `empty_detection`, edge, tiny, occluded, or hard-negative cases
- **THEN** they SHALL be available for stress evaluation and SHALL NOT be mixed into normal metrics without explicit reporting

### Requirement: Dataset provenance manifest
Every promoted retraining dataset SHALL include a manifest with sample provenance, review status, class counts, split, and label source.

#### Scenario: Write promotion manifest
- **WHEN** a retraining dataset is created
- **THEN** the manifest SHALL record source image path, source label path, reviewed label path, split, profile, review status, label source, and reviewer/date fields when available

#### Scenario: Report class counts
- **WHEN** a retraining dataset is created
- **THEN** the dataset report SHALL include image counts, empty-label counts, hard-negative counts, and per-class label counts by split
