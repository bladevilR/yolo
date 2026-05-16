#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render YOLO label overlays and contact sheets for quick QA."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont, ImageOps


DEFAULT_CLASSES = ["person", "head", "helmet", "vest", "no_helmet", "no_vest"]
COLORS = {
    "person": (48, 114, 255),
    "head": (180, 80, 220),
    "helmet": (255, 210, 0),
    "vest": (40, 190, 90),
    "no_helmet": (235, 70, 70),
    "no_vest": (255, 120, 30),
}


def parse_yolo_label_line(line: str) -> tuple[int, list[float]]:
    parts = line.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expected 5 fields in YOLO label line, got {len(parts)}: {line!r}")
    return int(parts[0]), [float(value) for value in parts[1:]]


def xywhn_to_xyxy(box: Sequence[float], width: int, height: int) -> tuple[int, int, int, int]:
    x_center, y_center, box_width, box_height = box
    x1 = round((x_center - box_width / 2) * width)
    y1 = round((y_center - box_height / 2) * height)
    x2 = round((x_center + box_width / 2) * width)
    y2 = round((y_center + box_height / 2) * height)
    return (
        max(0, min(width - 1, x1)),
        max(0, min(height - 1, y1)),
        max(0, min(width - 1, x2)),
        max(0, min(height - 1, y2)),
    )


def read_labels(label_path: Path) -> list[tuple[int, list[float]]]:
    if not label_path.exists():
        return []
    labels: list[tuple[int, list[float]]] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            labels.append(parse_yolo_label_line(line))
    return labels


def draw_labels_on_image(
    image_path: Path,
    label_path: Path,
    class_names: Sequence[str],
) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    font = ImageFont.load_default()

    for class_id, box in read_labels(label_path):
        if class_id < 0 or class_id >= len(class_names):
            continue
        class_name = class_names[class_id]
        color = COLORS.get(class_name, (255, 255, 255))
        x1, y1, x2, y2 = xywhn_to_xyxy(box, width, height)
        thickness = max(2, round(min(width, height) / 500))
        for offset in range(thickness):
            draw.rectangle([x1 - offset, y1 - offset, x2 + offset, y2 + offset], outline=color)
        text_bbox = draw.textbbox((x1, y1), class_name, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        text_y = max(0, y1 - text_h - 4)
        draw.rectangle([x1, text_y, x1 + text_w + 6, text_y + text_h + 4], fill=color)
        draw.text((x1 + 3, text_y + 2), class_name, fill=(0, 0, 0), font=font)

    return image


def make_thumbnail(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.copy()
    image.thumbnail(size, Image.Resampling.LANCZOS)
    thumb = Image.new("RGB", size, "white")
    thumb.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return thumb


def render_contact_sheets(
    images_dir: Path,
    labels_dir: Path,
    output_dir: Path,
    class_names: Sequence[str],
    columns: int = 5,
    rows: int = 4,
    thumb_size: tuple[int, int] = (384, 216),
    label_height: int = 36,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(images_dir.glob("*.jpg"))
    per_sheet = columns * rows
    sheet_paths: list[Path] = []

    for sheet_index, start in enumerate(range(0, len(image_paths), per_sheet), start=1):
        chunk = image_paths[start : start + per_sheet]
        cell_w, cell_h = thumb_size[0], thumb_size[1] + label_height
        sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
        draw = ImageDraw.Draw(sheet)

        for offset, image_path in enumerate(chunk):
            col = offset % columns
            row = offset // columns
            x = col * cell_w
            y = row * cell_h
            label_path = labels_dir / f"{image_path.stem}.txt"
            annotated = draw_labels_on_image(image_path, label_path, class_names)
            thumb = make_thumbnail(annotated, thumb_size)
            sheet.paste(thumb, (x, y))
            draw.rectangle([x, y + thumb_size[1], x + cell_w, y + cell_h], fill=(245, 245, 245))
            draw.text((x + 6, y + thumb_size[1] + 7), image_path.stem[:55], fill=(20, 20, 20))

        sheet_path = output_dir / f"boxed_contact_sheet_{sheet_index:03d}.jpg"
        sheet.save(sheet_path, quality=90)
        sheet_paths.append(sheet_path)
    return sheet_paths


def parse_classes(raw: str) -> list[str]:
    classes = [item.strip() for item in raw.split(",") if item.strip()]
    if not classes:
        raise ValueError("at least one class is required")
    return classes


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--classes", default=",".join(DEFAULT_CLASSES))
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--rows", type=int, default=4)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    sheets = render_contact_sheets(
        images_dir=args.images,
        labels_dir=args.labels,
        output_dir=args.output,
        class_names=parse_classes(args.classes),
        columns=args.columns,
        rows=args.rows,
    )
    print(f"Rendered boxed contact sheets: {len(sheets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
