# Station PPE Data Factory Handoff

Date: 2026-05-16
Branch: `codex/station-ppe-data-factory-20260515`

## Goal

Turn the copied field videos from `F:\yolo\2026-05-15` into a usable PPE dataset workflow on the current laptop, without attempting heavy model training on this machine.

The laptop is used for CPU-friendly work:

- Sparse frame extraction
- YOLO dataset scaffolding
- QA sampling
- Pseudo-label generation with an existing PPE model
- Contact-sheet rendering for fast human review
- High-risk pseudo-label error review

Training and model comparison should move to a stronger GPU machine, such as the RTX 2070S computer.

## Original Plan

1. Use this machine as the data-preparation workstation.
2. Extract frames from the six station/construction videos at `0.5 FPS`.
3. Build a YOLO-format dataset with empty labels first.
4. Use existing PPE detector weights only as a pseudo-label teacher.
5. Keep pseudo labels separate from official labels.
6. Generate QA packages and contact sheets before promoting any labels to training data.
7. Treat `no_helmet` and `no_vest` as suspicious classes, because they are more error-prone than visible-object classes.
8. Do not train from pseudo labels until a human review pass fixes obvious false positives, missed small workers, and wrong violation boxes.

## Data Outputs

These generated outputs are intentionally outside git and are ignored by `.gitignore`.

### Full Extracted Dataset

Path:

```text
F:\yolo\datasets\station_ppe_20260515_v0
```

Contents:

- Images: `4422`
- Empty YOLO labels: `4422`
- Split counts:
  - `train`: `3542`
  - `val`: `440`
  - `test`: `440`
- Classes:
  - `person`
  - `head`
  - `helmet`
  - `vest`
  - `no_helmet`
  - `no_vest`

Important files:

- `data.yaml`
- `metadata/videos.csv`
- `metadata/frames.csv`
- `metadata/summary.json`

### QA200 Package

Path:

```text
F:\yolo\datasets\station_ppe_20260515_v0_qa200
```

Purpose:

- Quick visual review of representative extracted frames.
- First pseudo-label test on 200 images.

Contents:

- Images: `200`
- Labels: `200`
- Contact sheets: `10`
- Pseudo labels: `200`
- Boxed pseudo-label contact sheets: `10`

QA200 pseudo-label stats:

```text
helmet: 340
vest: 316
person: 362
no_vest: 6
no_helmet: 0
```

### Full Pseudo Labels

Path:

```text
F:\yolo\datasets\station_ppe_20260515_v0\pseudo_labels
```

Model used:

```text
E:\yolo\PPE\Construction-Site-Safety-Gears-Detection-Model-Yolov8-main\Construction-Site-Safety-Gears-Detection-Model-Yolov8-main\models\best.pt
```

Full pseudo-label stats:

```text
images: 4422
labels: 4422
missing_labels: 0
nonempty_labels: 4171
boxes: 25193

person: 9427
helmet: 8205
vest: 7453
no_vest: 100
no_helmet: 8
```

Important files:

- `pseudo_label_summary.csv`
- `pseudo_label_class_counts.json`
- `pseudo_label_full.stdout.log`
- `pseudo_label_full.stderr.log`

### Pseudo QA300 Package

Path:

```text
F:\yolo\datasets\station_ppe_20260515_v0_pseudo_qa300
```

Purpose:

- Representative review package sampled from the full pseudo-label tree.

Contents:

- Images: `300`
- Labels: `300`
- Contact sheets: `15`
- Boxed pseudo-label contact sheets: `15`

### Error Review 240 Package

Path:

```text
F:\yolo\datasets\station_ppe_20260515_v0_error_review240
```

Purpose:

- Targeted review set for likely pseudo-label mistakes.
- Built after noticing visible wrong boxes in pseudo-label previews.

Contents:

- Images: `240`
- Labels: `240`
- Boxed contact sheets: `12`

Sampling groups:

```text
empty_detection: 48
many_boxes: 60
routine_sample: 72
violation_class: 60
```

Review priority:

1. Check `violation_class` samples first.
2. Treat `no_helmet` and `no_vest` as suspicious until manually confirmed.
3. Check `many_boxes` samples for false positives on steel, shadows, pipes, and background structures.
4. Check `empty_detection` samples for missed small workers.

## Code Added

### `data_factory/video_dataset_builder.py`

Builds a YOLO dataset draft from video files.

Key behavior:

- Supports OpenCV and FFmpeg extraction backends.
- Uses `imageio-ffmpeg` for portable FFmpeg on Windows.
- Creates `images/train`, `images/val`, `images/test`.
- Creates matching empty label files.
- Writes `data.yaml`, `videos.csv`, `frames.csv`, and `summary.json`.
- Can keep all frames or apply conservative duplicate/quality filtering.

### `data_factory/qa_package.py`

Creates representative image samples and contact sheets.

Key behavior:

- Samples evenly across source videos.
- Supports copying labels from either official labels or a parallel pseudo-label tree.
- Writes `sample.csv` and a review README.

### `data_factory/prelabel_yolo.py`

Generates YOLO-format pseudo labels from an existing Ultralytics detector.

Key behavior:

- Maps model class names into the target PPE schema.
- Preserves `train`/`val`/`test` subdirectories.
- Keeps pseudo labels separate from official labels.
- Writes class-count and per-image summary files.

### `data_factory/render_yolo_labels.py`

Renders YOLO labels onto images and creates boxed contact sheets.

Key behavior:

- Draws class-colored boxes for quick visual review.
- Supports flat QA folders.

### `data_factory/error_review.py`

Creates a high-risk pseudo-label review package.

Key behavior:

- Flags empty detections, violation-class detections, many-box images, and routine samples.
- Copies images and pseudo labels into a review set.
- Writes `review_samples.csv` and a focused review README.

### `data_factory/README.md`

Documents the commands used for:

- Full dataset extraction
- QA package creation
- QA pseudo-labeling
- Full pseudo-labeling
- Full pseudo-label QA rendering

## Tests Added

```text
tests/test_video_dataset_builder.py
tests/test_qa_package.py
tests/test_prelabel_yolo.py
tests/test_render_yolo_labels.py
tests/test_error_review.py
```

Coverage:

- Frame-step calculation
- YOLO dataset directory creation
- FFmpeg command construction
- Even QA sampling
- Pseudo-label class mapping
- Label path preservation for `train`/`val`/`test`
- YOLO label parsing/rendering helpers
- Error-review reason classification

## Dependency Added

```text
imageio-ffmpeg>=0.6.0
```

Reason:

- System `ffmpeg` was not installed.
- OpenCV HEVC random/sparse extraction was too slow on this laptop.
- `imageio-ffmpeg` provides a local FFmpeg binary that handled the field videos much faster.

## Commands Used

Extract the full dataset:

```powershell
python -m data_factory.video_dataset_builder --input "F:\yolo\2026-05-15" --output "F:\yolo\datasets\station_ppe_20260515_v0" --sample-fps 0.5 --extract-backend ffmpeg --ffmpeg-qscale 3 --dedup-threshold -1
```

Create QA200:

```powershell
python -m data_factory.qa_package --dataset "F:\yolo\datasets\station_ppe_20260515_v0" --output "F:\yolo\datasets\station_ppe_20260515_v0_qa200" --sample-size 200 --columns 5 --rows 4
```

Pseudo-label QA200:

```powershell
python -m data_factory.prelabel_yolo --model "E:\yolo\PPE\Construction-Site-Safety-Gears-Detection-Model-Yolov8-main\Construction-Site-Safety-Gears-Detection-Model-Yolov8-main\models\best.pt" --images "F:\yolo\datasets\station_ppe_20260515_v0_qa200\images" --output-labels "F:\yolo\datasets\station_ppe_20260515_v0_qa200\pseudo_labels" --conf 0.20 --imgsz 1280 --batch 8 --device cpu
```

Pseudo-label the full dataset:

```powershell
python -m data_factory.prelabel_yolo --model "E:\yolo\PPE\Construction-Site-Safety-Gears-Detection-Model-Yolov8-main\Construction-Site-Safety-Gears-Detection-Model-Yolov8-main\models\best.pt" --images "F:\yolo\datasets\station_ppe_20260515_v0\images" --output-labels "F:\yolo\datasets\station_ppe_20260515_v0\pseudo_labels" --conf 0.20 --imgsz 1280 --batch 8 --device cpu
```

Create high-risk error review:

```powershell
python -m data_factory.error_review --dataset "F:\yolo\datasets\station_ppe_20260515_v0" --label-root "F:\yolo\datasets\station_ppe_20260515_v0\pseudo_labels" --output "F:\yolo\datasets\station_ppe_20260515_v0_error_review240" --sample-size 240

python -m data_factory.render_yolo_labels --images "F:\yolo\datasets\station_ppe_20260515_v0_error_review240\images" --labels "F:\yolo\datasets\station_ppe_20260515_v0_error_review240\labels" --output "F:\yolo\datasets\station_ppe_20260515_v0_error_review240\boxed_contact_sheets" --columns 5 --rows 4
```

## Validation

Latest verification:

```text
python -m unittest discover -s tests -p "test*.py"
Ran 20 tests in 0.013s
OK
```

Dataset integrity checks performed:

```text
images 4422
labels 4422
missing_labels 0
missing_images 0
nonempty_labels 4171
boxes 25193
```

Error review package check:

```text
images: 240
labels: 240
boxed_contact_sheets: 12
```

## Current Assessment

The generated pseudo labels are useful as annotation drafts, but they are noisy.

Observed issues:

- Some `no_vest` and `no_helmet` detections are wrong.
- Some small/far workers are missed.
- Some detections attach to background structures, pipes, shadows, or materials.
- High-angle views make PPE boxes small and sensitive to image size.

Do not train directly on `pseudo_labels`.

Recommended next step:

1. Review `F:\yolo\datasets\station_ppe_20260515_v0_error_review240\boxed_contact_sheets`.
2. Correct labels in CVAT or X-AnyLabeling.
3. Promote only reviewed labels into the official `labels` tree.
4. Train visible classes first: `person`, `head`, `helmet`, `vest`.
5. Infer `no_helmet` and `no_vest` primarily through rules, not raw detector classes.

## Product/Model Plan Going Forward

Near term:

- Use this repo's data-factory workflow to prepare site-specific datasets.
- Use existing PPE detector weights only for pre-labeling.
- Run human QA before training.
- Train first production candidate on a stronger GPU machine.

Model direction:

- Short-term speed: Ultralytics YOLO workflow.
- Productization risk control: evaluate RF-DETR / RT-DETR / OpenMMLab alternatives or handle Ultralytics commercial licensing.
- Edge deployment: validate YOLO/RKNN first for RK3588; keep NVIDIA/TensorRT for the first stable multi-camera delivery.

Deployment direction:

- 30-camera RK3588 coverage should be treated as sparse inspection, roughly `0.5-1 FPS` per stream, not continuous high-FPS tracking.
- PPE violations should use multi-frame rules and cooldowns.
- First version should favor visible-object detection plus rules over direct violation-class training.
