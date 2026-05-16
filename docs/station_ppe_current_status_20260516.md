# Station PPE Current Status

Date: 2026-05-16

## Current Data Location

The active local data root is now:

```text
M:\yolo
```

Active station PPE dataset:

```text
M:\yolo\datasets\station_ppe_20260515_v0
```

Primary training config:

```text
E:\yolo\data_station_ppe_20260515.yaml
```

## Completed Mechanical Steps

- Field videos are present at `M:\yolo\2026-05-15`.
- Extracted YOLO dataset is present at `M:\yolo\datasets\station_ppe_20260515_v0`.
- Existing pseudo labels are present at `M:\yolo\datasets\station_ppe_20260515_v0\pseudo_labels`.
- QA and error-review packages are present under `M:\yolo\datasets`.
- Generated dataset metadata and review CSV paths have been migrated from `F:\yolo` to `M:\yolo`.

## Review Stop Gates

No human label review has been completed yet.

Stop before any of the following actions and get user confirmation:

1. Treating `station_ppe_20260515_v0_qa200` as reviewed.
2. Treating `station_ppe_20260515_v0_pseudo_qa300` as reviewed.
3. Treating `station_ppe_20260515_v0_error_review240` as reviewed.
4. Promoting any `pseudo_labels` file into the official `labels` tree.
5. Training a model on pseudo labels as if they were verified labels.
6. Using `no_helmet` or `no_vest` as trusted training classes without explicit user review.

## Immediate Next Human Review Target

Start with:

```text
M:\yolo\datasets\station_ppe_20260515_v0_error_review240\boxed_contact_sheets
```

This package contains 240 high-risk pseudo-label samples across:

```text
empty_detection: 48
many_boxes: 60
routine_sample: 72
violation_class: 60
```

Priority order:

1. `violation_class`
2. `many_boxes`
3. `empty_detection`
4. `routine_sample`

## Important Constraint

The previous teacher model path recorded in the handoff was:

```text
E:\yolo\PPE\Construction-Site-Safety-Gears-Detection-Model-Yolov8-main\Construction-Site-Safety-Gears-Detection-Model-Yolov8-main\models\best.pt
```

That file is not present in the current `E:\yolo` checkout. Existing pseudo labels can still be reviewed, but rerunning pseudo-label generation requires choosing a current teacher model path first.

## Local Verification Notes

Dataset counts after the M-drive path migration:

```text
images: 4422
labels: 4422
pseudo_labels: 4422
error_review240 boxed contact sheets: 12
```

The local `python` command points to the Microsoft Store alias and is not usable.
The existing `M:\yolo\.venv_mm` virtual environment points to a missing
`D:\python\python.exe`. The Python launcher can run Python 3.13, but the full
test suite currently lacks installed dependencies:

```text
missing: ultralytics, cv2
```

Do not treat the current machine as training-ready until a clean Python
environment is created or repaired.
