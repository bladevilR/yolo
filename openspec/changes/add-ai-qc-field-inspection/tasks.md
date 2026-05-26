## 1. Data Inventory And Scenario Setup

- [x] 1.1 Create a field-QC dataset layout under `datasets/field_qc/` with separate folders for `rebar_material_counting`, `rebar_coupler_thread_qc`, `concrete_surface_qc`, and shared reports.
- [x] 1.2 Copy or index the current `E:\yolo\素材` photos and videos into scenario inventories without mutating the original files.
- [x] 1.3 Generate a media manifest containing file path, media type, scenario candidate, dimensions, capture notes, and review status.
- [x] 1.4 Create a capture-quality review sheet that marks endpoint photos, side-view material piles, coupler close-ups, concrete overview photos, blur, glare, occlusion, and missing scale.

## 2. Business Rules And Label Taxonomy

- [x] 2.1 Define mandatory site metadata fields for all AI QC submissions.
- [ ] 2.2 Confirm steel/rebar counting unit: root/bar, bundle, batch, or receipt-line quantity.
- [ ] 2.3 Confirm rebar coupler exposed-thread thresholds by coupler type and steel diameter.
- [x] 2.4 Define concrete surface taxonomy for the first pilot, including defect classes and a generic `surface-anomaly-needs-review` class.
- [x] 2.5 Write scenario capture guidance for endpoint counting, coupler side-on close-ups, and concrete overview plus close-up photo pairs.

## 3. Shared Field QC Workflow

- [x] 3.1 Implement media manifest loading and scenario routing for local image folders.
- [x] 3.2 Implement metadata validation that flags missing project, area, floor or zone, component or material identifier, photographer, timestamp, and scenario.
- [x] 3.3 Implement basic image quality checks for blur, exposure, cropping, and target-presence review flags.
- [x] 3.4 Implement common annotated evidence and JSON/CSV report writers.
- [x] 3.5 Add a review-state model with `awaiting_review`, `accepted`, `rejected`, and `corrected` statuses.

## 4. Rebar Material Counting Demo

- [x] 4.1 Build a first endpoint-bar detection/counting prototype for clear bundle endpoint images.
- [x] 4.2 Add occlusion and side-view handling that marks unsuitable images as estimate-only or recapture-needed.
- [x] 4.3 Output annotated counted instances, total count, confidence summary, and review flag per image.
- [x] 4.4 Run the prototype on the current field material photos and save report artifacts.
- [x] 4.5 Review count results manually and record typical error cases for the next sample-collection round.

## 5. Rebar Coupler Exposed-Thread QC Demo

- [x] 5.1 Build a first detector or heuristic prototype for coupler location and adjacent thread-region localization.
- [x] 5.2 Implement threshold configuration for exposed thread count or exposed length rules.
- [x] 5.3 Add ambiguity flags for cropped couplers, glare, blur, rust, occlusion, overlapping bars, and missing thresholds.
- [x] 5.4 Output annotated coupler evidence, left/right exposed-thread evidence, configured threshold, decision, and review flag.
- [x] 5.5 Run the prototype on the current coupler photos and summarize suspected non-compliant and needs-review cases.

## 6. Concrete Surface QC Demo

- [x] 6.1 Build a first concrete surface anomaly screening prototype using the confirmed defect taxonomy.
- [x] 6.2 Support overview and close-up media linkage in the local manifest.
- [x] 6.3 Add measurement gating so width, length, or area is only reported when scale or calibration exists.
- [x] 6.4 Output annotated suspected regions, anomaly class, confidence, measurement status, and review flag.
- [x] 6.5 Run the prototype on the current concrete photos and identify which defect classes need more positive samples.

## 7. Verification And Acceptance

- [x] 7.1 Add tests for metadata validation, scenario routing, report writing, and review-state transitions.
- [x] 7.2 Add smoke tests for each scenario prototype using a small fixture image set.
- [x] 7.3 Produce a Demo package containing annotated images, JSON/CSV summaries, and a short written feasibility note.
- [x] 7.4 Run OpenSpec validation for `add-ai-qc-field-inspection`.
- [ ] 7.5 Review the Demo outputs with stakeholders and decide whether the next delivery surface is offline script, local web page, H5 upload flow, Android APK, or iOS-compatible path.
