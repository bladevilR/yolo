## Context

The previous retraining change was written before the current CVAT review state existed. The project now has a CVAT task at `http://localhost:8080/tasks/1/jobs/1` where the user has manually edited 121 images, plus a read-only backup and YOLO export captured before introducing supervision QC:

```text
E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1\cvat_import\task1_manual_121_backup_before_supervision_20260522_104756.json
E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1\labels_cvat_task1_current_20260522_104756
```

The supervision QC snapshot contains 200 images, 2163 boxes, and no malformed rows, invalid classes, non-positive boxes, or missing labels. It still flags 11 duplicate boxes and 44 orphan PPE boxes. Those flags are review leads, not automatic corrections.

The next training plan must therefore treat CVAT as the human source of truth, protect the user's manual edits, and make promotion into training explicit. The model target remains `person`, `helmet`, and visible `vest`; `no_helmet` and `no_vest` are downstream event states rather than training classes.

## Goals / Non-Goals

**Goals:**

- Preserve the current CVAT task and all manual edits before any dataset preparation.
- Convert the current task into a reviewed, reproducible YOLO dataset with manifest-backed provenance.
- Use supervision QC as a pre-training gate and human-review accelerator.
- Run controlled retraining experiments that compare against the V2 baseline and report both detector metrics and event behavior.
- Produce a candidate decision report that can distinguish demo improvement from pilot or business acceptance.

**Non-Goals:**

- Do not overwrite the current CVAT task from generated labels.
- Do not train directly from Codex draft labels, raw model predictions, or unresolved QC issue labels.
- Do not add `no_helmet`, `no_vest`, identity, face recognition, or cross-camera tracking classes in this change.
- Do not claim acceptance from mAP alone.

## Decisions

### Decision 1: Snapshot CVAT before every promotion step

Every dataset promotion starts by exporting the CVAT task into a timestamped backup and YOLO label directory. Training consumes only those exported files, never live CVAT state.

Alternative considered: train directly from the latest local labels. This is faster but risks losing the distinction between human edits, generated labels, and stale exports.

### Decision 2: Make human review status explicit

The user-reported 121 edited images are valuable, but they are not enough as a machine-readable training gate by themselves. The promotion workflow will maintain a review manifest with `manual_status`, reviewer, review date, source snapshot, QC flags, and notes for every image.

Alternative considered: infer reviewed images from CVAT object counts or modification time. This is brittle and could train on partially reviewed frames.

### Decision 3: Use supervision QC as a review queue, not an auto-fixer

Duplicate and orphan PPE flags will create a focused review list. The workflow may generate overlays and contact sheets, but it will not delete or move boxes automatically.

Alternative considered: automatically remove duplicate boxes and orphan PPE. This was rejected because small helmets, partially visible vests, and occluded workers can look orphaned to geometry rules while still being valid.

### Decision 4: Split training into pilot and candidate phases

The first run can be a `v3a_cvat_pilot` after all critical QC flags in the current snapshot are reviewed and enough images are marked `manual_status=done`. It is only a feedback run. The candidate run should be `v3b_cvat_reviewed_candidate`, after the full 200-image task is reviewed or explicitly skipped, hard negatives are confirmed, and split manifests are frozen.

Alternative considered: wait for a larger 400-image dataset before any retraining. This is safer for acceptance but delays feedback on whether the current label corrections are moving the model in the right direction.

### Decision 5: Keep normal evaluation and stress evaluation separate

Normal validation/test splits should represent expected production-like frames. Hard negatives, many-box images, empty detections, tiny/edge workers, occlusion, and clutter should be reported as stress sets.

Alternative considered: mix hard cases into normal validation. That makes one metric hard to interpret and can hide whether failures are ordinary generalization issues or targeted stress failures.

### Decision 6: Select models by event behavior as well as detector metrics

The candidate must be evaluated through the strict demo/event pipeline. The report must include false person events, duplicate person events, manual-review queue size, and suspected PPE violation precision/recall where reviewed labels are available.

Alternative considered: select by best mAP50-95 only. This was rejected because the business-visible failures are event-level false alarms and missed PPE states.

## Risks / Trade-offs

- CVAT review status is not yet fully machine-readable -> require an explicit manifest and avoid assuming all 200 frames are reviewed.
- Only 200 images may remain too small for acceptance -> allow a pilot run but label it as pilot, and require additional data if metrics or stress results remain weak.
- Geometry-based orphan PPE checks can over-flag valid boxes -> treat QC flags as human-review prompts only.
- Vest detection may remain weak because visible vest examples are sparse or visually inconsistent -> require per-class count reporting and visible-vest examples across distance, color, occlusion, and lighting.
- Larger image size can improve small helmet recall but hurt deployment latency -> run controlled 640 vs 960 experiments and keep accuracy/latency trade-offs explicit.
- Hard negatives can reduce false positives but damage recall if over-weighted -> keep hard negatives in training with bounded ratios and separately report stress performance.

## Migration Plan

1. Keep the V2 model and old retraining change as historical baseline material.
2. Export a new CVAT snapshot before any training dataset build.
3. Generate supervision QC overlays, issue CSV, and contact sheets from that snapshot.
4. Build or update the review manifest and resolve all critical QC issues.
5. Promote only reviewed samples into a frozen YOLO dataset with split manifests.
6. Run pilot retraining, evaluate, and decide whether more review/data is needed before a candidate run.
7. Run candidate retraining only after dataset gates pass.
8. Keep rollback simple: continue using the V2 demo baseline until a v3 candidate report explicitly accepts a replacement.

## Open Questions

- Should the next immediate run be a quick `v3a_cvat_pilot`, or should training wait until all 200 current CVAT images are marked reviewed?
- What minimum target should mark success for the next milestone: improved demo, pilot-site trial, or formal business acceptance?
- Is RK3588 deployment latency a hard constraint for this cycle, or can 960-size accuracy experiments be used to learn first?
