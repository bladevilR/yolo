# Station PPE V3 Class Map And Annotation Rules

- Generated date: 2026-05-21

## Detector Classes

```yaml
0: person
1: helmet
2: vest
```

- `person`: visible worker body extent. Use one box per real worker; remove boxes on bags, covers, pipes, extinguishers, materials, and clutter.
- `helmet`: visible helmet shell on a worker. Do not guess hidden helmets.
- `vest`: visible safety vest or high-visibility torso garment. Box only the visible vest area, not the full torso unless the full torso is visibly vest.
- `no_helmet` and `no_vest`: event-layer states only. They are derived after matching PPE evidence to a person and must not appear as detector classes.

## Annotation Rules

- Visible vest boxes: annotate orange, yellow, reflective, or other clearly visible safety vest regions; skip ambiguous reflections or ordinary clothing.
- Helmet boxes: annotate visible helmets even when small, but skip if the head/helmet is too blurred to verify.
- Partial workers: annotate visible body parts as `person` when the worker is clearly present; tag edge/occluded cases for stress evaluation.
- Tiny or edge workers: include only when a human can consistently place a box; otherwise mark unclear and keep out of normal validation.
- Hard negatives: include reviewed images where false-person sources are present and false person boxes were removed.
- Unclear samples: keep in the manifest with notes; do not use for normal metrics unless a reviewer marks them complete and assigns the right profile.
- Skipped samples: record why they were skipped so they do not silently enter v3 training.
