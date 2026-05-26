#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a box-level review workspace from a PPE demo review queue."""

from __future__ import annotations

import argparse
import csv
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def ensure_fresh_output(output_root: Path, force: bool = False) -> None:
    if not output_root.exists():
        output_root.mkdir(parents=True)
        return
    if not force:
        raise FileExistsError(f"Output already exists: {output_root}")
    shutil.rmtree(output_root)
    output_root.mkdir(parents=True)


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


def build_file_index(root: Path, suffixes: set[str]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes and path.name not in index:
            index[path.name] = path
    return index


def parse_box(row: Mapping[str, str]) -> tuple[int, int, int, int]:
    return tuple(int(float(row[key])) for key in ("x1", "y1", "x2", "y2"))  # type: ignore[return-value]


def clip_box(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    return (
        max(0, min(width - 1, x1)),
        max(0, min(height - 1, y1)),
        max(0, min(width - 1, x2)),
        max(0, min(height - 1, y2)),
    )


def crop_with_context(
    image: np.ndarray,
    box: tuple[int, int, int, int],
    pad_x_ratio: float = 0.45,
    pad_y_ratio: float = 0.35,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = clip_box(box, width, height)
    box_w = max(1, x2 - x1)
    box_h = max(1, y2 - y1)
    pad_x = max(30, round(box_w * pad_x_ratio))
    pad_y = max(30, round(box_h * pad_y_ratio))
    cx1 = max(0, x1 - pad_x)
    cy1 = max(0, y1 - pad_y)
    cx2 = min(width, x2 + pad_x)
    cy2 = min(height, y2 + pad_y)
    crop = image[cy1:cy2, cx1:cx2].copy()
    return crop, (cx1, cy1, cx2, cy2)


def draw_candidate_on_crop(
    crop: np.ndarray,
    crop_box: tuple[int, int, int, int],
    candidate_box: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> np.ndarray:
    cx1, cy1, _cx2, _cy2 = crop_box
    x1, y1, x2, y2 = candidate_box
    cv2.rectangle(crop, (x1 - cx1, y1 - cy1), (x2 - cx1, y2 - cy1), color, 3)
    return crop


def row_color(row: Mapping[str, str]) -> tuple[int, int, int]:
    if row.get("queue_source") == "accepted_event":
        return (60, 180, 60) if row.get("status") == "ok" else (40, 40, 230)
    return (0, 170, 255)


def write_contact_sheet(
    rows: Sequence[Mapping[str, Any]],
    output_path: Path,
    columns: int = 5,
    tile_width: int = 300,
    tile_height: int = 300,
) -> None:
    if not rows:
        return
    caption_height = 74
    margin = 8
    tiles: list[np.ndarray] = []
    for row in rows:
        crop_path = Path(str(row["crop_path"]))
        image = cv2.imread(str(crop_path))
        if image is None:
            continue
        scale = min(tile_width / image.shape[1], tile_height / image.shape[0])
        resized_width = max(1, int(image.shape[1] * scale))
        resized_height = max(1, int(image.shape[0] * scale))
        resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_AREA)
        tile = np.full((tile_height + caption_height, tile_width, 3), 255, dtype=np.uint8)
        y_offset = (tile_height - resized_height) // 2
        x_offset = (tile_width - resized_width) // 2
        tile[y_offset : y_offset + resized_height, x_offset : x_offset + resized_width] = resized
        color = row_color(row)
        cv2.putText(tile, f"{row['review_id']} {row['queue_source']}", (6, tile_height + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.44, color, 1, cv2.LINE_AA)
        cv2.putText(tile, str(row["review_reason"])[:42], (6, tile_height + 39), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (30, 30, 30), 1, cv2.LINE_AA)
        cv2.putText(tile, str(row["recommendation"])[:42], (6, tile_height + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (30, 30, 30), 1, cv2.LINE_AA)
        tiles.append(tile)

    if not tiles:
        return
    sheet_rows = int(np.ceil(len(tiles) / columns))
    sheet = np.full(
        (sheet_rows * (tile_height + caption_height + margin) + margin, columns * (tile_width + margin) + margin, 3),
        245,
        dtype=np.uint8,
    )
    for index, tile in enumerate(tiles):
        row_index = index // columns
        col_index = index % columns
        y = margin + row_index * (tile_height + caption_height + margin)
        x = margin + col_index * (tile_width + margin)
        sheet[y : y + tile.shape[0], x : x + tile.shape[1]] = tile
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), sheet)


def copy_label(label_index: Mapping[str, Path], image_name: str, target: Path) -> None:
    label_name = f"{Path(image_name).stem}.txt"
    source = label_index.get(label_name)
    if source is not None:
        shutil.copy2(source, target)
    else:
        target.write_text("", encoding="utf-8")


def create_review_queue_workspace(
    queue_csv: Path,
    images_root: Path,
    labels_root: Path,
    output_root: Path,
    force: bool = False,
) -> list[dict[str, Any]]:
    rows = read_csv(queue_csv)
    image_index = build_file_index(images_root, {".jpg", ".jpeg", ".png"})
    label_index = build_file_index(labels_root, {".txt"})

    ensure_fresh_output(output_root, force=force)
    images_out = output_root / "images"
    crops_out = output_root / "crops"
    labels_current_out = output_root / "labels_current"
    labels_reviewed_out = output_root / "labels_reviewed"
    for path in (images_out, crops_out, labels_current_out, labels_reviewed_out):
        path.mkdir(parents=True, exist_ok=True)

    copied_images: set[str] = set()
    output_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        image_name = row["image_name"]
        source_image = image_index.get(image_name)
        if source_image is None:
            raise FileNotFoundError(f"Image from queue not found: {image_name}")

        image_target = images_out / image_name
        label_name = f"{Path(image_name).stem}.txt"
        current_label_target = labels_current_out / label_name
        reviewed_label_target = labels_reviewed_out / label_name
        if image_name not in copied_images:
            shutil.copy2(source_image, image_target)
            copy_label(label_index, image_name, current_label_target)
            copy_label(label_index, image_name, reviewed_label_target)
            copied_images.add(image_name)

        image = cv2.imread(str(source_image))
        if image is None:
            raise ValueError(f"Cannot read image: {source_image}")
        candidate_box = parse_box(row)
        crop, crop_box = crop_with_context(image, candidate_box)
        crop = draw_candidate_on_crop(crop, crop_box, candidate_box, row_color(row))
        review_id = f"q{index:04d}"
        crop_name = f"{review_id}__{Path(image_name).stem}.jpg"
        crop_path = crops_out / crop_name
        cv2.imwrite(str(crop_path), crop)

        updated = dict(row)
        updated["review_id"] = review_id
        updated["label_name"] = label_name
        updated["manual_decision"] = "todo"
        updated["manual_status"] = "todo"
        updated["manual_notes"] = ""
        updated["local_image_path"] = str(image_target)
        updated["crop_path"] = str(crop_path)
        updated["current_label_path"] = str(current_label_target)
        updated["reviewed_label_path"] = str(reviewed_label_target)
        output_rows.append(updated)

    fieldnames = merge_fieldnames(
        output_rows,
        [
            "review_id",
            "label_name",
            "manual_decision",
            "manual_status",
            "manual_notes",
            "local_image_path",
            "crop_path",
            "current_label_path",
            "reviewed_label_path",
        ],
    )
    write_csv(output_root / "review_queue_workspace.csv", output_rows, fieldnames)
    write_contact_sheet(output_rows, output_root / "crop_contact_sheets" / "review_queue_contact_sheet_001.jpg")
    write_readme(output_root, queue_csv, images_root, labels_root, output_rows)
    return output_rows


def write_readme(
    output_root: Path,
    queue_csv: Path,
    images_root: Path,
    labels_root: Path,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    source_counts = Counter(str(row["queue_source"]) for row in rows)
    reason_counts = Counter(str(row["review_reason"]) for row in rows)
    unique_images = len({str(row["image_name"]) for row in rows})
    lines = [
        "# PPE Review Queue Workspace",
        "",
        f"- Source queue: {queue_csv}",
        f"- Source images: {images_root}",
        f"- Source labels: {labels_root}",
        f"- Review rows: {len(rows)}",
        f"- Unique images: {unique_images}",
        "",
        "Source counts:",
    ]
    lines.extend(f"- {name}: {count}" for name, count in sorted(source_counts.items()))
    lines.extend(["", "Review reasons:"])
    lines.extend(f"- {name}: {count}" for name, count in sorted(reason_counts.items()))
    lines.extend(
        [
            "",
            "Folders:",
            "",
            "- `images/`: full source images copied for label editing.",
            "- `crops/`: candidate-level crops with the review box drawn.",
            "- `labels_current/`: current YOLO labels copied from the source dataset.",
            "- `labels_reviewed/`: editable labels for the next corrected dataset.",
            "- `crop_contact_sheets/`: fast visual scan of all queue rows.",
            "",
            "Manual decision values to use:",
            "",
            "- `true_worker_fix_label`",
            "- `hard_negative_not_worker`",
            "- `duplicate`",
            "- `unclear_skip`",
            "- `ppe_status_fix`",
            "",
            "Set `manual_status=done` after correction.",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-csv", required=True, type=Path)
    parser.add_argument("--images-root", required=True, type=Path)
    parser.add_argument("--labels-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    rows = create_review_queue_workspace(
        queue_csv=args.queue_csv,
        images_root=args.images_root,
        labels_root=args.labels_root,
        output_root=args.output,
        force=args.force,
    )
    print(f"Created PPE review queue workspace: {args.output}")
    print(f"Review rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
