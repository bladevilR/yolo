#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply a conservative automatic PPE label review pass to a review workspace."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np


PERSON_CLASS = 0
HELMET_CLASS = 2
VEST_CLASS = 3
DEFAULT_KEEP_CLASSES = {PERSON_CLASS, HELMET_CLASS, VEST_CLASS}


@dataclass(frozen=True)
class Label:
    class_id: int
    x: float
    y: float
    w: float
    h: float

    def as_line(self) -> str:
        return f"{self.class_id} {self.x:.6f} {self.y:.6f} {self.w:.6f} {self.h:.6f}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_label_line(line: str) -> Label | None:
    parts = line.strip().split()
    if len(parts) != 5:
        return None
    try:
        class_id = int(parts[0])
        x, y, w, h = (float(value) for value in parts[1:])
    except ValueError:
        return None
    if w <= 0 or h <= 0:
        return None
    return Label(class_id, clamp01(x), clamp01(y), clamp01(w), clamp01(h))


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def read_labels(path: Path) -> list[Label]:
    if not path.exists():
        return []
    labels: list[Label] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parsed = parse_label_line(line)
        if parsed is not None:
            labels.append(parsed)
    return labels


def write_labels(path: Path, labels: Sequence[Label]) -> None:
    path.write_text("\n".join(label.as_line() for label in labels) + ("\n" if labels else ""), encoding="utf-8")


def label_to_xyxy(label: Label, width: int, height: int) -> tuple[int, int, int, int]:
    x1 = round((label.x - label.w / 2) * width)
    y1 = round((label.y - label.h / 2) * height)
    x2 = round((label.x + label.w / 2) * width)
    y2 = round((label.y + label.h / 2) * height)
    return (
        max(0, min(width - 1, x1)),
        max(0, min(height - 1, y1)),
        max(0, min(width - 1, x2)),
        max(0, min(height - 1, y2)),
    )


def xyxy_to_label(class_id: int, box: tuple[int, int, int, int], width: int, height: int) -> Label:
    x1, y1, x2, y2 = box
    return Label(
        class_id=class_id,
        x=clamp01(((x1 + x2) / 2) / width),
        y=clamp01(((y1 + y2) / 2) / height),
        w=clamp01(max(1, x2 - x1) / width),
        h=clamp01(max(1, y2 - y1) / height),
    )


def box_iou(a: Label, b: Label) -> float:
    ax1 = a.x - a.w / 2
    ay1 = a.y - a.h / 2
    ax2 = a.x + a.w / 2
    ay2 = a.y + a.h / 2
    bx1 = b.x - b.w / 2
    by1 = b.y - b.h / 2
    bx2 = b.x + b.w / 2
    by2 = b.y + b.h / 2
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    intersection = iw * ih
    union = a.w * a.h + b.w * b.h - intersection
    return intersection / union if union > 0 else 0.0


def deduplicate_labels(labels: Sequence[Label], iou_threshold: float = 0.9) -> list[Label]:
    kept: list[Label] = []
    for label in labels:
        duplicate = any(
            label.class_id == existing.class_id and box_iou(label, existing) >= iou_threshold for existing in kept
        )
        if not duplicate:
            kept.append(label)
    return kept


def filter_labels(labels: Sequence[Label], keep_classes: set[int] = DEFAULT_KEEP_CLASSES) -> list[Label]:
    return [label for label in labels if label.class_id in keep_classes and 0 < label.w <= 1 and 0 < label.h <= 1]


def existing_vest_overlaps_person(person: Label, labels: Sequence[Label]) -> bool:
    return any(label.class_id == VEST_CLASS and box_iou(person, label) > 0.05 for label in labels)


def detect_vest_candidate(image_bgr: np.ndarray, person: Label) -> Label | None:
    height, width = image_bgr.shape[:2]
    px1, py1, px2, py2 = label_to_xyxy(person, width, height)
    person_w = px2 - px1
    person_h = py2 - py1
    if person_w < 18 or person_h < 35:
        return None

    # Focus on torso, excluding most helmet/head and legs. The field footage has
    # top-down person boxes, so keep the torso window slightly generous.
    tx1 = round(px1 + person_w * 0.12)
    tx2 = round(px2 - person_w * 0.12)
    ty1 = round(py1 + person_h * 0.18)
    ty2 = round(py1 + person_h * 0.82)
    if tx2 <= tx1 or ty2 <= ty1:
        return None

    torso = image_bgr[ty1:ty2, tx1:tx2]
    if torso.size == 0:
        return None
    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)

    orange_red = ((hsv[:, :, 0] <= 24) | (hsv[:, :, 0] >= 168)) & (hsv[:, :, 1] >= 80) & (hsv[:, :, 2] >= 80)
    yellow_green = (hsv[:, :, 0] >= 25) & (hsv[:, :, 0] <= 88) & (hsv[:, :, 1] >= 60) & (hsv[:, :, 2] >= 90)
    blue_vest = (hsv[:, :, 0] >= 88) & (hsv[:, :, 0] <= 132) & (hsv[:, :, 1] >= 45) & (hsv[:, :, 2] >= 55)
    mask = (orange_red | yellow_green | blue_vest).astype("uint8") * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    torso_area = max(1, torso.shape[0] * torso.shape[1])
    mask_area = int(np.count_nonzero(mask))
    if mask_area < max(16, torso_area * 0.012):
        return None

    num_labels, components, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates: list[tuple[int, tuple[int, int, int, int]]] = []
    for component_id in range(1, num_labels):
        x, y, w, h, area = stats[component_id]
        if area < max(16, torso_area * 0.018):
            continue
        if w < 4 or h < 6:
            continue
        candidates.append((int(area), (tx1 + x, ty1 + y, tx1 + x + w, ty1 + y + h)))

    if not candidates:
        return None

    # If high-visibility color is present in the torso, label the torso region rather than
    # only the color pixels. Small color patches are too fragmented for the first model.
    box = (tx1, ty1, tx2, ty2)
    return xyxy_to_label(VEST_CLASS, box, width, height)


def review_labels_for_image(image_path: Path, labels: Sequence[Label]) -> tuple[list[Label], dict[str, int]]:
    image = cv2.imread(str(image_path))
    if image is None:
        return list(labels), {"invalid_image": 1, "vest_added": 0, "duplicates_removed": 0}

    filtered = filter_labels(labels)
    deduped = deduplicate_labels(filtered)
    stats = {
        "invalid_image": 0,
        "vest_added": 0,
        "duplicates_removed": len(filtered) - len(deduped),
    }

    reviewed = list(deduped)
    for person in [label for label in deduped if label.class_id == PERSON_CLASS]:
        if existing_vest_overlaps_person(person, reviewed):
            continue
        vest = detect_vest_candidate(image, person)
        if vest is None:
            continue
        reviewed.append(vest)
        stats["vest_added"] += 1

    reviewed = deduplicate_labels(reviewed)
    return reviewed, stats


def merge_fieldnames(rows: Sequence[Mapping[str, Any]], extra_fields: Sequence[str]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    for key in extra_fields:
        if key not in names:
            names.append(key)
    return names


def auto_review_workspace(workspace: Path, reset_from_original: bool = False) -> dict[str, Any]:
    rows = read_csv(workspace / "labeling_queue.csv")
    total = {
        "images": len(rows),
        "vest_added": 0,
        "duplicates_removed": 0,
        "invalid_image": 0,
    }
    updated_rows: list[dict[str, Any]] = []

    for row in rows:
        image_path = workspace / "images" / row["image_name"]
        label_name = row.get("label_name") or f"{Path(row['image_name']).stem}.txt"
        label_path = workspace / "labels_reviewed" / label_name
        if reset_from_original:
            original_path = workspace / "labels_pseudo_original" / label_name
            if original_path.exists():
                label_path.write_text(original_path.read_text(encoding="utf-8"), encoding="utf-8")
        original_labels = read_labels(label_path)
        reviewed, stats = review_labels_for_image(image_path, original_labels)
        write_labels(label_path, reviewed)
        for key in ("vest_added", "duplicates_removed", "invalid_image"):
            total[key] += stats[key]

        notes = [
            "codex_auto_review: kept person/helmet/vest, removed duplicate boxes, added torso-level vest candidates where high-visibility color is visible"
        ]
        if stats["vest_added"]:
            notes.append(f"vest_added={stats['vest_added']}")
        if stats["duplicates_removed"]:
            notes.append(f"duplicates_removed={stats['duplicates_removed']}")
        updated = dict(row)
        updated["manual_status"] = "codex_reviewed"
        updated["manual_notes"] = "; ".join(filter(None, [row.get("manual_notes", ""), " | ".join(notes)]))
        updated["codex_vest_added"] = str(stats["vest_added"])
        updated["codex_duplicates_removed"] = str(stats["duplicates_removed"])
        updated_rows.append(updated)

    fieldnames = merge_fieldnames(updated_rows, ["codex_vest_added", "codex_duplicates_removed"])
    write_csv(workspace / "labeling_queue.csv", updated_rows, fieldnames)
    summary_path = workspace / "codex_auto_review_summary.json"
    summary_path.write_text(json.dumps(total, ensure_ascii=False, indent=2), encoding="utf-8")
    return total


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-workspace", required=True, type=Path)
    parser.add_argument("--reset-from-original", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    summary = auto_review_workspace(args.review_workspace, reset_from_original=args.reset_from_original)
    print(f"Auto-reviewed workspace: {args.review_workspace}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
