## Context

The XCreator platform renders production pages from stored JSON configuration into WUI/jQuery/jqGrid runtime pages. The investigated `电子档案台账` page is mainly `toolbarFragment + gridFragment`, with runtime behavior generated into `_demoGrid_config` and platform scripts such as `platformMethod.js` and `platformEvent.js`. The design editor is Vue2/Element UI, but the user-facing runtime is not a normal maintainable frontend project.

The two requested additions are:

- Knowledge-base Q&A, preferably reachable through a floating ball.
- OCR certificate/photo recognition integrated into existing upload locations, with automatic form filling only after review.

The knowledge base appears to be an existing or planned system that is not currently connected to these XCreator pages. The first implementation should therefore reserve a stable adapter contract and UI entry while keeping the feature hidden, stubbed, or pointed at a test endpoint until the real knowledge-system API is known.

Both features handle sensitive production context. They must be built as controlled, environment-aware services and integrated into XCreator pages through a small loader/bridge. They must not require ad hoc production edits, hardcoded localhost endpoints, or direct mutation of business records.

Supporting implementation notes:

- `knowledge-adapter-contract.md` defines the reserved contract for the existing knowledge-base system.
- `ocr-upload-integration-notes.md` defines how OCR attaches to current upload/photo controls.

## Goals / Non-Goals

**Goals:**

- Provide a page-embedded assistant widget that can later answer from the existing approved knowledge base with citations.
- Define and implement a knowledge-system adapter contract even if the real backend is not connected in the first milestone.
- Provide OCR extraction for supported certificates/photos attached through existing upload controls and map recognized fields into XCreator forms after user review.
- Keep integration compatible with WUI/jQuery/jqGrid runtime pages and page JSON configuration.
- Support page-level enablement, upload-slot configuration, and field mapping by `appCode`, `pageCode`, `pageId`, tenant, and environment.
- Preserve production safety: no save/submit/delete/归档 actions are triggered by the assistant or OCR fill bridge.
- Keep the knowledge and OCR services independently testable outside XCreator.

**Non-Goals:**

- Do not rewrite XCreator or export all low-code pages into a new application in this change.
- Do not replace the current grid/list business APIs.
- Do not submit forms automatically after OCR fill.
- Do not train a custom OCR model in the first implementation unless baseline OCR quality is insufficient.
- Do not build a replacement knowledge-base management system in this change.
- Do not ingest private production documents into a third-party model, cloud OCR service, or external knowledge system without explicit approval.

## Decisions

### Decision 1: Use a thin XCreator loader plus external assistant/OCR services

The page integration will be a small JavaScript loader that creates the floating UI, reads safe page context, and communicates with backend services. Knowledge retrieval, OCR, field mapping, audit, and configuration live outside the low-code page JSON.

Alternative considered: implement everything as XCreator custom scripts. This is fast for a prototype but brittle, hard to test, and dangerous in production because logic would be scattered across hidden script fields and page configuration.

### Decision 2: Prefer a floating assistant widget with a fallback menu/page entry

The primary UX is a floating ball that expands into a side panel or modal. If page-level script injection is blocked or too risky, the fallback is a normal XCreator menu/button that opens the same assistant page in an iframe or new window.

Alternative considered: embed a large permanent panel into each page. That consumes space in jqGrid-heavy operational screens and increases the chance of layout regressions.

### Decision 3: Reserve a knowledge-system adapter instead of owning the knowledge base

The assistant backend will define an adapter contract for `ask`, `search`, `source lookup`, health, authentication, and error responses. Until the existing knowledge system is connected, the assistant can run in disabled mode, stub mode, or test-fixture mode. The XCreator widget and page configuration will not assume a specific knowledge vendor or storage model.

Alternative considered: implement a new full ingestion/indexing knowledge base now. This creates avoidable duplication if the organization already has a system and would delay the page integration work.

### Decision 4: Treat knowledge answers as retrieval-grounded, not general chat

The assistant must use the configured knowledge adapter and return source citations when answers are supported. If the adapter returns no usable source, the assistant must say it cannot answer from the knowledge base. Page context such as `appCode`, `pageCode`, selected record type, and visible form labels may be passed as retrieval hints, but not as unrestricted prompt data.

Alternative considered: connect a general chat model directly. That would be easier but creates hallucination, data leakage, and audit risks.

### Decision 5: Attach OCR to existing upload controls

OCR will be configured per existing upload/photo widget or upload slot. When a user selects or uploads a configured image/document, the enhancement can offer recognition using the selected file or resulting attachment reference while preserving the original upload behavior. This keeps OCR where users already work instead of adding a disconnected page.

Alternative considered: create a standalone OCR page where users upload documents and copy values back manually. This avoids page integration but loses the main benefit and creates duplicate upload steps.

### Decision 6: Make OCR a draft-to-confirm workflow

OCR output becomes a reviewable draft with field values and confidence. The user confirms which fields to apply. The fill bridge writes values into controls associated with the current upload slot and triggers change events only; it does not save, submit, approve, delete, archive, or call business action endpoints.

Alternative considered: OCR uploads and directly submits the form. This is rejected because certificate OCR will be imperfect and because production business actions must remain explicitly user-controlled.

### Decision 7: Use pluggable OCR providers, with on-prem as the default assumption

The OCR service will expose a provider interface. The first provider should be deployable on-prem or inside the trusted network, such as PaddleOCR/RapidOCR-style engines or an existing internal OCR service. Cloud OCR can remain an optional provider only after data handling approval.

Alternative considered: start with a cloud OCR API. This can improve accuracy for common IDs but may violate data handling expectations for certificates and internal business documents.

### Decision 8: Store configuration centrally, not inside every page script

Feature flags, knowledge adapter endpoint aliases, OCR document types, upload-slot bindings, and field mappings will be stored in a backend configuration table/file keyed by tenant, app, page, and environment. The loader fetches this config at runtime.

Alternative considered: hardcode per-page config in `staticPageDesign` scripts. This repeats logic and risks production drift.

### Decision 9: Add an XCreator-safe form bridge

The form bridge will locate fields by configured selectors, XCreator widget IDs, upload-slot relationship, labels, or stable field names. It will support common WUI controls and expose a dry-run mode that reports unresolved fields before any fill occurs.

Alternative considered: rely only on DOM label matching. That is convenient but too ambiguous for Chinese forms with repeated labels or hidden jqGrid editors.

## Risks / Trade-offs

- Production page integration could affect layout or event behavior -> start in a cloned/test page, load the widget only behind explicit config, and provide the fallback page entry.
- Knowledge-system interface is not confirmed yet -> reserve a strict adapter contract, support stub/disabled modes, and avoid committing to a storage/indexing implementation.
- Knowledge answers may hallucinate or expose unauthorized content -> enforce adapter-grounded answers, citations, permission filters, and audit logs.
- OCR may misread certificates -> show confidence, require user confirmation, and never auto-submit.
- Upload controls may be implemented differently across low-code pages -> start with one or two known upload widget patterns, keep the original upload flow intact, and add dry-run diagnostics.
- Field mappings may drift when low-code pages are edited -> provide mapping validation and a dry-run check in each environment.
- Browser token handling is sensitive -> the loader must not log `cwUserToken` or copy it into documents; backend calls should use a controlled session/proxy pattern.
- Hardcoded endpoints can break production -> all assistant/OCR URLs must come from environment config, not `localhost`.
- Large document uploads can affect performance -> enforce file size/page limits and asynchronous status polling for slower OCR jobs.

## Migration Plan

1. Build the assistant/OCR services and widget in a standalone local or test environment.
2. Create a cloned XCreator test page or non-production app that mirrors the target page.
3. Add only the loader script or fallback menu entry in the test environment.
4. Configure the knowledge assistant in stub mode or against a test adapter endpoint until the existing knowledge-system API is confirmed.
5. Configure one existing upload slot and one OCR document type with a small, non-sensitive sample set.
6. Validate the widget loads without changing grid rendering, search, pagination, upload, or operation buttons.
7. Validate OCR fill in dry-run mode, then confirmed-fill mode, without saving forms.
8. Add audit logs and redaction checks.
9. Pilot with selected pages/users.
10. Promote to production only after endpoint config, permission filtering, and rollback are verified.

Rollback strategy:

- Disable the page-level feature flag to hide the floating widget.
- Remove or disable the loader script/menu entry if needed.
- Keep backend services deployable independently so disabling the integration does not affect existing XCreator pages.

## Open Questions

- Which certificate/document types are first priority: ID card, business license, construction permit, qualification certificate, archive cover sheet, or another internal template?
- What is the actual existing knowledge-base system endpoint, authentication mechanism, request schema, response schema, and source-citation format?
- Which existing upload/photo controls should be the first OCR integration targets?
- Does the deployment environment require fully on-prem OCR/LLM, or can approved cloud services be used for non-sensitive pilots?
- Which XCreator page should be the first integration target after the cloned test page?
