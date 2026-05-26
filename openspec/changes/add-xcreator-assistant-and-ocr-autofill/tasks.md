## 1. Safety And Integration Baseline

- [x] 1.1 Create or identify a non-production XCreator page/app clone for assistant and OCR integration testing.
- [x] 1.2 Capture a read-only baseline of the target page config, runtime `_demoGrid_config`, visible controls, existing upload/photo controls, and business action buttons before any integration.
- [x] 1.3 Define environment-specific endpoint configuration for assistant/OCR services with no hardcoded localhost production URLs.
- [x] 1.4 Implement a feature-flag/config model keyed by tenant, appCode, pageCode/pageId, environment, and role.
- [x] 1.5 Add redaction utilities that remove `cwUserToken`, `cwAppToken`, session tokens, and raw auth parameters from logs and diagnostics.

## 2. XCreator Widget Loader And Page Bridge

- [x] 2.1 Build a small loader script that can render a floating assistant entry without changing grid/list behavior.
- [x] 2.2 Add a fallback entry mode that opens the assistant through menu, iframe, or openWindow when floating injection is disabled.
- [x] 2.3 Implement safe page-context collection for tenant, appCode, pageCode, pageId, title, and enabled feature config.
- [x] 2.4 Implement a bridge API for dry-run upload-control discovery, form field discovery, and confirmed field filling.
- [ ] 2.5 Validate the loader on the cloned page for layout, pagination, search, and operation-button regressions.

## 3. Knowledge Assistant Service

- [x] 3.1 Define the reserved knowledge-system adapter contract for ask, search, source lookup, health check, authentication, errors, and citations.
- [ ] 3.2 Confirm or revise `knowledge-adapter-contract.md` with the owner of the existing knowledge-base system.
- [x] 3.3 Implement disabled, stub, and test-endpoint modes for pages where the existing knowledge system is not yet connected.
- [x] 3.4 Implement adapter configuration keyed by tenant, app, page, role, endpoint alias, and source-scope hints.
- [x] 3.5 Implement adapter-grounded answer handling with citations and refusal behavior when the adapter returns no supporting source.
- [x] 3.6 Implement conversation audit logging and user feedback capture without storing sensitive tokens.
- [x] 3.7 Add assistant UI states for disabled placeholder, loading, cited answer, unsupported question, adapter error, source preview, and feedback.

## 4. OCR Recognition Service

- [x] 4.1 Inventory the first target pages' existing photo/attachment upload controls and identify the upload widget patterns to support.
- [x] 4.2 Confirm or revise `ocr-upload-integration-notes.md` against the first target upload widget pattern.
- [x] 4.3 Define the initial supported certificate/document types and their normalized field schema.
- [x] 4.4 Implement the OCR provider interface and configure the first trusted/on-prem-capable provider.
- [x] 4.5 Implement validation for file type, size, page count, existing attachment reference, and configured document type.
- [x] 4.6 Implement OCR job creation, status tracking, extraction output, normalized values, and per-field confidence.
- [x] 4.7 Implement low-confidence and uncertain-document-type handling that requires manual review before mapping.
- [x] 4.8 Implement OCR artifact retention and cleanup according to configured policy without deleting original business attachments by default.

## 5. OCR Review And Auto-Fill

- [x] 5.1 Implement upload-slot-level field mapping from OCR field keys to XCreator selectors, widget IDs, or stable field names.
- [x] 5.2 Build the OCR review panel next to or launched from the upload control, showing extracted values, confidence, target fields, unmapped fields, and user-selectable apply choices.
- [x] 5.3 Implement confirmed fill so selected fields are written to XCreator controls associated with the upload slot and normal change events are triggered.
- [x] 5.4 Enforce that OCR fill never triggers save, submit, delete, archive, download, approve, or other business action buttons.
- [x] 5.5 Add mapping dry-run diagnostics for missing fields, duplicate targets, unsupported widgets, and unresolved selectors.
- [x] 5.6 Add audit logging for OCR job outcome, applied field keys, confidence summary, and user/page identifiers.

## 6. Verification And Rollout Gates

- [x] 6.1 Add unit tests for config resolution, token redaction, knowledge adapter modes, OCR field normalization, upload-slot detection, and mapping validation.
- [ ] 6.2 Add integration tests or scripted browser checks for widget load, assistant disabled/stub/Q&A states, upload-control OCR launch, OCR draft review, confirmed fill, and cancel behavior on the cloned page.
- [x] 6.3 Run production-safety checks verifying no save/submit/delete/归档/download action is invoked by assistant or OCR flows.
- [x] 6.4 Document deployment, rollback, feature-flag disablement, and first-page onboarding steps.
- [x] 6.5 Run `openspec validate add-xcreator-assistant-and-ocr-autofill --strict` and record any follow-up fixes.
- [ ] 6.6 Obtain business/security approval for the knowledge-system adapter endpoint, OCR document types, data retention policy, target upload controls, and production pilot page before production enablement.
