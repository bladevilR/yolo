## ADDED Requirements

### Requirement: Supervision Dependency Is Pinned
The system SHALL declare `supervision` as a pinned bounded dependency for station PPE visual QA utilities.

#### Scenario: Dependency installed for QA tools
- **WHEN** the project dependencies are installed from `requirements.txt`
- **THEN** supervision-backed PPE QC commands can import `supervision` without changing CVAT or Ultralytics training commands

### Requirement: YOLO Labels Convert To Supervision Detections
The system SHALL convert station PPE YOLO label files into `supervision.Detections` with pixel-space bounding boxes, class IDs, and class names for `person`, `helmet`, and `vest`.

#### Scenario: Valid YOLO label conversion
- **WHEN** a PPE image and matching YOLO label file are provided
- **THEN** the converter returns detections whose boxes match the image dimensions and whose class IDs map to the configured class names

#### Scenario: Malformed YOLO rows are reported
- **WHEN** a label file contains malformed rows, invalid class IDs, or non-positive boxes
- **THEN** the converter reports those rows in the QC summary instead of silently treating them as valid detections

### Requirement: Supervision Backed Review Overlays
The system SHALL render station PPE overlays and contact sheets using supervision annotators while preserving label names and stable per-class colors.

#### Scenario: Overlay generation
- **WHEN** the QC CLI is run on an image directory and YOLO label directory
- **THEN** it writes annotated image overlays that show `person`, `helmet`, and `vest` boxes with readable labels

#### Scenario: Contact sheet generation
- **WHEN** the QC CLI is run with contact-sheet output enabled
- **THEN** it writes paginated contact sheets suitable for fast human spot checks

### Requirement: Dataset QC Summary
The system SHALL generate a machine-readable QC summary for a station PPE image/label directory.

#### Scenario: Class and issue counts
- **WHEN** the QC CLI processes a label directory
- **THEN** it writes summary counts for images, label files, instances per class, empty labels, malformed rows, invalid classes, duplicate boxes, and orphan PPE boxes

#### Scenario: Orphan PPE detection
- **WHEN** a `helmet` or `vest` box is not spatially associated with any `person` box in the same image
- **THEN** the QC summary flags that image and class as an orphan PPE issue without modifying the original label file

### Requirement: Non-Mutating QC Workflow
The system SHALL keep supervision-backed QC read-only with respect to reviewed labels unless a separate explicit mutation command is introduced.

#### Scenario: QC preserves source labels
- **WHEN** the QC CLI is run on CVAT-exported or local YOLO labels
- **THEN** the original label files remain unchanged and all outputs are written to a separate output directory
