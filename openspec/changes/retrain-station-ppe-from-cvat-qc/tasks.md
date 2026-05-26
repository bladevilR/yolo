## 1. CVAT Snapshot And Safety

- [x] 1.1 Create a reusable CVAT task export script that writes a timestamped annotation backup, YOLO labels, and snapshot manifest without importing or mutating CVAT.
- [x] 1.2 Export a fresh snapshot of task 1/job 1 and verify image count, label file count, class map, and total box count: `E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1\cvat_snapshots\task1_20260522_113918\snapshot_manifest.json` (`200` images, `200` label files, `2163` boxes; `person=1012`, `helmet=678`, `vest=473`).
- [x] 1.3 Preserve the existing `task1_manual_121_backup_before_supervision_20260522_104756.json` as historical evidence and record it in the new snapshot manifest.
- [x] 1.4 Add a safety check that refuses to write into the live CVAT import directory or overwrite existing snapshot outputs unless an explicit new timestamp is used.

## 2. Review Manifest And QC Queue

- [x] 2.1 Create or update a review manifest for all 200 current CVAT images with frame name, snapshot ID, manual status, reviewer, review date, sample profile, QC flags, and notes: `E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1\cvat_snapshots\task1_20260522_113918\review_manifest.csv`.
- [x] 2.2 Import supervision QC results into the manifest, including duplicate-box, orphan-PPE, empty-label, malformed-row, invalid-class, non-positive-box, and missing-label flags.
- [x] 2.3 Generate a prioritized review queue for the current 11 duplicate-box issues and 44 orphan-PPE issues with overlay and contact-sheet references: `E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1\cvat_snapshots\task1_20260522_113918\qc_review_queue.csv` (`56` rows including `1` empty-label review row).
- [x] 2.4 Generate a human review instruction sheet for CVAT that explains how to mark `done`, `skip`, `stress-only`, hard negative, visible vest, partial worker, tiny worker, and unclear cases: `E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1\cvat_snapshots\task1_20260522_113918\CVAT_REVIEW_INSTRUCTIONS.md`.
- [x] 2.5 Pause promotion until the user confirms which images are reviewed or provides a completed manifest; do not infer the 121 edited images from object counts alone.

## 3. Dataset Promotion

- [ ] 3.1 Implement a promotion script that accepts only `manual_status=done` samples for normal train/validation/test splits.
- [ ] 3.2 Allow `skip` and `stress-only` samples to be excluded from normal splits while preserving them in manifest/report outputs.
- [ ] 3.3 Validate class IDs as exactly `0=person`, `1=helmet`, and `2=vest`, and reject `no_helmet` or `no_vest` as training classes.
- [ ] 3.4 Generate frozen train, validation, test, stress, and demo/evaluation split manifests with source-frame and sample-profile metadata.
- [ ] 3.5 Generate a dataset report with image counts, empty-label counts, hard-negative counts, class counts by split, QC issue counts, and provenance warnings.

## 4. Controlled Retraining Experiments

- [ ] 4.1 Create a reproducible training entrypoint for `v3a_cvat_pilot` and `v3b_cvat_reviewed_candidate` runs that records dataset snapshot, split manifests, parameters, seed, device, and output paths.
- [ ] 4.2 Run `v3a_cvat_pilot` only after critical QC flags in the reviewed subset are resolved, and label it as pilot-only if not all 200 current CVAT images are reviewed or skipped.
- [ ] 4.3 Run a candidate YOLOv8n baseline on the frozen reviewed dataset and compare it to `station_ppe_20260519_codex_v2_3class`.
- [ ] 4.4 Run a controlled 640 vs 960 image-size experiment using the same dataset snapshot and split manifests.
- [ ] 4.5 If deployment constraints allow, run a controlled YOLOv8n vs YOLOv8s experiment and record accuracy/latency trade-offs separately.
- [ ] 4.6 Preserve each run's weights, `args.yaml`, `results.csv`, plots, confusion matrices, validation predictions, and run manifest.

## 5. Evaluation And Candidate Decision

- [ ] 5.1 Evaluate each run on normal validation and test splits with precision, recall, mAP50, mAP50-95, per-class metrics, and confusion matrices.
- [ ] 5.2 Evaluate each run on the stress split with false-person cases, duplicate-person cases, missed-worker cases, PPE confusion cases, and hard-negative examples.
- [ ] 5.3 Run the strict demo/event pipeline for the leading candidate and generate annotated outputs, event CSV, rejected candidates, and manual review queue summaries.
- [ ] 5.4 Manually review demo events and report suspected no-helmet precision/recall, suspected no-vest precision/recall where labels support it, false event count, duplicate event count, and review queue volume.
- [ ] 5.5 Produce a candidate decision report labeled `demo-ready`, `pilot-ready`, `business-acceptance-ready`, or `rejected`, with reasons and next actions.

## 6. Documentation And Verification

- [ ] 6.1 Update the current work summary to reflect the new CVAT snapshot, supervision QC gate, reviewed dataset path, training run IDs, and candidate decision.
- [ ] 6.2 Document that high-angle identity recognition, face recognition, `no_helmet`/`no_vest` object classes, and cross-camera tracking remain out of scope.
- [ ] 6.3 Add unit tests for snapshot export, review manifest merge, promotion gating, split generation, and dataset report validation.
- [ ] 6.4 Run the relevant pytest suite and `openspec validate retrain-station-ppe-from-cvat-qc --strict`.
- [ ] 6.5 Record final artifact paths for the promoted dataset, training runs, QC outputs, and decision report in `tasks.md` or a linked report before archiving.
