## Why

The现场调研素材 shows three quality-control opportunities that can be validated quickly with phone photos: steel material counting, rebar coupler exposed-thread checks, and concrete surface defect screening. Defining these as a focused AI QC pilot now will turn the field photos into clear capture rules, model outputs, and review workflows instead of a broad "AI inspection" request.

## What Changes

- Introduce a field-photo AI QC workflow that accepts photos/videos with project location metadata, runs scenario-specific analysis, and returns annotated evidence for human review.
- Add steel/rebar material counting for端面清晰的成捆钢筋, with counts, annotated detections, and manual-review flags for occluded or side-view piles.
- Add rebar mechanical coupler exposed-thread screening, including coupler detection, left/right thread-region detection, and rule-based suspicious/non-compliant flags based on project thresholds.
- Add concrete surface quality screening for visible defects such as honeycombing, pitting, exposed aggregate/rebar, holes, cracks, leakage marks, repair patches, and color/finish anomalies.
- Keep the first delivery as an assisted-inspection Demo/POC: AI produces evidence and疑似问题, while final acceptance remains a human quality decision.
- Defer production mobile app store distribution, BIM comparison, millimeter-level measurement without calibration, and fully automated final compliance decisions to later changes.

## Capabilities

### New Capabilities

- `field-qc-capture-workflow`: Defines photo/video intake, metadata, capture guidance, review states, and evidence output shared by all field AI QC scenarios.
- `rebar-material-counting`: Defines steel/rebar bundle counting behavior for端面可见 materials, including confidence, occlusion handling, and review output.
- `rebar-coupler-thread-qc`: Defines rebar mechanical coupler and exposed-thread quality screening behavior, including threshold-based compliance flags.
- `concrete-surface-qc`: Defines concrete surface defect screening behavior for visible defects and surface anomalies from field photos.

### Modified Capabilities

- None.

## Impact

- Adds OpenSpec requirements for a new AI QC pilot separate from the existing PPE-focused pipeline.
- Will likely add dataset organization for the现场调研素材 and future labeled samples.
- Will affect or add inference scripts for scenario routing, image annotation, JSON/CSV report output, and optional contact-sheet QA.
- May later affect mobile/H5 upload flows, but the first proposal can run as an offline or local web Demo before mobile productization.
- Requires business inputs for coupler exposed-thread thresholds, counting units, concrete defect taxonomy, and photo-capture standards.
