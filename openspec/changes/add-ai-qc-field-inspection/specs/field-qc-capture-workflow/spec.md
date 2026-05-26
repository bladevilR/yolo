## ADDED Requirements

### Requirement: Media intake with traceable metadata
The system SHALL accept field photos or short videos only with scenario selection and traceable site metadata sufficient for quality review.

#### Scenario: Intake accepts complete field metadata
- **WHEN** a user submits media with scenario, project, inspection area, floor or zone, component or material identifier, photographer, and timestamp
- **THEN** the system stores the media and metadata together and marks the item ready for scenario analysis

#### Scenario: Intake flags missing traceability
- **WHEN** submitted media lacks required scenario or site metadata
- **THEN** the system records the item as incomplete and reports the missing fields before analysis is treated as reviewable evidence

### Requirement: Capture guidance for scenario-specific media
The system SHALL provide capture guidance that matches the selected AI QC scenario before or during submission.

#### Scenario: Steel counting capture guidance
- **WHEN** the selected scenario is steel or rebar material counting
- **THEN** the system instructs the user to capture the full endpoint face of the bundle, avoid edge cropping, reduce occlusion, and include material label or batch context when available

#### Scenario: Coupler QC capture guidance
- **WHEN** the selected scenario is rebar coupler exposed-thread QC
- **THEN** the system instructs the user to capture the whole coupler and both adjacent steel ends from a side-on angle with minimal blur and glare

#### Scenario: Concrete surface capture guidance
- **WHEN** the selected scenario is concrete surface QC
- **THEN** the system instructs the user to capture one overview image for location and one near image for defects, with a scale reference when measuring width or area is required

### Requirement: Capture-quality screening
The system SHALL screen submitted media for basic quality before producing final scenario output.

#### Scenario: Low quality media requires recapture or review
- **WHEN** submitted media is severely blurred, too dark, overexposed, cropped, or missing the target object
- **THEN** the system flags the item as low quality and returns a recapture or manual-review reason

### Requirement: Annotated evidence output
The system SHALL output annotated evidence and structured result data for every analyzed item.

#### Scenario: Analysis produces reviewable evidence
- **WHEN** a scenario analyzer completes successfully
- **THEN** the system writes an annotated image or frame, a structured JSON result, and a human-readable CSV or summary row containing scenario, metadata, detections, confidence, and review status

### Requirement: Human review state
The system SHALL preserve a human review state for every AI result.

#### Scenario: AI result awaits quality reviewer decision
- **WHEN** the system produces counts, suspected defects, or suspicious compliance flags
- **THEN** the result is marked as awaiting review until a human reviewer accepts, rejects, or corrects it

### Requirement: Measurement calibration handling
The system SHALL distinguish calibrated measurements from uncalibrated visual screening.

#### Scenario: Measurement requested without calibration
- **WHEN** a scenario asks for exposed length, spacing, width, or area and no scale reference or camera calibration is available
- **THEN** the system reports the finding as visual screening only and SHALL NOT output a final precise measurement
