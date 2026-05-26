## ADDED Requirements

### Requirement: Detect couplers and adjacent exposed-thread regions
The system SHALL detect rebar mechanical couplers and the visible thread regions on both adjacent steel ends when they are visible in the submitted media.

#### Scenario: Coupler and both sides are visible
- **WHEN** the media clearly shows a coupler and the adjacent steel on both sides
- **THEN** the system identifies the coupler, left-side exposed-thread region, right-side exposed-thread region, and writes annotated evidence

#### Scenario: Coupler is partially visible
- **WHEN** the media crops off one side of the coupler or adjacent steel
- **THEN** the system flags the item as incomplete and requests recapture or manual review

### Requirement: Threshold-driven compliance screening
The system SHALL apply project-supplied exposed-thread thresholds before producing suspected compliance results.

#### Scenario: Exposed-thread threshold exists
- **WHEN** the project configuration defines allowed visible thread count or exposed length for the coupler condition
- **THEN** the system compares detected exposed-thread evidence with the configured threshold and returns pass, suspected non-compliant, or needs review

#### Scenario: Exposed-thread threshold is missing
- **WHEN** no applicable threshold is configured
- **THEN** the system SHALL NOT output pass/fail and SHALL mark the item as needs standard confirmation

### Requirement: Thread count or length evidence
The system SHALL provide the evidence used for each exposed-thread screening decision.

#### Scenario: Visible thread count is used
- **WHEN** the system can distinguish visible thread ridges with sufficient confidence
- **THEN** the system reports the visible thread-count estimate per side and marks uncertain ridges for review

#### Scenario: Exposed length is requested
- **WHEN** the rule requires exposed length measurement
- **THEN** the system outputs length only when scale reference, known steel/coupler dimensions, or camera calibration is available

### Requirement: Ambiguity handling
The system SHALL flag image conditions that make coupler exposed-thread screening unreliable.

#### Scenario: Glare blur or occlusion affects thread visibility
- **WHEN** glare, motion blur, rust, straps, overlapping bars, or shallow depth of field prevents reliable thread detection
- **THEN** the system marks the result as needs review and includes the reason code

### Requirement: Coupler QC report output
The system SHALL produce report output suitable for a quality engineer to review suspected coupler issues.

#### Scenario: Coupler QC report is generated
- **WHEN** a coupler item is analyzed
- **THEN** the system writes media ID, site metadata, coupler detections, side-specific exposed-thread evidence, configured threshold, decision, review flag, and annotated evidence path to the structured report
