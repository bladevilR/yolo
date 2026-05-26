# Station PPE Multimodal QC Notes

Date: 2026-05-19

## Role Definition

Use Codex multimodal review as a first-pass junior QA step, not as the final label authority.

The review target is to reduce human workload before formal annotation:

1. Remove obviously poor or repetitive samples.
2. Flag visible false positives, missed workers, missed helmets, and weak vest labels.
3. Select the best candidate frames for the first site-specific PPE training set.
4. Keep face recognition out of scope for this high-angle video batch.

## Reviewed Material

Source dataset:

```text
E:\yolo\datasets\station_ppe_20260519_v0
```

Visual QA sheets reviewed in this pass:

```text
E:\yolo\datasets\station_ppe_20260519_v0_pseudo_world_qa300\boxed_contact_sheets\boxed_contact_sheet_001.jpg
E:\yolo\datasets\station_ppe_20260519_v0_pseudo_world_qa300\boxed_contact_sheets\boxed_contact_sheet_002.jpg
E:\yolo\datasets\station_ppe_20260519_v0_pseudo_world_qa300\boxed_contact_sheets\boxed_contact_sheet_003.jpg
E:\yolo\datasets\station_ppe_20260519_v0_error_review240\boxed_contact_sheets\boxed_contact_sheet_001.jpg
E:\yolo\datasets\station_ppe_20260519_v0_error_review240\boxed_contact_sheets\boxed_contact_sheet_002.jpg
E:\yolo\datasets\station_ppe_20260519_v0_error_review240\boxed_contact_sheets\boxed_contact_sheet_003.jpg
```

## First-Pass Findings

The video batch can support a first PPE detection loop, but it is still a high-angle construction-site view. It is suitable for:

```text
person detection
helmet detection
coarse vest detection after human correction
area-level PPE event evidence
```

It is not suitable for:

```text
face recognition
identity-level tracking
reliable no_helmet / no_vest violation training without manual correction
```

Observed pseudo-label behavior:

```text
person: generally useful as a draft, but misses distant/edge workers
helmet: useful as a draft, but small helmets are often missed
vest: weak; treat as manual-label-first
no_helmet / no_vest: not available from this YOLO-World pseudo-label pass
```

Full pseudo-label count:

```text
person: 6604
helmet: 2664
vest: 53
```

## Sheet-Level Notes

### Pseudo QA Sheet 001

Range:

```text
0001_00000001874000000_f00000000.jpg
through
0020_00000001874000000_f00020750.jpg
```

Decision:

```text
usable_for_first_training: yes
needs_human_label_fix: yes
dedup_pressure: high
```

Notes:

- Many frames contain clear workers near the lower half of the image.
- Person and helmet boxes are often usable as starting boxes.
- The sequence is highly repetitive; keep a diverse subset rather than every frame.
- Vest labels are mostly absent even when reflective/orange clothing is visible.
- Faces are not usable because of distance, angle, and helmet occlusion.

### Pseudo QA Sheet 002

Range:

```text
0021_00000001874000000_f00021750.jpg
through
0040_00000001874000000_f00042500.jpg
```

Decision:

```text
usable_for_first_training: yes
needs_human_label_fix: yes
dedup_pressure: high
```

Notes:

- Good continuity of workers moving through the same area.
- Useful for teaching the model the local camera angle and steel-frame background.
- Several small helmets and workers near the image edge should be manually checked.
- Do not use this sequence alone; it will overfit to one camera and one local composition.

### Pseudo QA Sheet 003

Range:

```text
0041_00000001874000000_f00043625.jpg
through
0060_00000001876000000_f00009750.jpg
```

Decision:

```text
usable_for_first_training: mixed
needs_human_label_fix: yes
dedup_pressure: medium
```

Notes:

- The first part contains usable close/medium PPE examples.
- Some frames transition into fewer workers or harder distant cases.
- This sheet is useful for hard samples, but not all frames should be promoted.

### Error Review Sheets 001-002

Decision:

```text
use_as_hard_negative_or_low_priority: yes
promote_directly_to_training: no
```

Notes:

- Many `empty_detection` samples still contain very small or edge workers.
- These frames explain why the detector misses people: the worker is tiny, partially occluded, or near the frame edge.
- Keep a small number as hard negatives/hard positives, but avoid flooding the first training set with low-signal frames.

### Error Review Sheet 003

Decision:

```text
use_for_error_correction: yes
promote_directly_to_training: no
```

Notes:

- The `many_boxes` cases are useful for checking duplicate boxes and crowded worker groups.
- These frames should be manually reviewed before training because wrong duplicated boxes can hurt the model.
- Good source for crowded PPE cases after correction.

## QC Tags To Use

Recommended tags for the next review CSV:

```text
accept_train
needs_box_fix
needs_class_fix
vest_manual
helmet_missed
person_missed
duplicate_frame
hard_negative
discard_low_signal
face_not_applicable
```

## Recommended First Training Set

For the first meaningful training run, do not promote all 2564 pseudo labels. Build a reviewed set:

```text
200-400 images total
person / helmet / vest labels manually corrected
include 30-50 hard negatives or edge cases
exclude identity / face labels
do not train no_helmet / no_vest as detection classes yet
```

Violation events should be derived by rules after detection:

```text
person exists + no overlapping helmet -> suspected no helmet
person exists + no vest region/class -> suspected no vest
multi-frame confirmation -> event
```

## Next Multimodal QC Step

Continue sheet-by-sheet review and produce a CSV with:

```text
sample_image
source_video
frame_index
qc_status
required_action
notes
```

The practical target is to reduce the 300-image pseudo QA package into a curated 200-400 image human-corrected training subset.

## Updated Execution Plan

User instruction:

```text
Use Codex multimodal ability as a junior human QA reviewer, update the plan, then execute.
```

Execution plan:

1. Align QA sample metadata with source video, frame index, timestamp, pseudo labels, and contact-sheet page.
2. Review all 15 QA contact sheets, 300 samples total, as a visual first-pass QA.
3. Assign sheet-level visual profiles:

```text
main_train
mixed_train
hard_case
low_signal
```

4. Generate a full first-pass QC CSV for all 300 QA samples.
5. Build a selected label-fix queue that combines:

```text
main/mixed QA samples
hard cases from low-signal sheets
targeted empty_detection and many_boxes samples from the error-review package
```

6. Render selected samples back into contact sheets for fast human correction.

## Executed Outputs

Multimodal QC package:

```text
E:\yolo\datasets\station_ppe_20260519_multimodal_qc_v0
```

Generated files:

```text
qc_review_qa300.csv
selected_for_label_fix.csv
sheet_review_summary.csv
summary.json
README.md
images\
labels_pseudo\
boxed_contact_sheets\
source_contact_sheets\
```

Package counts:

```text
QA samples reviewed: 300
Selected for label correction: 200
Selected images: 200
Selected pseudo-label files: 200
Selected contact sheets: 10
Source QA contact sheets copied: 15
```

Selected sample composition:

```text
qa300: 140
error_review240: 60
```

Profile composition:

```text
main_train: 48
mixed_train: 56
hard_case: 16
low_signal: 20
empty_detection: 24
many_boxes: 24
routine_sample: 12
```

## Current Recommendation

Use the 200-image selected queue as the next human correction target, not the full 2564-frame extracted dataset.

The correction priority is:

1. Correct all person and helmet boxes in `main_train` and `mixed_train`.
2. Manually add vest labels where visible.
3. Review `empty_detection` samples for missed small workers.
4. Review `many_boxes` samples for duplicate or incorrect boxes.
5. Keep only a limited number of low-signal frames as hard negatives.

After this correction pass, promote the corrected 200-image package into a reviewed YOLO training dataset and run the first meaningful site-specific training.

## Priority Label Fix V1

To reduce manual work further, the 200 selected samples were compressed into a first priority correction batch:

```text
E:\yolo\datasets\station_ppe_20260519_priority_label_fix_v1
```

Generated files:

```text
priority_label_fix.csv
summary.json
README.md
classes.yaml
images\
labels_pseudo\
boxed_contact_sheets\
```

Batch size:

```text
Total images: 128
Rendered contact sheets: 7
```

Selection composition:

```text
main_train: 48
mixed_train: 48
hard_case: 12
many_boxes: 12
empty_detection: 8
```

Source composition:

```text
qa300: 108
error_review240: 20
```

Pseudo-label totals before manual correction:

```text
person: 558
helmet: 261
vest: 5
```

Interpretation:

```text
person / helmet already have enough pseudo-label signal for first-pass correction.
vest is severely under-detected by pseudo labels and must be manually added where visible.
```

This batch is the recommended first manual correction queue. It is not final training data yet. The goal is to correct the highest-value samples first, then promote the corrected labels into a reviewed YOLO training split.

Practical correction order:

1. Fix `person`, `helmet`, and visible `vest` boxes in all `main_train` samples.
2. Fix the same classes in `mixed_train` samples to add viewpoint and distance variation.
3. Use `hard_case` samples to capture small targets, occlusion, and edge cases.
4. Use `many_boxes` samples to remove duplicate or wrong boxes.
5. Use `empty_detection` samples only where they clarify missed workers or valid hard negatives.

Current technical boundary:

```text
This batch can support a first PPE detector for visible worker / helmet / reflective vest.
It cannot support reliable face recognition because the available high-view construction footage does not provide enough frontal, high-pixel face samples.
```

## Review Workspace

An editable review workspace has been created from the priority queue:

```text
E:\yolo\datasets\station_ppe_20260519_priority_label_fix_v1_review_workspace
```

Workspace contents:

```text
images\
labels_reviewed\
labels_pseudo_original\
boxed_contact_sheets_initial\
labeling_queue.csv
labelimg_file_list.txt
README.md
```

Use `labels_reviewed` for manual correction. `labels_pseudo_original` is retained as the comparison baseline and should not be edited.

The conversion command after manual correction is:

```powershell
python -m data_factory.label_review promote `
  --review-workspace E:\yolo\datasets\station_ppe_20260519_priority_label_fix_v1_review_workspace `
  --output E:\yolo\datasets\station_ppe_20260519_reviewed_yolo_v1 `
  --require-status done
```

This promotion step intentionally requires `manual_status=done`, so unchecked pseudo labels are not accidentally treated as reviewed training data.

## End-To-End Demo Result

The first site-specific PPE loop has now been run end to end on the priority batch:

```text
source videos -> extracted frames -> pseudo labels -> Codex visual review -> reviewed YOLO dataset -> training -> annotated demo -> event CSV
```

Final reviewed training dataset:

```text
E:\yolo\datasets\station_ppe_20260519_codex_reviewed_yolo_v2_3class
```

Final model weight:

```text
E:\yolo\runs\detect\station_ppe_20260519_codex_v2_3class\weights\best.pt
```

Demo output:

```text
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_test
```

The V2 dataset uses three classes:

```text
person
helmet
vest
```

Label counts after Codex auto-review:

```text
person: 558
helmet: 254
vest: 192
```

Split:

```text
train: 96 images
val: 19 images
test: 13 images
```

### Validation Metrics

Validation split:

```text
all:    mAP50 0.470, mAP50-95 0.292
person: mAP50 0.600, mAP50-95 0.376
helmet: mAP50 0.804, mAP50-95 0.498
vest:   mAP50 0.0066, mAP50-95 0.0015
```

Test split:

```text
all:    mAP50 0.465, mAP50-95 0.289
person: mAP50 0.645, mAP50-95 0.427
helmet: mAP50 0.747, mAP50-95 0.438
vest:   mAP50 0.0035, mAP50-95 0.0008
```

Interpretation:

```text
person detection: usable for a first demo, still needs more corrected local data.
helmet detection: usable for a first demo and already has clear signal.
vest detector: not usable as a standalone model head in this run.
```

The vest label improvement raised the number of training labels, but the standalone vest head still failed to generalize. For the current demo, the practical path is therefore:

```text
YOLO model: person + helmet
rule layer: reflective vest color inside the detected person's torso region
event layer: no helmet / no vest / combined suspected violation
```

This is acceptable for a first technical demonstration, but it should not be presented as a mature vest detection model.

### Demo Event Output

The hybrid demo produced:

```text
annotated images: 13
person event rows: 64
```

Event status counts:

```text
ok: 39
no_helmet: 12
no_vest: 6
no_helmet+no_vest: 7
```

Demo files:

```text
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_test\annotated
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_test\ppe_events.csv
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_test\demo_contact_sheet.jpg
```

### Product Boundary

This batch proves that the construction-site PPE pipeline can be connected for medium/high-angle worker scenes:

```text
who/where at frame level: detected worker box and source image
when: source frame and timestamp text in the image
what violation: suspected no helmet and/or suspected no vest
```

It does not prove identity-level face recognition. The available high-angle footage is not suitable for face recognition because the faces are too small, angled downward, and often occluded by helmets or posture.

For the leadership scenario that requires "who, at what time, with what violation", the recommended engineering split is:

```text
near fixed camera, 2.4-3 m installation height: face capture / identity entry point
medium work-zone camera: person + helmet + vest + rule-based violation evidence
high camera: fire/smoke/area anomaly, not identity
backend: link events by time, camera, face checkpoint records, and track fragments
```

The next improvement should be human-corrected labels for vest and close/mid fixed-camera face samples, not more high-angle footage alone.

## Visual Acceptance Follow-Up

Date: 2026-05-20

A multimodal visual acceptance pass was performed on the demo output after the user flagged likely recognition errors.

Result:

```text
Original loose demo: not acceptable for business acceptance
Strict V4 demo: acceptable as technical workflow demo only
Business acceptance: not passed
```

The loose demo produced 64 person event rows, but visual review found:

```text
duplicate person boxes
bags/covers/materials detected as people
helmet false alarms caused by rigid helmet-person matching
unstable no_helmet/no_vest events from low-confidence candidates
```

A stricter post-processing version was generated:

```text
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v4
```

Strict V4 output:

```text
accepted person event rows: 19
rejected person candidates: 45
status counts: ok 18, no_vest 1
```

Inspection artifacts:

```text
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v4\person_event_crop_sheet.jpg
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v4\rejected_candidate_crop_sheet.jpg
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v4\visual_acceptance_20260520.md
```

Interpretation:

```text
Strict filtering improves presentation cleanliness and suppresses many false positives.
It also rejects some real workers, especially partial-body, low-confidence, or crowded cases.
```

Therefore the accurate report wording is:

```text
已打通工地 PPE 识别演示链路，可输出人员、安全帽、反光衣疑似状态；
当前样本和标签质量不足，自动告警准确性尚未达到交付验收标准。
```

Required before business acceptance:

```text
200-400 manually corrected images
human-corrected person / helmet / vest labels
hard negatives for bags, covers, pipes, extinguishers, and materials
near/mid fixed-camera samples
multi-frame confirmation for violation events
```

## Optimization Follow-Up V5

Date: 2026-05-20

The demo post-processing was revised again after visual inspection. Instead of simply suppressing uncertain cases, V5 separates outputs into:

```text
auto demo events
manual review queue
rejected candidates
```

V5 output directory:

```text
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v5
```

V5 summary:

```text
accepted person event rows: 19
auto_demo_ok: 13
needs_review: 6
rejected person candidates: 45
manual review queue rows: 39
```

Review queue composition:

```text
accepted_event: 6
rejected_candidate: 33
```

Review reasons:

```text
helmet_rule_only: 3
medium_person_confidence: 2
suspected_ppe_issue: 1
possible_worker_low_confidence: 18
possible_worker_or_hard_negative: 14
small_worker_check: 1
```

Key files:

```text
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v5\ppe_events.csv
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v5\ppe_review_queue.csv
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v5\review_queue_crop_sheet.jpg
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v5\optimization_notes_20260520.md
```

Interpretation:

```text
V5 is better than V4 because it does not hide uncertain detections.
It creates a concrete label-fix queue for the next training loop.
```

The next useful improvement is to correct the V5 review queue and retrain with those hard cases. Further threshold tuning alone will trade false positives for missed workers and will not solve the core data issue.

## V5 Review Workspace

The V5 queue has been converted into a box-level correction workspace:

```text
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace
```

Workspace contents:

```text
images\
crops\
labels_current\
labels_reviewed\
crop_contact_sheets\
review_queue_workspace.csv
codex_visual_triage_20260520.csv
codex_visual_triage_notes_20260520.md
```

Workspace summary:

```text
review rows: 39
unique images: 9
accepted_event rows: 6
rejected_candidate rows: 33
```

Codex visual triage, junior-QC only:

```text
true_worker_fix_label: 24
hard_negative_not_worker: 11
unclear_skip: 3
ppe_status_fix: 1
```

Interpretation:

```text
Most of the review queue is useful, not noise.
The next correction pass should add/fix true workers and add hard negatives for common false person detections.
```

This triage does not set `manual_status=done`. It is a work accelerator for human label correction, not final ground truth.

## Codex Draft Labels

Date: 2026-05-20

Codex visual triage was applied into a reversible draft label set:

```text
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace\labels_codex_draft
```

This step does not overwrite:

```text
labels_reviewed\
```

Draft application rules:

```text
true_worker_fix_label: add a person box only if no matching person label already exists
hard_negative_not_worker: remove overlapping person boxes from likely false person detections
ppe_status_fix: no label change, keep for human PPE status review
unclear_skip: no label change
```

Draft result:

```text
images: 9
review rows: 39
person_added: 1
person_removed: 10
skipped: 33
```

Draft files:

```text
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace\codex_draft_label_manifest.csv
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace\codex_draft_label_summary.json
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace\codex_draft_label_delta_20260520.md
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace\boxed_current
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace\boxed_codex_draft
```

Interpretation:

```text
The draft pass mainly removed false person labels from hard negatives.
Most true-worker candidates already had matching person labels, so they were skipped instead of duplicated.
```

This draft can be used for an experimental training run only if clearly labeled as Codex-draft data. It should not replace a human-reviewed dataset for acceptance testing.
