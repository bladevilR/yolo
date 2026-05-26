## ADDED Requirements

### Requirement: Existing Upload Control Integration
The OCR feature SHALL integrate with configured existing XCreator photo or attachment upload controls while preserving the original upload behavior.

#### Scenario: Upload control is OCR-enabled
- **WHEN** a user views a configured photo or attachment upload control
- **THEN** the page displays an OCR affordance near that control without preventing the normal upload action

#### Scenario: Upload control is not OCR-enabled
- **WHEN** a user views an upload control without OCR configuration
- **THEN** the upload control behaves exactly as it did before the OCR feature

#### Scenario: User uploads a photo normally
- **WHEN** a user uploads a file through an OCR-enabled upload control but does not start OCR
- **THEN** the original upload flow completes without OCR side effects

### Requirement: OCR Upload And Recognition
The system SHALL allow users to recognize supported certificate/document images or PDFs from an OCR-enabled existing upload control.

#### Scenario: Supported document uploaded
- **WHEN** a user selects or uploads a supported document type from an OCR-enabled upload control
- **THEN** the system creates an OCR job and returns extracted structured fields with confidence metadata

#### Scenario: Unsupported document uploaded
- **WHEN** a user selects or uploads an unsupported file type, document type, or oversized file
- **THEN** the system rejects the upload with a clear error and does not attempt to fill the page

### Requirement: Document Type And Field Extraction
The OCR service SHALL identify the configured document type and extract only fields defined for that type.

#### Scenario: Document type recognized
- **WHEN** the OCR provider recognizes a configured document type
- **THEN** the result includes the document type, extracted field keys, raw field values, normalized field values, and per-field confidence

#### Scenario: Document type uncertain
- **WHEN** the OCR provider cannot confidently identify the document type
- **THEN** the system requires the user to select or confirm the document type before any field mapping is offered

### Requirement: Review Before Fill
The system SHALL present OCR results as a user-reviewable draft before writing values into any XCreator form fields.

#### Scenario: User reviews OCR results
- **WHEN** OCR extraction completes
- **THEN** the user sees the related upload slot, extracted values, confidence indicators, unresolved fields, and target field mappings before applying values

#### Scenario: User cancels OCR draft
- **WHEN** the user cancels the OCR draft
- **THEN** the system closes or clears the draft without changing any XCreator form fields

### Requirement: Confirmed Form Fill Bridge
The system SHALL fill XCreator form controls only after explicit user confirmation and SHALL NOT submit or save the form.

#### Scenario: User confirms mapped fields
- **WHEN** the user confirms selected OCR fields for fill
- **THEN** the bridge writes those values to XCreator fields configured for the current upload slot and triggers normal change events for those controls

#### Scenario: Save is not triggered
- **WHEN** OCR values are applied to a form
- **THEN** the system does not click save, submit, delete, archive, download, approve, or any other business action button

### Requirement: Field Mapping Configuration
The system SHALL support page-level and upload-slot-level mapping from OCR field keys to XCreator field selectors, widget IDs, or stable field names.

#### Scenario: Mapping exists
- **WHEN** an extracted OCR field has a configured mapping for the current tenant, app, page, upload slot, and document type
- **THEN** the review panel shows the target XCreator field and allows the user to apply the value

#### Scenario: Mapping missing
- **WHEN** an extracted OCR field has no configured target field
- **THEN** the review panel marks the field as unmapped and does not apply it automatically

#### Scenario: Mapping dry-run requested
- **WHEN** an administrator or tester runs mapping validation on a page
- **THEN** the system reports resolvable fields, missing fields, duplicate targets, and unsupported widgets without filling values

### Requirement: Privacy And Audit
The OCR feature SHALL protect certificate/document data and record an audit trail without leaking authentication tokens.

#### Scenario: OCR job completed
- **WHEN** an OCR job completes
- **THEN** the system records user/page identifiers, document type, applied field keys, confidence summary, and outcome status without storing raw tokens

#### Scenario: Uploaded file retention expires
- **WHEN** the configured retention period for OCR processing artifacts is reached
- **THEN** the system deletes or anonymizes OCR copies and intermediate artifacts according to retention policy without deleting the original business attachment unless explicitly configured

### Requirement: OCR Error Handling
The OCR feature SHALL degrade safely when recognition, mapping, or provider calls fail.

#### Scenario: OCR provider fails
- **WHEN** the OCR provider returns an error or times out
- **THEN** the system shows a recoverable error and does not change any XCreator form fields

#### Scenario: Low confidence field detected
- **WHEN** an extracted field falls below the configured confidence threshold
- **THEN** the system marks it for manual review and does not preselect it for filling
