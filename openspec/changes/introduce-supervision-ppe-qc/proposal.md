## Why

The station PPE pipeline is still early enough that the visual QA and evaluation surface can be standardized before more scripts accumulate around hand-written OpenCV drawing, YOLO label parsing, and ad hoc error reports. Introducing `supervision` now gives the project a stable computer-vision utility layer for overlays, dataset QA, and acceptance diagnostics without disrupting the already working CVAT and Ultralytics training path.

## What Changes

- Add `supervision` as a pinned project dependency for PPE QA, visualization, and evaluation utilities.
- Introduce a reusable station PPE helper layer that converts YOLO labels and model outputs into `supervision.Detections`.
- Add a CLI workflow for generating supervision-backed overlays, contact sheets, and label-quality summaries from image/label directories.
- Add dataset QA checks that flag empty labels, malformed boxes, invalid classes, orphan PPE boxes, duplicate boxes, and per-class distribution.
- Keep CVAT as the human review surface and Ultralytics as the training/inference engine; this change does not replace either system.
- Defer deeper video tracking and zone logic to later work after the detector and reviewed dataset stabilize.

## Capabilities

### New Capabilities

- `station-ppe-vision-qc`: Defines supervision-backed visual QA, label conversion, overlay rendering, contact-sheet generation, and dataset quality summary behavior for the station PPE pipeline.

### Modified Capabilities

- None.

## Impact

- Adds a Python dependency: `supervision>=0.28.0,<0.29.0`.
- Affects `requirements.txt`.
- Adds focused code under `data_factory/` for supervision conversions, rendering, and QA summaries.
- Adds a script under `scripts/` to run supervision-backed PPE QC over CVAT/YOLO review exports.
- Adds tests covering YOLO-to-detections conversion, QA counting, and rendering smoke behavior.
- Does not change the current CVAT task format, existing reviewed labels, OpenSpec retraining change, or Ultralytics training commands.
