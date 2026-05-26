## Context

The current station PPE workflow already uses CVAT for human review, Ultralytics for model training/inference, and several project-local scripts for YOLO label parsing, overlays, contact sheets, and auto-completion. Those scripts work, but they duplicate common computer-vision utilities such as box conversion, drawing, class filtering, duplicate detection, and per-image QA summaries.

`supervision` is a good fit now because the project is still early: the dataset and acceptance workflow are being shaped, and standardizing the QA layer before it spreads further will reduce future rework. The dependency should be introduced as an auxiliary utility layer only. CVAT remains the source of human truth, and Ultralytics remains the detector training path.

## Goals / Non-Goals

**Goals:**

- Provide a reusable `data_factory` module that converts station PPE YOLO labels into `supervision.Detections`.
- Generate supervision-backed overlays and contact sheets for fast human spot checks.
- Produce machine-readable QC summaries for class counts, malformed labels, invalid classes, empty labels, duplicate boxes, and orphan PPE boxes.
- Make the helper usable against both CVAT review exports and local YOLO label directories.
- Keep the first implementation narrow, tested, and independent from the retraining OpenSpec change.

**Non-Goals:**

- Do not replace CVAT as the manual annotation/review tool.
- Do not replace Ultralytics model training, validation, or export.
- Do not automatically promote supervision-generated summaries to human-approved gold labels.
- Do not introduce video tracking, zone-based event logic, or ByteTrack in this first change.
- Do not rewrite existing demo and retraining scripts unless they opt into the new helper.

## Decisions

1. Add `supervision>=0.28.0,<0.29.0` as a pinned dependency.

   Rationale: version `0.28.0` is the current published release visible from pip, and the project should avoid a floating dependency while supervision APIs are still evolving. The upper bound keeps implementation behavior reproducible. Alternative considered: leave supervision optional. That would reduce install impact but would make the new CLI unreliable and would not establish the utility layer clearly.

2. Introduce `data_factory/supervision_ppe.py` instead of modifying training code directly.

   Rationale: a focused adapter isolates dependency usage and keeps CVAT/YOLO training paths stable. Existing scripts can adopt it incrementally. Alternative considered: refactor `render_yolo_labels.py` in place. That is faster but increases regression risk for currently useful QA artifacts.

3. Use `supervision.Detections` as the internal box representation for new QA utilities.

   Rationale: supervision provides a normalized detection model that can represent labels loaded from YOLO files and model predictions converted from Ultralytics results. This lets downstream rendering and future evaluation code share one representation. Alternative considered: keep project-specific `BoxLabel` dataclasses everywhere. That avoids a dependency but preserves the current duplication.

4. Keep dataset QC conservative and descriptive.

   Rationale: QC output should flag suspicious samples, not silently edit labels or decide business acceptance. The CLI will report issues and draw artifacts; any actual label modification remains in CVAT or explicit auto-completion scripts. Alternative considered: integrate automatic correction in the same tool. That would be tempting but would blur the line between review evidence and label mutation.

5. Defer video tracking and zone logic.

   Rationale: supervision's tracking and polygon-zone tools are promising for reducing repeated alerts in fixed-camera video, but the current blocker is still reviewed detector labels and static-frame acceptance. Tracking should come after detector quality and per-frame QA stabilize.

## Risks / Trade-offs

- Dependency API drift -> Pin `<0.29.0`, centralize supervision calls in one adapter, and cover conversion/rendering with tests.
- Additional install weight -> Keep the first feature optional at workflow level and avoid importing supervision in unrelated training modules.
- False sense of label quality -> Name outputs as QC/suspicion reports and keep CVAT as the review authority.
- Rendering differences vs current overlays -> Generate new supervision outputs beside existing artifacts rather than replacing them immediately.
- Orphan PPE heuristics may not capture every edge case -> Report counts and sample names; do not auto-delete from labels in this change.

## Migration Plan

1. Add the dependency to `requirements.txt`.
2. Add `data_factory/supervision_ppe.py` with conversion, rendering, and QC helpers.
3. Add `scripts/supervision_station_ppe_qc.py` as a CLI entry point.
4. Add tests for conversion, QC summaries, and a smoke overlay/contact-sheet render.
5. Run the CLI on the current CVAT auto-completed labels to produce a new supervision QC package.
6. Leave existing OpenCV/PIL render scripts available until the new helper has been used on real review batches.

Rollback is simple: remove the dependency and new helper/CLI files. Existing CVAT labels, review zips, and training scripts are not changed by this proposal.

## Open Questions

- Whether later work should use supervision metrics for a custom validation report in addition to Ultralytics `val` outputs.
- Whether video tracking and polygon-zone filtering should become a separate OpenSpec change after the next retraining run.
