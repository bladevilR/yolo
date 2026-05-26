## ADDED Requirements

### Requirement: Detect visible concrete surface anomalies
The system SHALL detect visible concrete surface anomalies from field photos and mark them as suspected issues for human review.

#### Scenario: Surface anomaly is visible
- **WHEN** a concrete surface photo contains a visible anomaly such as honeycombing, pitting, exposed aggregate or rebar, hole, crack, leakage mark, repair patch, color difference, formwork seam, or surface damage
- **THEN** the system marks the suspected region and writes annotated evidence with anomaly type and confidence

### Requirement: Defect taxonomy configuration
The system SHALL use a configurable concrete defect taxonomy for first-stage screening.

#### Scenario: Taxonomy includes selected defect classes
- **WHEN** the project config lists concrete defect classes for the pilot
- **THEN** the system restricts concrete surface outputs to those classes plus a generic needs-review surface-anomaly class

#### Scenario: Unknown anomaly is detected
- **WHEN** a visible anomaly does not match a configured defect class with sufficient confidence
- **THEN** the system marks it as surface-anomaly needs review instead of assigning a final defect class

### Requirement: Overview and close-up evidence support
The system SHALL support linking overview and close-up photos for concrete surface QC evidence.

#### Scenario: Overview and close-up are submitted together
- **WHEN** a user submits an overview image for location and a close-up image for defect detail
- **THEN** the system links both media items under the same inspection record and uses the close-up for defect analysis

### Requirement: Measurement limitations for concrete defects
The system SHALL avoid precise concrete defect size measurements unless scale information is available.

#### Scenario: Defect area requested without scale
- **WHEN** the user requests defect area, width, or length and the photo has no scale reference or calibration
- **THEN** the system outputs only a visual region and SHALL NOT output a final precise measurement

#### Scenario: Defect area requested with scale
- **WHEN** the photo includes a usable scale reference or calibrated camera setup
- **THEN** the system can output an estimated area, width, or length with a calibrated-measurement flag

### Requirement: Concrete QC report output
The system SHALL produce report output suitable for concrete surface quality review.

#### Scenario: Concrete QC report is generated
- **WHEN** a concrete surface item is analyzed
- **THEN** the system writes media ID, site metadata, anomaly class, confidence, review flag, calibrated-measurement status, and annotated evidence path to the structured report
