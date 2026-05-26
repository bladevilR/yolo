## Why

The current station PPE pipeline proves the end-to-end technical path, but the latest model was trained from Codex auto-reviewed labels rather than human gold labels, and its vest detector does not generalize. To move from demo to a real implementation target, retraining must start from verified labels, hard negatives, and acceptance-oriented evaluation instead of more threshold tuning.

## What Changes

- Define a human-reviewed retraining dataset workflow for `person`, `helmet`, and visible `vest` labels.
- Promote the V5 review queue into a confirmed correction set before it can affect training.
- Add hard negatives for bags, covers, pipes, extinguishers, materials, and other false-person sources.
- Separate normal validation, hard-negative stress testing, and demo acceptance runs.
- Require reproducible training outputs with dataset provenance, class counts, split composition, metrics, confusion matrices, and demo event summaries.
- Keep high-angle face recognition and identity-level tracking out of this retraining change; those require near/mid fixed-camera identity samples.

## Capabilities

### New Capabilities

- `station-ppe-training-dataset`: Defines the human-reviewed dataset, label quality gates, hard-negative handling, split policy, and promotion rules required before retraining.
- `station-ppe-retraining-evaluation`: Defines reproducible model retraining, validation, stress-test evaluation, demo event verification, and acceptance reporting for the station PPE detector.

### Modified Capabilities

- None.

## Impact

- Affects `data_factory` dataset preparation, label-review, triage, and promotion workflows.
- Affects training scripts and run output naming under `outputs/` and `runs/detect/`.
- Affects station PPE documentation under `docs/`, especially the distinction between demo readiness and business acceptance.
- Does not require new model dependencies beyond the existing Ultralytics/OpenCV/Python workflow unless future hardware or identity work is separately scoped.
