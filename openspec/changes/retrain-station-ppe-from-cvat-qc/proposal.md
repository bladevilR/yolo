## Why

The station PPE project now has a more valuable data state than the previous retraining plan assumed: the CVAT task contains human edits across 121 images, and supervision-backed QC has produced a non-mutating snapshot of the current 200-image task. The next training plan should protect that manual work, close the remaining QC issues, and only train from a frozen, provenance-recorded dataset.

## What Changes

- Freeze the current CVAT task state before any further automation, including a task backup, YOLO export, and immutable dataset manifest.
- Use supervision QC outputs to drive a short human-review pass over duplicate boxes, orphan PPE boxes, empty labels, and high-risk images.
- Define a promotion gate so only reviewed CVAT annotations can enter the next training dataset.
- Build the next dataset from the current 200-image CVAT task snapshot, with explicit train/val/test/stress/demo splits.
- Run controlled retraining experiments against the frozen dataset rather than continuing threshold tuning.
- Evaluate candidate models with both detection metrics and strict demo/event behavior.
- Produce a training decision report that states whether the result is demo-ready, pilot-ready, acceptance-ready, or rejected.

## Capabilities

### New Capabilities

- `station-ppe-cvat-reviewed-dataset`: Defines how current CVAT annotations are snapshotted, QC-reviewed, promoted, split, and documented before training.
- `station-ppe-controlled-retraining`: Defines the controlled training experiments, model comparison, event-level validation, and candidate decision report for the next station PPE model.

### Modified Capabilities

- None.

## Impact

- Affects dataset preparation scripts under `data_factory/` and new or existing training scripts under `scripts/`.
- Uses the already introduced supervision QC utility as a required pre-training gate.
- Uses CVAT only as a source of reviewed annotations; this change must not overwrite or mutate the current CVAT task unless a separate explicit import/apply command is introduced.
- Produces additive dataset, training, evaluation, and report artifacts under `datasets/`, `runs/detect/`, `outputs/`, and `docs/`.
- Supersedes the practical execution path of the earlier `retrain-station-ppe-for-acceptance` plan, because that plan predated the current CVAT 121-image manual review state and supervision QC outputs.
