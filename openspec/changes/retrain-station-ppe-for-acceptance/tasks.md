## 1. Baseline And Data Audit

- [x] 1.1 Freeze the V2 baseline by recording model path, dataset path, class counts, split composition, validation metrics, test metrics, strict_v5 event counts, and known failure modes in a baseline report.
- [x] 1.2 Audit `station_ppe_20260519_priority_label_fix_v1_review_workspace` and `station_ppe_20260520_review_queue_v5_workspace` for review status, label paths, duplicate image names, empty labels, and Codex draft provenance.
- [x] 1.3 Define the v3 class map as exactly `person`, `helmet`, and visible `vest`, with `no_helmet` and `no_vest` reserved for event-layer logic only.
- [x] 1.4 Define annotation rules for visible vest boxes, helmet boxes, partial workers, tiny/edge workers, hard negatives, unclear samples, and skipped samples.

## 2. Human Review Workflow

- [x] 2.1 Create or update a review queue that combines the 128-image priority batch, the V5 review rows, and additional selected samples needed to reach the target 200-400 human-reviewed images.
- [ ] 2.2 Human-review and mark complete all accepted training samples with corrected `person`, `helmet`, and visible `vest` labels.
- [ ] 2.3 Convert bags, covers, materials, pipes, extinguishers, and other false-person examples into reviewed hard-negative samples with false person boxes removed.
- [ ] 2.4 Keep unclear or low-signal samples out of normal validation unless they are explicitly tagged for stress evaluation.
- [ ] 2.5 Record reviewer, review date, label source, manual status, notes, and sample profile in the manifest for every candidate image.

## 3. Dataset Promotion

- [ ] 3.1 Implement or update promotion tooling so only `manual_status=done` human-reviewed samples can enter the acceptance-oriented v3 dataset.
- [ ] 3.2 Generate the v3 YOLO dataset with train, validation, test, stress, and demo/evaluation manifests.
- [ ] 3.3 Ensure normal train/validation/test splits are stratified by source video, scene profile, camera view, and sample type.
- [ ] 3.4 Keep hard-negative, many_boxes, empty_detection, tiny, edge, and occluded samples available as separately reported stress data.
- [ ] 3.5 Generate a dataset report with image counts, empty-label counts, hard-negative counts, per-class counts by split, and provenance warnings.

## 4. Retraining Experiments

- [ ] 4.1 Create a reproducible training script for `station_ppe_20260521_v3_human_reviewed_3class` that records model, data path, image size, epochs, seed, device, and output directory.
- [ ] 4.2 Train a YOLOv8n baseline on the v3 dataset and compare it against `station_ppe_20260519_codex_v2_3class`.
- [ ] 4.3 Run a controlled image-size experiment, such as 640 vs 960, using the same v3 dataset and fixed split.
- [ ] 4.4 If deployment constraints allow, run a controlled model-scale experiment such as YOLOv8n vs YOLOv8s using the same dataset and split.
- [ ] 4.5 Preserve every run's `args.yaml`, `results.csv`, weights, confusion matrices, label plots, and training report.

## 5. Evaluation And Acceptance Reporting

- [ ] 5.1 Evaluate each candidate on normal validation and test splits with precision, recall, mAP50, mAP50-95, and per-class confusion matrices.
- [ ] 5.2 Evaluate each candidate on the stress set with false-person rate, duplicate-person rate, missed-worker examples, PPE confusion examples, and hard-negative failure cases.
- [ ] 5.3 Run the strict demo/event pipeline for the leading candidate and generate annotated images, event CSV, rejected candidates, and manual review queue summaries.
- [ ] 5.4 Manually review demo events and report auto-demo events, needs-review events, rejected candidates, suspected no-helmet precision/recall, and suspected no-vest precision/recall.
- [ ] 5.5 Produce a candidate decision report that clearly labels the result as demo-ready, pilot-ready, business-acceptance-ready, or rejected with reasons.

## 6. Documentation And Handoff

- [ ] 6.1 Update the current work summary to distinguish V2 Codex auto-reviewed training from v3 human-reviewed retraining.
- [ ] 6.2 Update the multimodal QC notes with v3 dataset provenance, training run IDs, evaluation results, and final candidate decision.
- [ ] 6.3 Document remaining non-goals, especially identity-level face recognition and cross-camera tracking, as requiring separate near/mid camera data collection.
- [ ] 6.4 Archive failed or superseded experiment outputs with concise failure reasons so future work does not repeat unhelpful tuning loops.
