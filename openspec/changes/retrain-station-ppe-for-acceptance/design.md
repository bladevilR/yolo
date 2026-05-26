## Context

The current station PPE work has an end-to-end demo pipeline:

```text
video frames -> pseudo labels -> Codex visual review -> YOLO training -> strict demo -> review queue
```

The latest trained detector is `station_ppe_20260519_codex_v2_3class`, trained on `station_ppe_20260519_codex_reviewed_yolo_v2_3class`. That dataset has useful structure, but it is explicitly Codex auto-reviewed rather than human gold-label data. The V2 model is acceptable as a technical demo baseline: person and helmet detection have signal, while vest detection failed as a standalone model head and is currently handled by a color-rule fallback.

The V5 strict demo created a valuable review queue with 39 rows across 9 images. This queue should not be treated as a complete retraining set. It is an error-focused patch set that must be folded back into a larger human-reviewed dataset.

## Goals / Non-Goals

**Goals:**

- Produce a retraining workflow that can move the project from demo baseline toward acceptance-grade PPE detection.
- Require human-reviewed `person`, `helmet`, and visible `vest` labels before training data is called reviewed.
- Add hard negatives for the false-person sources already observed: bags, covers, materials, pipes, extinguishers, and construction clutter.
- Split evaluation into normal validation, hard-negative stress testing, and strict demo/event verification.
- Generate reproducible model, dataset, metric, and report artifacts for every retraining run.

**Non-Goals:**

- Do not train `no_helmet` or `no_vest` as object classes in this change; derive them as event states after detection.
- Do not claim identity-level face recognition from the high-angle camera footage.
- Do not treat Codex draft labels as ground truth without human review.
- Do not optimize only confidence thresholds as a substitute for label correction.

## Decisions

### Decision 1: Train visible-object classes only

The detector will train `person`, `helmet`, and visible `vest`. Violation states will be computed downstream:

```text
person without matching helmet -> suspected no helmet
person without visible vest evidence -> suspected no vest
multi-frame confirmation -> event confidence
```

Alternative considered: train `no_helmet` and `no_vest` classes directly. This was rejected because the current data does not contain reliable absence labels and would teach the model inconsistent semantics.

### Decision 2: Human-reviewed data gates before retraining

The next acceptance-oriented training dataset should be created from the 128-image priority batch plus V5 corrections and additional selected samples until it reaches a 200-400 image human-reviewed set. A smaller 128+V5 run may be useful as an experiment, but it must be named as experimental and not used for acceptance claims.

Alternative considered: use `labels_codex_draft` directly for v3 training. This is faster, but it preserves Codex uncertainty and would repeat the same provenance problem as V2.

### Decision 3: Separate normal validation from stress testing

The V2 split placed `main_train` and `mixed_train` in train, `hard_case`/`many_boxes` in validation, and `empty_detection`/`many_boxes` in test. That is useful as a stress test but not as a normal generalization estimate. The new workflow will create:

```text
train: stratified by source video, camera view, profile, and scene
val: same distribution as train, human reviewed
test: held-out normal scenes, human reviewed
stress: hard negatives, many_boxes, empty_detection, edge/tiny/occluded cases
demo: selected clips/images for event-level acceptance review
```

Alternative considered: keep the V2 split. This would make metrics hard to interpret and could overstate or understate progress depending on which profile dominates a split.

### Decision 4: Evaluate event behavior, not only box mAP

Detector metrics are necessary but not enough. The retraining result must also report event-level behavior from the strict demo pipeline:

```text
false person events per image or clip
duplicate person event rate
suspected no_helmet precision/recall after manual review
suspected no_vest precision/recall after manual review
manual review queue volume
```

Alternative considered: report mAP only. This was rejected because the business failure modes are duplicate people, false people, and wrong PPE event states.

### Decision 5: Keep identity as a separate data program

The high-angle footage can support area-level PPE detection but not stable identity. If the final business target requires "who, when, what violation", retraining must be paired with new near/mid fixed-camera identity samples. This proposal keeps the PPE detector retraining focused and records identity as a dependency for a later change.

## Risks / Trade-offs

- Insufficient vest examples -> vest AP remains low. Mitigation: require human-visible vest labels across varied colors, distances, occlusions, and lighting before judging the vest head.
- Small helmets at 640 image size -> helmet recall may plateau. Mitigation: run a controlled image-size experiment, likely 640 vs 960, and compare latency separately from accuracy.
- Hard negatives overwhelm positives -> person recall falls. Mitigation: bound hard-negative ratio and keep a separate stress set for reporting.
- Codex draft labels leak into gold data -> metrics become untrustworthy. Mitigation: require `manual_status=done` and provenance fields before promotion.
- Better detector still creates noisy violations -> event layer remains unstable. Mitigation: use strict post-processing and multi-frame confirmation for video event claims.
- Dataset remains too camera-specific -> model overfits one high-angle scene. Mitigation: stratify by source video/time/profile and add near/mid camera samples when available.

## Migration Plan

1. Freeze the V2 model, dataset, and reports as the demo baseline.
2. Human-review the priority batch and V5 queue into a new `v3_human_reviewed` workspace.
3. Promote only confirmed rows into a new YOLO dataset with explicit normal and stress splits.
4. Train controlled experiments from the same dataset and write run manifests.
5. Evaluate detector metrics, stress metrics, and strict demo event metrics.
6. Select a candidate model only if it improves both detection quality and event behavior.
7. Archive rejected runs with their failure reason so later tuning does not repeat them.

Rollback is simple because training outputs are additive: keep V2 as the current demo baseline until a v3 candidate passes the agreed gates.

## Open Questions

- What is the minimum acceptable business target for the next milestone: technical demo improvement, pilot-site trial, or formal acceptance?
- Is edge deployment on RK3588 a hard constraint for this retraining cycle, or can accuracy experiments use a larger model first?
- How many new near/mid camera samples can be collected for identity and clearer PPE views?
- Who will perform final human label approval, and what annotation tool/status value will mark gold labels?
