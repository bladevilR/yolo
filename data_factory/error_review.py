#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a targeted review package for likely pseudo-label mistakes."""

from __future__ import annotations

import argparse
import csv
import shutil
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CLASS_NAMES = ["person", "head", "helmet", "vest", "no_helmet", "no_vest"]


def detection_stats(lines: Sequence[str]) -> dict[str, int]:
    stats = {name: 0 for name in CLASS_NAMES}
    stats["total"] = 0
    for line in lines:
        if not line.strip():
            continue
        class_id = int(line.split()[0])
        stats["total"] += 1
        if 0 <= class_id < len(CLASS_NAMES):
            stats[CLASS_NAMES[class_id]] += 1
    return stats


def review_reason(stats: Mapping[str, int]) -> str:
    if stats.get("total", 0) == 0:
        return "empty_detection"
    if stats.get("no_helmet", 0) or stats.get("no_vest", 0):
        return "violation_class"
    if stats.get("total", 0) >= 15:
        return "many_boxes"
    return "routine_sample"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def label_path_for_record(record: Mapping[str, str], dataset_root: Path, label_root: Path) -> Path:
    image_path = Path(record["image_path"])
    relative = image_path.relative_to(dataset_root / "images")
    return label_root / relative.with_suffix(".txt")


def enrich_records(dataset_root: Path, label_root: Path) -> list[dict[str, Any]]:
    records = read_csv(dataset_root / "metadata" / "frames.csv")
    enriched: list[dict[str, Any]] = []
    for record in records:
        label_path = label_path_for_record(record, dataset_root, label_root)
        lines = label_path.read_text(encoding="utf-8").splitlines() if label_path.exists() else []
        stats = detection_stats(lines)
        item: dict[str, Any] = dict(record)
        item["pseudo_label_path"] = str(label_path)
        item["review_reason"] = review_reason(stats)
        item.update(stats)
        enriched.append(item)
    return enriched


def pick_evenly(items: Sequence[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    if len(items) <= limit:
        return list(items)
    if limit == 1:
        return [items[0]]
    last = len(items) - 1
    return [items[round(i * last / (limit - 1))] for i in range(limit)]


def select_review_records(records: Sequence[dict[str, Any]], sample_size: int) -> list[dict[str, Any]]:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict(
        (reason, []) for reason in ("violation_class", "many_boxes", "empty_detection", "routine_sample")
    )
    for record in records:
        groups.setdefault(str(record["review_reason"]), []).append(record)

    for reason_records in groups.values():
        reason_records.sort(key=lambda item: (item["video_name"], int(item["frame_index"])))

    quotas = {
        "violation_class": min(len(groups["violation_class"]), max(20, sample_size // 4)),
        "many_boxes": min(len(groups["many_boxes"]), max(20, sample_size // 4)),
        "empty_detection": min(len(groups["empty_detection"]), max(20, sample_size // 5)),
    }
    selected: list[dict[str, Any]] = []
    for reason, quota in quotas.items():
        selected.extend(pick_evenly(groups[reason], quota))

    remaining = sample_size - len(selected)
    selected_keys = {(row["image_path"], row["review_reason"]) for row in selected}
    routine_candidates = [
        row
        for row in groups["routine_sample"]
        if (row["image_path"], row["review_reason"]) not in selected_keys
    ]
    selected.extend(pick_evenly(routine_candidates, remaining))
    selected = selected[:sample_size]
    selected.sort(key=lambda row: (str(row["review_reason"]), str(row["video_name"]), int(row["frame_index"])))
    return selected


def copy_review_records(records: Sequence[dict[str, Any]], output_root: Path) -> list[dict[str, Any]]:
    images_dir = output_root / "images"
    labels_dir = output_root / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        image_path = Path(str(record["image_path"]))
        label_path = Path(str(record["pseudo_label_path"]))
        reason = str(record["review_reason"])
        sample_stem = f"{index:04d}_{reason}_{image_path.stem}"
        sample_image = images_dir / f"{sample_stem}.jpg"
        sample_label = labels_dir / f"{sample_stem}.txt"
        shutil.copy2(image_path, sample_image)
        if label_path.exists():
            shutil.copy2(label_path, sample_label)
        else:
            sample_label.write_text("", encoding="utf-8")
        copied_record = dict(record)
        copied_record["sample_index"] = index
        copied_record["sample_image_path"] = str(sample_image)
        copied_record["sample_label_path"] = str(sample_label)
        copied.append(copied_record)
    return copied


def write_readme(output_root: Path, copied: Sequence[Mapping[str, Any]]) -> None:
    reasons = Counter(str(row["review_reason"]) for row in copied)
    lines = [
        "# Pseudo-Label Error Review",
        "",
        f"- Sample images: {len(copied)}",
        "",
        "Reason counts:",
    ]
    lines.extend(f"- {reason}: {count}" for reason, count in sorted(reasons.items()))
    lines.extend(
        [
            "",
            "Review focus:",
            "1. Mark false boxes, missed small workers, and wrong violation classes.",
            "2. Treat no_helmet/no_vest as suspicious until manually confirmed.",
            "3. Do not promote pseudo labels to training labels before this review.",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_error_review_package(
    dataset_root: Path,
    label_root: Path,
    output_root: Path,
    sample_size: int,
) -> list[dict[str, Any]]:
    if output_root.exists():
        raise FileExistsError(f"Output already exists: {output_root}")
    output_root.mkdir(parents=True)
    enriched = enrich_records(dataset_root, label_root)
    selected = select_review_records(enriched, sample_size)
    copied = copy_review_records(selected, output_root)
    fieldnames = list(copied[0].keys()) if copied else []
    if fieldnames:
        write_csv(output_root / "review_samples.csv", copied, fieldnames)
    write_readme(output_root, copied)
    return copied


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--label-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-size", type=int, default=240)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    records = create_error_review_package(args.dataset, args.label_root, args.output, args.sample_size)
    reasons = Counter(str(row["review_reason"]) for row in records)
    print(f"Created error review package: {args.output}")
    print(f"Samples: {len(records)}")
    print(dict(sorted(reasons.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
