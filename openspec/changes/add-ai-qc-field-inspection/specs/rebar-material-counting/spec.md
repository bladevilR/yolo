## ADDED Requirements

### Requirement: Count endpoint-visible steel bars
The system SHALL count visible steel or rebar ends when the submitted media shows an endpoint face suitable for individual bar separation.

#### Scenario: Endpoint bundle count
- **WHEN** the media shows a clear endpoint face with individual bar ends visible
- **THEN** the system detects each visible bar end, returns a total count, and writes an annotated image showing counted instances

### Requirement: Confidence and review flags for counts
The system SHALL include confidence and review flags with every material count.

#### Scenario: Count contains low-confidence detections
- **WHEN** one or more detected bar ends are low confidence or visually ambiguous
- **THEN** the system includes those detections in the annotated evidence and marks the count as requiring human review

### Requirement: Occlusion-aware counting boundary
The system SHALL avoid presenting occluded or side-view material piles as exact counts.

#### Scenario: Side-view pile is submitted
- **WHEN** the media shows mostly side surfaces of stacked bars instead of visible endpoints
- **THEN** the system marks the result as estimate-only or unsuitable for exact count and requests endpoint recapture or manual review

#### Scenario: Bundle is partially cropped
- **WHEN** the endpoint bundle is cut off by the image boundary
- **THEN** the system flags the count as incomplete and SHALL NOT mark the result as final

### Requirement: Counting unit and batch context
The system SHALL record the counting unit and available batch context with every material-counting result.

#### Scenario: Material label is visible or provided
- **WHEN** the user provides or captures material label, specification, bundle, batch, or receipt information
- **THEN** the system associates that context with the count result

#### Scenario: Counting unit is missing
- **WHEN** the user does not specify whether the result is root/bar count, bundle count, batch count, or receipt-line quantity
- **THEN** the system marks the submission incomplete for inventory reconciliation

### Requirement: Count report output
The system SHALL produce report output suitable for manual inventory reconciliation.

#### Scenario: Count report is generated
- **WHEN** a material-counting item is analyzed
- **THEN** the system writes media ID, site metadata, material context, detected count, review flag, and annotated evidence path to the structured report
