#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply Codex visual triage suggestions into reversible draft YOLO labels."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


PERSON_CLASS = 0


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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def parse_label(line: str) -> Label | None:
    parts = line.strip().split()
    if len(parts) != 5:
        return None
    try:
        class_id = int(parts[0])
        x, y, w, h = (float(part) for part in parts[1:])
    except ValueError:
        return None
    if w <= 0 or h <= 0:
        return None
    return Label(class_id, clamp01(x), clamp01(y), clamp01(w), clamp01(h))


def read_labels(path: Path) -> list[Label]:
    if not path.exists():
        return []
    labels: list[Label] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        label = parse_label(line)
        if label is not None:
            labels.append(label)
    return labels


def write_labels(path: Path, labels: Sequence[Label]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(label.as_line() for label in labels) + ("\n" if labels else ""), encoding="utf-8")


def parse_box(row: Mapping[str, str]) -> tuple[int, int, int, int]:
    return tuple(int(float(row[key])) for key in ("x1", "y1", "x2", "y2"))  # type: ignore[return-value]


def label_to_xyxy(label: Label, width: int, height: int) -> tuple[int, int, int, int]:
    x1 = round((label.x - label.w / 2) * width)
    y1 = round((label.y - label.h / 2) * height)
    x2 = round((label.x + label.w / 2) * width)
    y2 = round((label.y + label.h / 2) * height)
    return x1, y1, x2, y2


def xyxy_to_label(class_id: int, box: tuple[int, int, int, int], width: int, height: int) -> Label:
    x1, y1, x2, y2 = box
    return Label(
        class_id=class_id,
        x=clamp01(((x1 + x2) / 2) / width),
        y=clamp01(((y1 + y2) / 2) / height),
        w=clamp01(max(1, x2 - x1) / width),
        h=clamp01(max(1, y2 - y1) / height),
    )


def area(box: tuple[int, int, int, int]) -> int:
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def intersection(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))


def iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    inter = intersection(a, b)
    union = area(a) + area(b) - inter
    return 0.0 if union <= 0 else inter / union


def smaller_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    inter = intersection(a, b)
    smaller = min(area(a), area(b))
    return 0.0 if smaller <= 0 else inter / smaller


def load_image_sizes(rows: Sequence[Mapping[str, str]], images_dir: Path) -> dict[str, tuple[int, int]]:
    from PIL import Image

    sizes: dict[str, tuple[int, int]] = {}
    for row in rows:
        image_name = str(row["image_name"])
        if image_name in sizes:
            continue
        with Image.open(images_dir / image_name) as image:
            sizes[image_name] = image.size
    return sizes


def has_matching_person(
    labels: Sequence[Label],
    candidate: tuple[int, int, int, int],
    width: int,
    height: int,
    iou_threshold: float,
    containment_threshold: float,
) -> bool:
    for label in labels:
        if label.class_id != PERSON_CLASS:
            continue
        box = label_to_xyxy(label, width, height)
        if iou(box, candidate) >= iou_threshold or smaller_overlap(box, candidate) >= containment_threshold:
            return True
    return False


def apply_rows_to_label_file(
    labels: Sequence[Label],
    rows: Sequence[Mapping[str, str]],
    width: int,
    height: int,
    add_iou: float,
    add_containment: float,
    remove_iou: float,
    remove_containment: float,
) -> tuple[list[Label], dict[str, int]]:
    updated = list(labels)
    stats = {
        "person_added": 0,
        "person_removed": 0,
        "skipped": 0,
    }
    for row in rows:
        decision = row.get("codex_suggested_decision", "")
        candidate = parse_box(row)
        if decision == "true_worker_fix_label":
            if has_matching_person(updated, candidate, width, height, add_iou, add_containment):
                stats["skipped"] += 1
                continue
            updated.append(xyxy_to_label(PERSON_CLASS, candidate, width, height))
            stats["person_added"] += 1
        elif decision == "hard_negative_not_worker":
            kept: list[Label] = []
            removed = 0
            for label in updated:
                if label.class_id != PERSON_CLASS:
                    kept.append(label)
                    continue
                box = label_to_xyxy(label, width, height)
                should_remove = iou(box, candidate) >= remove_iou or smaller_overlap(box, candidate) >= remove_containment
                if should_remove:
                    removed += 1
                else:
                    kept.append(label)
            updated = kept
            stats["person_removed"] += removed
            if removed == 0:
                stats["skipped"] += 1
        else:
            stats["skipped"] += 1
    return updated, stats


def grouped_by_image(rows: Sequence[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["image_name"], []).append(row)
    return grouped


def copy_source_labels(source_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for source in source_dir.glob("*.txt"):
        shutil.copy2(source, output_dir / source.name)


def apply_triage_to_workspace(
    workspace: Path,
    triage_csv: Path | None = None,
    output_label_dir: Path | None = None,
    add_iou: float = 0.20,
    add_containment: float = 0.60,
    remove_iou: float = 0.20,
    remove_containment: float = 0.70,
) -> dict[str, Any]:
    triage_path = triage_csv or workspace / "codex_visual_triage_20260520.csv"
    output_dir = output_label_dir or workspace / "labels_codex_draft"
    images_dir = workspace / "images"
    source_labels_dir = workspace / "labels_reviewed"
    rows = read_csv(triage_path)
    sizes = load_image_sizes(rows, images_dir)
    grouped = grouped_by_image(rows)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    copy_source_labels(source_labels_dir, output_dir)

    summary = {
        "images": len(grouped),
        "review_rows": len(rows),
        "person_added": 0,
        "person_removed": 0,
        "skipped": 0,
        "output_label_dir": str(output_dir),
    }
    manifest_rows: list[dict[str, Any]] = []
    for image_name, image_rows in grouped.items():
        width, height = sizes[image_name]
        label_name = f"{Path(image_name).stem}.txt"
        label_path = output_dir / label_name
        before = read_labels(label_path)
        after, stats = apply_rows_to_label_file(
            labels=before,
            rows=image_rows,
            width=width,
            height=height,
            add_iou=add_iou,
            add_containment=add_containment,
            remove_iou=remove_iou,
            remove_containment=remove_containment,
        )
        write_labels(label_path, after)
        for key in ("person_added", "person_removed", "skipped"):
            summary[key] += stats[key]
        manifest_rows.append(
            {
                "image_name": image_name,
                "label_name": label_name,
                "before_labels": len(before),
                "after_labels": len(after),
                **stats,
            }
        )

    fieldnames = ["image_name", "label_name", "before_labels", "after_labels", "person_added", "person_removed", "skipped"]
    write_csv(workspace / "codex_draft_label_manifest.csv", manifest_rows, fieldnames)
    (workspace / "codex_draft_label_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--triage-csv", type=Path)
    parser.add_argument("--output-label-dir", type=Path)
    parser.add_argument("--add-iou", type=float, default=0.20)
    parser.add_argument("--add-containment", type=float, default=0.60)
    parser.add_argument("--remove-iou", type=float, default=0.20)
    parser.add_argument("--remove-containment", type=float, default=0.70)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    summary = apply_triage_to_workspace(
        workspace=args.workspace,
        triage_csv=args.triage_csv,
        output_label_dir=args.output_label_dir,
        add_iou=args.add_iou,
        add_containment=args.add_containment,
        remove_iou=args.remove_iou,
        remove_containment=args.remove_containment,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
