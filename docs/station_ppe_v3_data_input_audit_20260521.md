# Station PPE V3 Data Input Audit

- Generated date: 2026-05-21

## Priority Workspace

- Rows: 128
- Unique images: 128
- Duplicate image rows: 0
- Manual status counts: `{'codex_reviewed': 128}`
- Profile counts: `{'main_train': 48, 'mixed_train': 48, 'hard_case': 12, 'many_boxes': 12, 'empty_detection': 8}`
- Reviewed label path status: `{'nonempty': 114, 'empty': 14}`
- Original pseudo label path status: `{'nonempty': 114, 'empty': 14}`
- Rows carrying Codex auto-review notes: 128

## V5 Review Workspace

- Rows: 39
- Unique images: 9
- Duplicate image rows: 30
- Manual status counts: `{'todo': 39}`
- Queue source counts: `{'accepted_event': 6, 'rejected_candidate': 33}`
- Current label path status: `{'nonempty': 33, 'empty': 6}`
- Reviewed label path status: `{'nonempty': 33, 'empty': 6}`
- Codex suggested decision counts: `{'ppe_status_fix': 1, 'true_worker_fix_label': 24, 'hard_negative_not_worker': 11, 'unclear_skip': 3}`
- Codex draft manifest rows: 9

## Gate Decision

- These inputs are review queues, not a completed v3 training dataset.
- `codex_reviewed` and `todo` are blocked until a human reviewer marks corrected full-image labels as `done`.
- V5 event rows are useful error evidence, but duplicate event rows must be collapsed at image level before dataset promotion.
