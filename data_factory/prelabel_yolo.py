#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate YOLO-format pseudo labels from an existing Ultralytics model."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ultralytics import YOLO


DEFAULT_TARGET_CLASSES = ["person", "head", "helmet", "vest", "no_helmet", "no_vest"]
DEFAULT_WORLD_CLASSES = ["person", "hard hat", "safety helmet", "safety vest", "reflective vest"]


CLASS_ALIASES = {
    "person": "person",
    "people": "person",
    "hardhat": "helmet",
    "hard_hat": "helmet",
    "helmet": "helmet",
    "safety_helmet": "helmet",
    "vest": "vest",
    "safety_vest": "vest",
    "reflective_vest": "vest",
    "no_hardhat": "no_helmet",
    "no_hard_hat": "no_helmet",
    "no_helmet": "no_helmet",
    "no_safety_helmet": "no_helmet",
    "no_vest": "no_vest",
    "no_safety_vest": "no_vest",
    "no_reflective_vest": "no_vest",
}


def normalize_class_name(name: str) -> str:
    normalized = name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def map_model_class_to_target(model_class_name: str, target_classes: Sequence[str]) -> int | None:
    canonical = CLASS_ALIASES.get(normalize_class_name(model_class_name))
    if canonical is None:
        return None
    try:
        return list(target_classes).index(canonical)
    except ValueError:
        return None


def yolo_line(class_id: int, xywhn: Sequence[float]) -> str:
    return f"{class_id} " + " ".join(f"{value:.6f}" for value in xywhn)


def iter_images(images_root: Path) -> list[Path]:
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if images_root.is_file():
        return [images_root]
    return sorted(path for path in images_root.rglob("*") if path.suffix.lower() in extensions)


def target_label_path(image_path: Path, images_root: Path, output_labels: Path) -> Path:
    try:
        relative = image_path.relative_to(images_root)
    except ValueError:
        relative = Path(image_path.name)
    return output_labels / relative.with_suffix(".txt")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prelabel_images(
    model_path: Path,
    images_root: Path,
    output_labels: Path,
    target_classes: Sequence[str],
    model_classes: Sequence[str] | None = None,
    conf: float = 0.2,
    imgsz: int = 1280,
    batch: int = 8,
    device: str = "cpu",
) -> tuple[Counter[str], list[dict[str, Any]]]:
    image_paths = iter_images(images_root)
    output_labels.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(model_path))
    if model_classes:
        if not hasattr(model, "set_classes"):
            raise RuntimeError(f"Model does not support custom class prompts: {model_path}")
        model.set_classes(list(model_classes))
    class_counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []

    for start in range(0, len(image_paths), batch):
        batch_paths = image_paths[start : start + batch]
        results = model.predict(
            [str(path) for path in batch_paths],
            imgsz=imgsz,
            conf=conf,
            device=device,
            verbose=False,
        )
        for image_path, result in zip(batch_paths, results):
            label_lines: list[str] = []
            detections = 0
            mapped_detections = 0
            if result.boxes is not None:
                for box in result.boxes:
                    detections += 1
                    model_class_id = int(box.cls.item())
                    model_class_name = model.names[model_class_id]
                    target_id = map_model_class_to_target(model_class_name, target_classes)
                    if target_id is None:
                        continue
                    xywhn = box.xywhn.squeeze().tolist()
                    label_lines.append(yolo_line(target_id, xywhn))
                    class_counts[target_classes[target_id]] += 1
                    mapped_detections += 1

            label_path = target_label_path(image_path, images_root, output_labels)
            label_path.parent.mkdir(parents=True, exist_ok=True)
            label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")
            rows.append(
                {
                    "image_path": str(image_path),
                    "label_path": str(label_path),
                    "detections": detections,
                    "mapped_detections": mapped_detections,
                }
            )

    write_csv(
        output_labels.parent / "pseudo_label_summary.csv",
        rows,
        ["image_path", "label_path", "detections", "mapped_detections"],
    )
    (output_labels.parent / "pseudo_label_class_counts.json").write_text(
        json.dumps(dict(class_counts), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return class_counts, rows


def parse_classes(raw: str) -> list[str]:
    classes = [item.strip() for item in raw.split(",") if item.strip()]
    if not classes:
        raise ValueError("at least one target class is required")
    return classes


def parse_optional_classes(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    return parse_classes(raw)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--output-labels", required=True, type=Path)
    parser.add_argument("--classes", default=",".join(DEFAULT_TARGET_CLASSES))
    parser.add_argument(
        "--model-classes",
        default=None,
        help=(
            "Optional comma-separated prompt classes for YOLO-World style models. "
            f"Example: {','.join(DEFAULT_WORLD_CLASSES)}"
        ),
    )
    parser.add_argument("--conf", type=float, default=0.2)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    counts, rows = prelabel_images(
        model_path=args.model,
        images_root=args.images,
        output_labels=args.output_labels,
        target_classes=parse_classes(args.classes),
        model_classes=parse_optional_classes(args.model_classes),
        conf=args.conf,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
    )
    print(f"Images: {len(rows)}")
    print(f"Mapped detections: {sum(counts.values())}")
    print(json.dumps(dict(counts), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
