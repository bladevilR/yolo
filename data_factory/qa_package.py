#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a small QA review package from an extracted YOLO dataset."""

from __future__ import annotations

import argparse
import csv
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TypeVar

from PIL import Image, ImageDraw, ImageOps


T = TypeVar("T")


def pick_evenly_spaced(items: Sequence[T], limit: int) -> list[T]:
    if limit <= 0:
        return []
    if len(items) <= limit:
        return list(items)
    if limit == 1:
        return [items[0]]

    max_index = len(items) - 1
    return [items[round(i * max_index / (limit - 1))] for i in range(limit)]


def allocate_group_counts(group_sizes: Mapping[str, int], total: int) -> dict[str, int]:
    groups = OrderedDict((name, max(0, size)) for name, size in group_sizes.items())
    if total <= 0 or not groups:
        return {name: 0 for name in groups}

    positive_groups = [(name, size) for name, size in groups.items() if size > 0]
    if total < len(positive_groups):
        selected = {
            name
            for name, _size in sorted(
                positive_groups,
                key=lambda item: (-item[1], list(groups).index(item[0])),
            )[:total]
        }
        return {name: int(name in selected) for name in groups}

    allocations = {name: (1 if size > 0 else 0) for name, size in groups.items()}
    remaining = total - sum(allocations.values())
    positive_total = sum(size for _name, size in positive_groups)
    if remaining <= 0 or positive_total <= 0:
        return allocations

    remainders: list[tuple[float, int, str]] = []
    for name, size in positive_groups:
        raw = remaining * size / positive_total
        whole = int(raw)
        allocations[name] += whole
        remainders.append((raw - whole, size, name))

    leftover = total - sum(allocations.values())
    for _fraction, _size, name in sorted(remainders, reverse=True)[:leftover]:
        allocations[name] += 1
    return allocations


def read_frame_records(frames_csv: Path) -> list[dict[str, str]]:
    with frames_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def group_by_video(records: Iterable[dict[str, str]]) -> OrderedDict[str, list[dict[str, str]]]:
    groups: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for record in records:
        groups.setdefault(record["video_name"], []).append(record)
    return groups


def select_records(records: Sequence[dict[str, str]], sample_size: int) -> list[dict[str, str]]:
    groups = group_by_video(records)
    allocations = allocate_group_counts(
        {video_name: len(video_records) for video_name, video_records in groups.items()},
        sample_size,
    )
    selected: list[dict[str, str]] = []
    for video_name, video_records in groups.items():
        selected.extend(pick_evenly_spaced(video_records, allocations[video_name]))
    selected.sort(key=lambda row: (row["video_name"], int(row["frame_index"])))
    return selected


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def resolve_label_source(
    image_path: Path,
    dataset_images_root: Path,
    default_label_path: Path,
    label_root: Path | None,
) -> Path:
    if label_root is None:
        return default_label_path
    try:
        relative_image = image_path.relative_to(dataset_images_root)
    except ValueError:
        return label_root / f"{image_path.stem}.txt"
    return label_root / relative_image.with_suffix(".txt")


def copy_sample_files(
    records: Sequence[dict[str, str]],
    output_root: Path,
    dataset_images_root: Path,
    label_root: Path | None = None,
) -> list[dict[str, str]]:
    images_dir = output_root / "images"
    labels_dir = output_root / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, str]] = []
    for index, record in enumerate(records, start=1):
        image_path = Path(record["image_path"])
        label_path = resolve_label_source(
            image_path=image_path,
            dataset_images_root=dataset_images_root,
            default_label_path=Path(record["label_path"]),
            label_root=label_root,
        )
        sample_name = f"{index:04d}_{image_path.name}"
        sample_label_name = f"{Path(sample_name).stem}.txt"
        sample_image_path = images_dir / sample_name
        sample_label_path = labels_dir / sample_label_name
        shutil.copy2(image_path, sample_image_path)
        if label_path.exists():
            shutil.copy2(label_path, sample_label_path)
        else:
            sample_label_path.write_text("", encoding="utf-8")

        updated = dict(record)
        updated["sample_index"] = str(index)
        updated["sample_image_path"] = str(sample_image_path)
        updated["sample_label_path"] = str(sample_label_path)
        copied.append(updated)
    return copied


def make_thumbnail(image_path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        thumb = Image.new("RGB", size, "white")
        x = (size[0] - image.width) // 2
        y = (size[1] - image.height) // 2
        thumb.paste(image, (x, y))
        return thumb


def make_contact_sheets(
    records: Sequence[dict[str, str]],
    output_dir: Path,
    columns: int = 5,
    rows: int = 4,
    thumb_size: tuple[int, int] = (384, 216),
    label_height: int = 44,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    per_sheet = columns * rows
    sheet_paths: list[Path] = []

    for sheet_index, start in enumerate(range(0, len(records), per_sheet), start=1):
        chunk = records[start : start + per_sheet]
        cell_w, cell_h = thumb_size[0], thumb_size[1] + label_height
        sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
        draw = ImageDraw.Draw(sheet)

        for offset, record in enumerate(chunk):
            col = offset % columns
            row = offset // columns
            x = col * cell_w
            y = row * cell_h
            thumb = make_thumbnail(Path(record["sample_image_path"]), thumb_size)
            sheet.paste(thumb, (x, y))
            label = (
                f"{record['sample_index']} {record['video_name']}\n"
                f"t={float(record['timestamp_seconds']):.1f}s f={record['frame_index']}"
            )
            draw.rectangle([x, y + thumb_size[1], x + cell_w, y + cell_h], fill=(245, 245, 245))
            draw.text((x + 6, y + thumb_size[1] + 5), label, fill=(20, 20, 20))

        sheet_path = output_dir / f"contact_sheet_{sheet_index:03d}.jpg"
        sheet.save(sheet_path, quality=90)
        sheet_paths.append(sheet_path)
    return sheet_paths


def create_qa_package(
    dataset_root: Path,
    output_root: Path,
    sample_size: int,
    label_root: Path | None = None,
    columns: int = 5,
    rows: int = 4,
) -> tuple[list[dict[str, str]], list[Path]]:
    records = read_frame_records(dataset_root / "metadata" / "frames.csv")
    selected = select_records(records, sample_size)
    if output_root.exists():
        raise FileExistsError(f"Output already exists: {output_root}")
    output_root.mkdir(parents=True)
    copied = copy_sample_files(
        selected,
        output_root,
        dataset_images_root=dataset_root / "images",
        label_root=label_root,
    )
    fieldnames = list(copied[0].keys()) if copied else []
    if fieldnames:
        write_csv(output_root / "sample.csv", copied, fieldnames)
    sheets = make_contact_sheets(copied, output_root / "contact_sheets", columns=columns, rows=rows)
    write_readme(output_root, dataset_root, copied, sheets)
    return copied, sheets


def write_readme(
    output_root: Path,
    dataset_root: Path,
    records: Sequence[dict[str, str]],
    sheets: Sequence[Path],
) -> None:
    video_counts: OrderedDict[str, int] = OrderedDict()
    for record in records:
        video_counts[record["video_name"]] = video_counts.get(record["video_name"], 0) + 1

    lines = [
        "# QA Review Package",
        "",
        f"- Source dataset: {dataset_root}",
        f"- Sample images: {len(records)}",
        f"- Contact sheets: {len(sheets)}",
        "",
        "Per-video sample counts:",
    ]
    lines.extend(f"- {name}: {count}" for name, count in video_counts.items())
    lines.extend(
        [
            "",
            "Review flow:",
            "1. Open the contact sheets for fast visual inspection.",
            "2. Inspect copied images if a sheet shows unclear PPE or tiny people.",
            "3. Use sample.csv to trace any image back to source video and timestamp.",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path, help="Extracted YOLO dataset root")
    parser.add_argument("--output", required=True, type=Path, help="QA package output directory")
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--label-root", type=Path, default=None, help="Optional label tree to copy instead of frames.csv labels")
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--rows", type=int, default=4)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    records, sheets = create_qa_package(
        dataset_root=args.dataset,
        output_root=args.output,
        sample_size=args.sample_size,
        label_root=args.label_root,
        columns=args.columns,
        rows=args.rows,
    )
    print(f"Created QA package: {args.output}")
    print(f"Sample images: {len(records)}")
    print(f"Contact sheets: {len(sheets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
