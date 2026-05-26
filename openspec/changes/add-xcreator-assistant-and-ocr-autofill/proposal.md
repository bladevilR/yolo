## Why

The XCreator platform is difficult to extend because business behavior is spread across page JSON, WUI/jqGrid runtime scripts, rule pages, and backend service codes. Users need two focused productivity additions: a knowledge-base Q&A assistant that can be reached from existing low-code pages through a reserved interface to the existing knowledge system, and OCR-based certificate/photo recognition integrated into current upload flows to reduce manual form entry without directly mutating production data.

## What Changes

- Add an embeddable knowledge assistant entrypoint for XCreator pages, surfaced as a floating ball or equivalent non-invasive widget.
- Reserve a knowledge-system adapter API so the assistant can call the existing knowledge base once its endpoint, authentication, and response schema are confirmed.
- Provide a stub/mock mode for development and a disabled/placeholder mode when the knowledge system is not yet connected.
- Add OCR recognition to existing photo/attachment upload locations, extracting structured fields from uploaded or selected images into a reviewable draft.
- Add a form-fill bridge that maps OCR fields into nearby or configured XCreator page fields only after user confirmation.
- Add tenant/app/page-level configuration so each page can enable the assistant, OCR, neither, or both.
- Add safety controls for production: read-only preview first, explicit confirmation before fill, audit logging, token redaction, and environment-specific endpoint configuration.
- Keep existing XCreator runtime pages working; no breaking change to existing page JSON, grid data APIs, or menu routes.

## Capabilities

### New Capabilities

- `xcreator-knowledge-assistant`: Defines the embeddable knowledge-base Q&A assistant, reserved adapter contract to the existing knowledge system, answer safety, source citation, and page-level enablement.
- `xcreator-ocr-autofill`: Defines OCR integration on existing photo/attachment upload controls, field extraction, confidence handling, user review, and confirmed form auto-fill behavior.

### Modified Capabilities

- None.

## Impact

- Affects XCreator runtime integration points described in `docs/xcreator-lowcode-platform-handbook.md`, especially floating UI injection, page-level custom scripts/configuration, and service URL mapping.
- Adds new backend services or adapters for knowledge Q&A proxying, OCR extraction, field mapping, audit logs, and configuration.
- Adds frontend assets for a floating assistant widget and OCR review panel that must work inside WUI/jQuery/jqGrid pages without relying on unsafe production page edits.
- Touches existing upload/photo widgets only through a reversible enhancement layer; the original upload behavior must remain available.
- Requires a non-production integration environment or cloned page/app before touching the formal production system.
- Requires endpoint configuration to avoid hardcoded localhost or environment-specific URLs in production page config.
