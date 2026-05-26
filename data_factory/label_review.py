#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare human label review workspaces and promote corrected labels to YOLO datasets."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_CLASS_NAMES = ["person", "head", "helmet", "vest", "no_helmet", "no_vest"]


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


def create_review_workspace(
    priority_package: Path,
    output_root: Path,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Copy a priority label-fix package into an editable human-review workspace."""
    manifest_path = priority_package / "priority_label_fix.csv"
    image_root = priority_package / "images"
    pseudo_label_root = priority_package / "labels_pseudo"
    rows = read_csv(manifest_path)

    ensure_fresh_output(output_root, force=force)
    images_out = output_root / "images"
    reviewed_labels_out = output_root / "labels_reviewed"
    original_labels_out = output_root / "labels_pseudo_original"
    images_out.mkdir()
    reviewed_labels_out.mkdir()
    original_labels_out.mkdir()

    copied: list[dict[str, Any]] = []
    file_list: list[str] = []
    for row in rows:
        image_name = row["image_name"]
        label_name = row.get("label_name") or f"{Path(image_name).stem}.txt"
        image_source = image_root / image_name
        label_source = pseudo_label_root / label_name
        image_target = images_out / image_name
        reviewed_label_target = reviewed_labels_out / label_name
        original_label_target = original_labels_out / label_name

        shutil.copy2(image_source, image_target)
        if label_source.exists():
            shutil.copy2(label_source, reviewed_label_target)
            shutil.copy2(label_source, original_label_target)
        else:
            reviewed_label_target.write_text("", encoding="utf-8")
            original_label_target.write_text("", encoding="utf-8")

        updated = dict(row)
        updated["manual_status"] = row.get("manual_status") or "todo"
        updated["manual_notes"] = row.get("manual_notes") or ""
        updated["local_image_path"] = str(image_target)
        updated["reviewed_label_path"] = str(reviewed_label_target)
        updated["pseudo_original_label_path"] = str(original_label_target)
        copied.append(updated)
        file_list.append(str(image_target))

    fieldnames = merge_fieldnames(
        copied,
        ["manual_status", "manual_notes", "local_image_path", "reviewed_label_path", "pseudo_original_label_path"],
    )
    write_csv(output_root / "labeling_queue.csv", copied, fieldnames)
    (output_root / "labelimg_file_list.txt").write_text("\n".join(file_list) + "\n", encoding="utf-8")
    write_review_workspace_readme(output_root, priority_package, copied)
    return copied


def write_review_workspace_readme(
    output_root: Path,
    priority_package: Path,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    lines = [
        "# Label Review Workspace",
        "",
        f"- Source priority package: {priority_package}",
        f"- Images to review: {len(rows)}",
        "",
        "Folders:",
        "",
        "- `images/`: images used for manual review.",
        "- `labels_reviewed/`: editable YOLO labels. Start here when correcting labels.",
        "- `labels_pseudo_original/`: immutable pseudo-label baseline for comparison.",
        "- `labeling_queue.csv`: review queue and status table.",
        "",
        "Review rules:",
        "",
        "1. Correct `person`, `helmet`, and visible `vest` first.",
        "2. Do not mark tiny or unclear PPE by guessing.",
        "3. Set `manual_status` to `done` after a sample is corrected.",
        "4. Use `manual_notes` for unclear face, tiny helmet, occlusion, or low-signal frames.",
        "",
        "After correction, run:",
        "",
        "```powershell",
        "python -m data_factory.label_review promote --review-workspace <this_folder> --output <reviewed_dataset> --require-status done",
        "```",
    ]
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def sort_rows_for_split(rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    def key(row: Mapping[str, str]) -> tuple[int, str]:
        try:
            rank = int(float(str(row.get("priority_rank", "0"))))
        except ValueError:
            rank = 0
        return rank, str(row.get("image_name", ""))

    return sorted(rows, key=key)


def split_rows(
    rows: Sequence[dict[str, str]],
    val_ratio: float,
    test_ratio: float,
) -> list[tuple[str, dict[str, str]]]:
    if val_ratio < 0 or test_ratio < 0 or val_ratio + test_ratio >= 1:
        raise ValueError("val_ratio and test_ratio must be non-negative and sum to less than 1")

    sorted_rows = sort_rows_for_split(rows)
    total = len(sorted_rows)
    test_count = round(total * test_ratio)
    val_count = round(total * val_ratio)
    train_count = total - val_count - test_count

    split_records: list[tuple[str, dict[str, str]]] = []
    for index, row in enumerate(sorted_rows):
        if index < train_count:
            split = "train"
        elif index < train_count + val_count:
            split = "val"
        else:
            split = "test"
        split_records.append((split, row))
    return split_records


def filter_rows_by_status(
    rows: Sequence[dict[str, str]],
    required_statuses: Sequence[str] | None,
) -> list[dict[str, str]]:
    if not required_statuses:
        return list(rows)
    allowed = {status.strip().lower() for status in required_statuses if status.strip()}
    return [row for row in rows if str(row.get("manual_status", "")).strip().lower() in allowed]


def write_data_yaml(output_root: Path, class_names: Sequence[str]) -> None:
    lines = [
        f"path: {output_root.as_posix()}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        f"nc: {len(class_names)}",
        "names:",
    ]
    lines.extend(f"  {index}: {name}" for index, name in enumerate(class_names))
    (output_root / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def promote_reviewed_dataset(
    review_workspace: Path,
    output_root: Path,
    val_ratio: float = 0.15,
    test_ratio: float = 0.10,
    required_statuses: Sequence[str] | None = None,
    class_names: Sequence[str] = DEFAULT_CLASS_NAMES,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Copy reviewed labels into a YOLO train/val/test dataset."""
    rows = filter_rows_by_status(read_csv(review_workspace / "labeling_queue.csv"), required_statuses)
    if not rows:
        raise ValueError("No rows selected for promotion")

    ensure_fresh_output(output_root, force=force)
    for split in ("train", "val", "test"):
        (output_root / "images" / split).mkdir(parents=True)
        (output_root / "labels" / split).mkdir(parents=True)

    copied: list[dict[str, Any]] = []
    for split, row in split_rows(rows, val_ratio=val_ratio, test_ratio=test_ratio):
        image_name = row["image_name"]
        label_name = row.get("label_name") or f"{Path(image_name).stem}.txt"
        image_source = review_workspace / "images" / image_name
        label_source = review_workspace / "labels_reviewed" / label_name
        image_target = output_root / "images" / split / image_name
        label_target = output_root / "labels" / split / label_name

        shutil.copy2(image_source, image_target)
        if label_source.exists():
            shutil.copy2(label_source, label_target)
        else:
            label_target.write_text("", encoding="utf-8")

        updated = dict(row)
        updated["split"] = split
        updated["dataset_image_path"] = str(image_target)
        updated["dataset_label_path"] = str(label_target)
        copied.append(updated)

    fieldnames = merge_fieldnames(copied, ["split", "dataset_image_path", "dataset_label_path"])
    write_csv(output_root / "manifest.csv", copied, fieldnames)
    write_data_yaml(output_root, class_names)
    write_promoted_readme(output_root, review_workspace, copied)
    return copied


def write_promoted_readme(
    output_root: Path,
    review_workspace: Path,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    split_counts = {split: sum(row.get("split") == split for row in rows) for split in ("train", "val", "test")}
    lines = [
        "# Reviewed YOLO Dataset",
        "",
        f"- Source review workspace: {review_workspace}",
        f"- Total images: {len(rows)}",
        "",
        "Split counts:",
    ]
    lines.extend(f"- {split}: {count}" for split, count in split_counts.items())
    lines.extend(
        [
            "",
            "Use `data.yaml` as the Ultralytics training config.",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_classes(raw: str) -> list[str]:
    classes = [item.strip() for item in raw.split(",") if item.strip()]
    if not classes:
        raise ValueError("at least one class is required")
    return classes


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    workspace = subparsers.add_parser("workspace", help="create an editable label review workspace")
    workspace.add_argument("--priority-package", required=True, type=Path)
    workspace.add_argument("--output", required=True, type=Path)
    workspace.add_argument("--force", action="store_true")

    promote = subparsers.add_parser("promote", help="promote reviewed labels into a YOLO dataset")
    promote.add_argument("--review-workspace", required=True, type=Path)
    promote.add_argument("--output", required=True, type=Path)
    promote.add_argument("--val-ratio", type=float, default=0.15)
    promote.add_argument("--test-ratio", type=float, default=0.10)
    promote.add_argument("--require-status", action="append", default=[])
    promote.add_argument("--classes", default=",".join(DEFAULT_CLASS_NAMES))
    promote.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        if args.command == "workspace":
            rows = create_review_workspace(args.priority_package, args.output, force=args.force)
            print(f"Created label review workspace: {args.output}")
            print(f"Samples: {len(rows)}")
            return 0
        if args.command == "promote":
            rows = promote_reviewed_dataset(
                review_workspace=args.review_workspace,
                output_root=args.output,
                val_ratio=args.val_ratio,
                test_ratio=args.test_ratio,
                required_statuses=args.require_status,
                class_names=parse_classes(args.classes),
                force=args.force,
            )
            print(f"Created reviewed YOLO dataset: {args.output}")
            print(f"Samples: {len(rows)}")
            return 0
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"label_review error: {exc}", file=sys.stderr)
        return 2
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
