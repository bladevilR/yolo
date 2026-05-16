# Data Factory

CPU-friendly tools for turning field videos into a YOLO dataset draft.

Example for the 2026-05-15 station videos on the current workstation:

```bash
python -m data_factory.video_dataset_builder \
  --input M:\yolo\2026-05-15 \
  --output M:\yolo\datasets\station_ppe_20260515_v0 \
  --sample-fps 0.5 \
  --extract-backend ffmpeg \
  --ffmpeg-qscale 3 \
  --dedup-threshold -1
```

The generated labels are intentionally empty. Import the dataset into CVAT,
X-AnyLabeling, or another annotation tool, run pre-labeling if available, then
human-review before training.

Create a 200-image QA review package:

```bash
python -m data_factory.qa_package \
  --dataset M:\yolo\datasets\station_ppe_20260515_v0 \
  --output M:\yolo\datasets\station_ppe_20260515_v0_qa200 \
  --sample-size 200
```

Generate pseudo labels for that QA package without overwriting the empty labels:

```bash
python -m data_factory.prelabel_yolo \
  --model <path-to-current-ppe-teacher-best.pt> \
  --images M:\yolo\datasets\station_ppe_20260515_v0_qa200\images \
  --output-labels M:\yolo\datasets\station_ppe_20260515_v0_qa200\pseudo_labels \
  --conf 0.20 \
  --imgsz 1280 \
  --batch 8 \
  --device cpu
```

Render pseudo-label contact sheets:

```bash
python -m data_factory.render_yolo_labels \
  --images M:\yolo\datasets\station_ppe_20260515_v0_qa200\images \
  --labels M:\yolo\datasets\station_ppe_20260515_v0_qa200\pseudo_labels \
  --output M:\yolo\datasets\station_ppe_20260515_v0_qa200\pseudo_contact_sheets
```

Run pseudo-labeling on the full extracted dataset while preserving
`train`/`val`/`test` subdirectories:

```bash
python -m data_factory.prelabel_yolo \
  --model <path-to-current-ppe-teacher-best.pt> \
  --images M:\yolo\datasets\station_ppe_20260515_v0\images \
  --output-labels M:\yolo\datasets\station_ppe_20260515_v0\pseudo_labels \
  --conf 0.20 \
  --imgsz 1280 \
  --batch 8 \
  --device cpu
```

Create a representative QA package from the full pseudo-label tree:

```bash
python -m data_factory.qa_package \
  --dataset M:\yolo\datasets\station_ppe_20260515_v0 \
  --label-root M:\yolo\datasets\station_ppe_20260515_v0\pseudo_labels \
  --output M:\yolo\datasets\station_ppe_20260515_v0_pseudo_qa300 \
  --sample-size 300

python -m data_factory.render_yolo_labels \
  --images M:\yolo\datasets\station_ppe_20260515_v0_pseudo_qa300\images \
  --labels M:\yolo\datasets\station_ppe_20260515_v0_pseudo_qa300\labels \
  --output M:\yolo\datasets\station_ppe_20260515_v0_pseudo_qa300\pseudo_contact_sheets
```

Existing pseudo labels are drafts only. Stop for human review before promoting
them into the official `labels` tree or training as if they were verified labels.
