# Station PPE V2 Baseline Freeze

- Generated date: 2026-05-21
- Model path: `E:\yolo\runs\detect\station_ppe_20260519_codex_v2_3class\weights\best.pt`
- Dataset path: `E:\yolo\datasets\station_ppe_20260519_codex_reviewed_yolo_v2_3class`
- Training results CSV: `E:\yolo\runs\detect\station_ppe_20260519_codex_v2_3class\results.csv`
- Strict V5 demo output: `E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v5`

## Dataset Counts

- Image counts: `{'train': 96, 'val': 19, 'test': 13}`
- Label file counts: `{'train': 96, 'val': 19, 'test': 13}`
- Empty label files: `{'train': 0, 'val': 6, 'test': 8}`
- Class counts: `{'person': 558, 'helmet': 254, 'vest': 192}`
- Invalid label rows: 0
- Missing label files: 0
- Orphan label files: 0

## Manifest Composition

- Rows: 128
- Split counts: `{'train': 96, 'val': 19, 'test': 13}`
- Profile counts: `{'main_train': 48, 'mixed_train': 48, 'hard_case': 12, 'many_boxes': 12, 'empty_detection': 8}`
- Manual status counts: `{'codex_reviewed': 128}`
- Provenance warning: manifest paths still reference v2_6class in some rows

## Training Final Aggregate

- Final epoch: 25
- Precision(B): 0.84808
- Recall(B): 0.45747
- mAP50(B): 0.47552
- mAP50-95(B): 0.2822

## Validation And Test Metrics

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


## Strict V5 Demo Counts

- Event decision counts: `{'needs_review': 6, 'auto_demo_ok': 13}`
- Event status counts: `{'no_vest': 1, 'ok': 18}`
- Review queue source counts: `{'accepted_event': 6, 'rejected_candidate': 33}`
- Rejected candidate rows: 45

## Known Failure Modes

- V2 was trained from Codex auto-reviewed labels, not human gold labels.
- Vest detector did not generalize; vest event handling relies on downstream color/rule fallback.
- V2 validation/test splits are stress-heavy rather than normal business acceptance splits.
- The current demo can show the workflow, but it is not business-acceptance-ready.
