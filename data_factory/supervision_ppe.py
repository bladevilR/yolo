#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Supervision-backed QA helpers for station PPE YOLO labels."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import supervision as sv
from PIL import Image, ImageDraw, ImageOps


DEFAULT_CLASSES = ["person", "helmet", "vest"]
CLASS_COLORS = {
    "person": "#3072ff",
    "helmet": "#ffd200",
    "vest": "#28be5a",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def color_palette(class_names: Sequence[str] = DEFAULT_CLASSES) -> sv.ColorPalette:
    colors = [CLASS_COLORS.get(class_name, "#ffffff") for class_name in class_names]
    return sv.ColorPalette.from_hex(colors)


def empty_detections() -> sv.Detections:
    return sv.Detections(
        xyxy=np.empty((0, 4), dtype=np.float32),
        class_id=np.empty((0,), dtype=int),
        data={"class_name": []},
    )


def yolo_to_xyxy(box: Sequence[float], image_size: tuple[int, int]) -> list[float]:
    image_width, image_height = image_size
    x_center, y_center, box_width, box_height = box
    x1 = (x_center - box_width / 2) * image_width
    y1 = (y_center - box_height / 2) * image_height
    x2 = (x_center + box_width / 2) * image_width
    y2 = (y_center + box_height / 2) * image_height
    return [
        max(0.0, min(float(image_width), x1)),
        max(0.0, min(float(image_height), y1)),
        max(0.0, min(float(image_width), x2)),
        max(0.0, min(float(image_height), y2)),
    ]


def load_yolo_detections(
    label_path: Path,
    image_size: tuple[int, int],
    class_names: Sequence[str] = DEFAULT_CLASSES,
) -> tuple[sv.Detections, list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    if not label_path.exists():
        issues.append({"issue": "missing_label_file", "label_path": str(label_path)})
        return empty_detections(), issues

    xyxy: list[list[float]] = []
    class_ids: list[int] = []
    class_name_values: list[str] = []

    for row_index, raw_line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        issue_base = {"label_path": str(label_path), "row": row_index, "line": raw_line}
        if len(parts) != 5:
            issues.append({**issue_base, "issue": "malformed_row"})
            continue
        try:
            class_id = int(parts[0])
            x_center, y_center, box_width, box_height = (float(value) for value in parts[1:])
        except ValueError:
            issues.append({**issue_base, "issue": "malformed_row"})
            continue
        if class_id < 0 or class_id >= len(class_names):
            issues.append({**issue_base, "issue": "invalid_class", "class_id": class_id})
            continue
        if box_width <= 0 or box_height <= 0:
            issues.append({**issue_base, "issue": "non_positive_box", "class_id": class_id})
            continue
        xyxy.append(yolo_to_xyxy((x_center, y_center, box_width, box_height), image_size))
        class_ids.append(class_id)
        class_name_values.append(class_names[class_id])

    if not xyxy:
        return empty_detections(), issues

    detections = sv.Detections(
        xyxy=np.array(xyxy, dtype=np.float32),
        class_id=np.array(class_ids, dtype=int),
        data={"class_name": class_name_values},
    )
    return detections, issues


def list_images(images_dir: Path) -> list[Path]:
    return sorted(path for path in images_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def detection_iou(left: Sequence[float], right: Sequence[float]) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    ix1 = max(lx1, rx1)
    iy1 = max(ly1, ry1)
    ix2 = min(lx2, rx2)
    iy2 = min(ly2, ry2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    intersection = iw * ih
    left_area = max(0.0, lx2 - lx1) * max(0.0, ly2 - ly1)
    right_area = max(0.0, rx2 - rx1) * max(0.0, ry2 - ry1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def find_duplicate_issues(
    detections: sv.Detections,
    image_name: str,
    label_name: str,
    iou_threshold: float,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if detections.class_id is None:
        return issues
    kept_by_class: dict[int, list[Sequence[float]]] = {}
    for index, (box, class_id) in enumerate(zip(detections.xyxy, detections.class_id), start=1):
        class_id = int(class_id)
        kept = kept_by_class.setdefault(class_id, [])
        if any(detection_iou(box, existing) >= iou_threshold for existing in kept):
            issues.append(
                {
                    "issue": "duplicate_box",
                    "image_name": image_name,
                    "label_name": label_name,
                    "class_id": class_id,
                    "detection_index": index,
                }
            )
        else:
            kept.append(box)
    return issues


def helmet_associated_with_person(helmet: Sequence[float], person: Sequence[float]) -> bool:
    hx1, hy1, hx2, hy2 = helmet
    px1, py1, px2, py2 = person
    person_width = max(1.0, px2 - px1)
    person_height = max(1.0, py2 - py1)
    center_x = (hx1 + hx2) / 2
    center_y = (hy1 + hy2) / 2
    return (
        px1 - person_width * 0.20 <= center_x <= px2 + person_width * 0.20
        and py1 - person_height * 0.25 <= center_y <= py1 + person_height * 0.45
    )


def find_orphan_ppe_issues(
    detections: sv.Detections,
    image_name: str,
    label_name: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if detections.class_id is None:
        return issues

    persons = [box for box, class_id in zip(detections.xyxy, detections.class_id) if int(class_id) == 0]
    for index, (box, class_id) in enumerate(zip(detections.xyxy, detections.class_id), start=1):
        class_id = int(class_id)
        if class_id not in {1, 2}:
            continue
        associated = False
        if class_id == 1:
            associated = any(helmet_associated_with_person(box, person) for person in persons)
        elif class_id == 2:
            associated = any(detection_iou(box, person) > 0.03 for person in persons)
        if not associated:
            issues.append(
                {
                    "issue": "orphan_ppe_box",
                    "image_name": image_name,
                    "label_name": label_name,
                    "class_id": class_id,
                    "detection_index": index,
                }
            )
    return issues


def summarize_yolo_directory(
    images_dir: Path,
    labels_dir: Path,
    class_names: Sequence[str] = DEFAULT_CLASSES,
    duplicate_iou_threshold: float = 0.90,
) -> dict[str, Any]:
    image_paths = list_images(images_dir)
    class_counts = Counter({class_name: 0 for class_name in class_names})
    issues: list[dict[str, Any]] = []
    per_image: list[dict[str, Any]] = []
    label_file_count = 0
    empty_label_files = 0

    for image_path in image_paths:
        label_path = labels_dir / f"{image_path.stem}.txt"
        if label_path.exists():
            label_file_count += 1
        with ImageOps.exif_transpose(Image.open(image_path)) as image:
            image_size = image.size
        detections, parse_issues = load_yolo_detections(label_path, image_size, class_names)
        image_issues: list[dict[str, Any]] = []
        for issue in parse_issues:
            image_issues.append({"image_name": image_path.name, "label_name": label_path.name, **issue})
        if len(detections) == 0:
            empty_label_files += 1
        if detections.class_id is not None:
            for class_id in detections.class_id:
                class_counts[class_names[int(class_id)]] += 1
        image_issues.extend(find_duplicate_issues(detections, image_path.name, label_path.name, duplicate_iou_threshold))
        image_issues.extend(find_orphan_ppe_issues(detections, image_path.name, label_path.name))
        issues.extend(image_issues)
        per_image.append(
            {
                "image_name": image_path.name,
                "label_name": label_path.name,
                "detections": int(len(detections)),
                "issues": len(image_issues),
            }
        )

    issue_counts = Counter(issue["issue"] for issue in issues)
    return {
        "image_count": len(image_paths),
        "label_file_count": label_file_count,
        "empty_label_files": empty_label_files,
        "class_counts": dict(class_counts),
        "malformed_rows": issue_counts.get("malformed_row", 0),
        "invalid_class_rows": issue_counts.get("invalid_class", 0),
        "non_positive_boxes": issue_counts.get("non_positive_box", 0),
        "duplicate_boxes": issue_counts.get("duplicate_box", 0),
        "orphan_ppe_boxes": issue_counts.get("orphan_ppe_box", 0),
        "missing_label_files": issue_counts.get("missing_label_file", 0),
        "issue_counts": dict(issue_counts),
        "issues": issues,
        "images": per_image,
    }


def detection_labels(detections: sv.Detections, class_names: Sequence[str]) -> list[str]:
    if detections.class_id is None:
        return []
    return [class_names[int(class_id)] for class_id in detections.class_id]


def render_overlay(
    image_path: Path,
    label_path: Path,
    output_path: Path,
    class_names: Sequence[str] = DEFAULT_CLASSES,
) -> Path:
    image = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
    scene = np.array(image)
    detections, _issues = load_yolo_detections(label_path, image.size, class_names)
    palette = color_palette(class_names)
    box_annotator = sv.BoxAnnotator(color=palette, thickness=max(2, round(min(image.size) / 500)))
    label_annotator = sv.LabelAnnotator(color=palette, text_color=sv.Color.BLACK, text_scale=0.45, text_padding=4)
    annotated = box_annotator.annotate(scene=scene.copy(), detections=detections)
    annotated = label_annotator.annotate(scene=annotated, detections=detections, labels=detection_labels(detections, class_names))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(annotated).save(output_path, quality=95)
    return output_path


def make_thumbnail(image_path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    thumb = Image.new("RGB", size, "white")
    thumb.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return thumb


def render_contact_sheets(
    overlay_paths: Sequence[Path],
    output_dir: Path,
    columns: int = 4,
    rows: int = 3,
    thumb_size: tuple[int, int] = (384, 216),
    label_height: int = 36,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    per_sheet = columns * rows
    sheet_paths: list[Path] = []
    for sheet_index, start in enumerate(range(0, len(overlay_paths), per_sheet), start=1):
        chunk = overlay_paths[start : start + per_sheet]
        cell_width = thumb_size[0]
        cell_height = thumb_size[1] + label_height
        sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "white")
        draw = ImageDraw.Draw(sheet)
        for offset, overlay_path in enumerate(chunk):
            col = offset % columns
            row = offset // columns
            x = col * cell_width
            y = row * cell_height
            sheet.paste(make_thumbnail(overlay_path, thumb_size), (x, y))
            draw.rectangle([x, y + thumb_size[1], x + cell_width, y + cell_height], fill=(245, 245, 245))
            draw.text((x + 6, y + thumb_size[1] + 7), overlay_path.stem[:55], fill=(20, 20, 20))
        sheet_path = output_dir / f"boxed_contact_sheet_{sheet_index:03d}.jpg"
        sheet.save(sheet_path, quality=90)
        sheet_paths.append(sheet_path)
    return sheet_paths


def write_issues_csv(path: Path, issues: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for issue in issues:
        for key in issue:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or ["issue"])
        writer.writeheader()
        writer.writerows(issues)


def render_qc_outputs(
    images_dir: Path,
    labels_dir: Path,
    output_dir: Path,
    class_names: Sequence[str] = DEFAULT_CLASSES,
    columns: int = 4,
    rows: int = 3,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir = output_dir / "overlays"
    contact_sheets_dir = output_dir / "contact_sheets"
    overlay_paths = [
        render_overlay(image_path, labels_dir / f"{image_path.stem}.txt", overlays_dir / image_path.name, class_names)
        for image_path in list_images(images_dir)
    ]
    sheet_paths = render_contact_sheets(overlay_paths, contact_sheets_dir, columns=columns, rows=rows)
    summary = summarize_yolo_directory(images_dir, labels_dir, class_names)
    summary_path = output_dir / "qc_summary.json"
    issues_path = output_dir / "qc_issues.csv"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_issues_csv(issues_path, summary["issues"])
    return {
        "summary_path": str(summary_path),
        "issues_path": str(issues_path),
        "overlay_count": len(overlay_paths),
        "contact_sheets": [str(path) for path in sheet_paths],
    }


def parse_classes(raw: str) -> list[str]:
    classes = [item.strip() for item in raw.split(",") if item.strip()]
    if not classes:
        raise ValueError("At least one class name is required")
    return classes
