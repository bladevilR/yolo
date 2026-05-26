## ADDED Requirements

### Requirement: CVAT Snapshot Is Preserved Before Dataset Promotion
The system SHALL create a timestamped backup of the current CVAT task annotations and a matching YOLO export before building any retraining dataset.

#### Scenario: Snapshot before promotion
- **WHEN** the dataset promotion workflow is started for the current station PPE task
- **THEN** it writes a task backup, YOLO labels, and a snapshot manifest to a new timestamped output directory without importing annotations back into CVAT

#### Scenario: Source labels are not mutated
- **WHEN** the promotion workflow reads CVAT-exported labels
- **THEN** the original CVAT task and source label directory remain unchanged

### Requirement: Review Manifest Records Human Status
The system SHALL maintain a review manifest for every candidate image with frame name, source snapshot, manual status, reviewer, review date, QC flags, sample profile, and notes.

#### Scenario: Manifest seeded from snapshot
- **WHEN** a CVAT snapshot is exported
- **THEN** the system creates or updates a manifest row for every image in the snapshot

#### Scenario: Only explicit review status is trusted
- **WHEN** an image lacks `manual_status=done`
- **THEN** the image is excluded from acceptance-candidate training splits unless it is explicitly marked as `skip` or stress-only

### Requirement: Supervision QC Drives Review Queue
The system SHALL use supervision QC summary and issue CSV outputs to prioritize duplicate boxes, orphan PPE boxes, empty labels, malformed rows, invalid classes, non-positive boxes, and missing labels for human review.

#### Scenario: QC issue queue is generated
- **WHEN** supervision QC finds duplicate boxes or orphan PPE boxes
- **THEN** the system records those images and issue types in a review queue with links to overlay and contact-sheet artifacts

#### Scenario: Critical QC issues block promotion
- **WHEN** a reviewed training candidate still has unresolved malformed rows, invalid classes, non-positive boxes, missing labels, or unreviewed duplicate-box issues
- **THEN** the candidate is blocked from normal train, validation, and test splits

### Requirement: Class Map Remains Stable
The promoted dataset SHALL use exactly three detector classes: `person`, `helmet`, and visible `vest`, with class IDs `0`, `1`, and `2`.

#### Scenario: Stable class map validation
- **WHEN** the promotion workflow validates YOLO labels
- **THEN** any class ID outside `0`, `1`, or `2` is reported as a blocking error

#### Scenario: Violation states are excluded from labels
- **WHEN** the dataset contains PPE violation examples
- **THEN** `no_helmet` and `no_vest` remain event-layer states and are not written as YOLO training classes

### Requirement: Dataset Splits Are Frozen And Documented
The system SHALL generate frozen train, validation, test, stress, and demo/evaluation manifests from reviewed samples.

#### Scenario: Split manifests generated
- **WHEN** reviewed samples are promoted
- **THEN** the system writes split manifests that list image path, label path, source video or frame identity, review status, sample profile, and split name

#### Scenario: Stress samples remain separately reportable
- **WHEN** samples are tagged as hard negative, many-box, empty detection, tiny worker, edge worker, occluded worker, or clutter
- **THEN** they are either placed in the stress split or tagged so stress metrics can be reported separately from normal validation and test metrics

### Requirement: Dataset Report Is Generated
The system SHALL generate a machine-readable and human-readable dataset report before training.

#### Scenario: Dataset report contains counts
- **WHEN** a dataset is promoted
- **THEN** the report includes image counts, empty-label counts, hard-negative counts, per-class instance counts, QC issue counts, and split composition

#### Scenario: Provenance warnings are visible
- **WHEN** any promoted sample has missing reviewer metadata, draft-label provenance, unresolved QC flags, or inconsistent split metadata
- **THEN** the report lists a provenance warning and marks whether it blocks training
