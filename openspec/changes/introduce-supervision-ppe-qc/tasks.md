## 1. Dependency And Adapter Setup

- [x] 1.1 Add `supervision>=0.28.0,<0.29.0` to `requirements.txt`.
- [x] 1.2 Create `data_factory/supervision_ppe.py` with station PPE class configuration and color mapping.
- [x] 1.3 Implement YOLO label parsing that records malformed rows, invalid class IDs, and non-positive boxes.
- [x] 1.4 Implement conversion from valid YOLO rows to `supervision.Detections` in pixel-space coordinates.

## 2. Dataset QC

- [x] 2.1 Implement per-image and aggregate QC counting for images, label files, empty labels, and class instances.
- [x] 2.2 Implement duplicate-box detection using same-class IoU thresholds.
- [x] 2.3 Implement orphan PPE detection for `helmet` and `vest` boxes not associated with any `person` box.
- [x] 2.4 Write `qc_summary.json` and optional `qc_issues.csv` outputs without mutating source labels.

## 3. Supervision Rendering CLI

- [x] 3.1 Add `scripts/supervision_station_ppe_qc.py` with `--images`, `--labels`, `--output`, and `--classes` arguments.
- [x] 3.2 Render per-image overlays using supervision annotators with stable station PPE colors and readable labels.
- [x] 3.3 Render paginated contact sheets for fast human spot checks.
- [x] 3.4 Ensure output artifacts are written beside source data in a separate output directory.

## 4. Tests And Verification

- [x] 4.1 Add unit tests for valid YOLO-to-Detections conversion.
- [x] 4.2 Add unit tests for malformed labels, invalid classes, empty label files, duplicate boxes, and orphan PPE flags.
- [x] 4.3 Add a rendering smoke test that creates at least one overlay/contact sheet with supervision installed.
- [x] 4.4 Run the new CLI on the current CVAT auto-completed review labels and record the generated summary path: `E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1\supervision_qc_task1_current_20260522_104756\qc_summary.json`.
- [x] 4.5 Run the relevant pytest suite and OpenSpec validation.
