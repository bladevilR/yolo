#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only CVAT snapshot, manifest, and QC review queue CLI for station PPE."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_factory.cvat_ppe_review import (
    build_qc_review_queue,
    export_cvat_task_to_dict,
    read_json,
    seed_review_manifest,
    write_cvat_review_instructions,
    write_json,
    write_snapshot_from_export,
)


DEFAULT_ROOT = Path(r"E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1")
DEFAULT_HISTORICAL_BACKUP = (
    DEFAULT_ROOT
    / "cvat_import"
    / "task1_manual_121_backup_before_supervision_20260522_104756.json"
)


def default_snapshot_id(task_id: int) -> str:
    return f"task{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def add_common_snapshot_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--snapshot-id")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--historical-backup", type=Path, default=DEFAULT_HISTORICAL_BACKUP)
    parser.add_argument("--source-url", default="http://localhost:8080/tasks/1/jobs/1")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export", help="export current CVAT task read-only into a timestamped snapshot")
    export.add_argument("--host", default="http://localhost:8080")
    export.add_argument("--username", default="admin")
    export.add_argument("--password", default="StationPPE@2026")
    export.add_argument("--task-id", type=int, default=1)
    add_common_snapshot_args(export)

    backup = subparsers.add_parser("from-backup", help="build a snapshot from an existing CVAT backup JSON")
    backup.add_argument("--backup-json", required=True, type=Path)
    backup.add_argument("--task-id", type=int, default=1)
    add_common_snapshot_args(backup)

    manifest = subparsers.add_parser("manifest", help="seed review manifest from snapshot and supervision QC summary")
    manifest.add_argument("--snapshot-manifest", required=True, type=Path)
    manifest.add_argument("--qc-summary", required=True, type=Path)
    manifest.add_argument("--output", required=True, type=Path)

    queue = subparsers.add_parser("queue", help="build QC review queue from manifest and supervision QC summary")
    queue.add_argument("--review-manifest", required=True, type=Path)
    queue.add_argument("--qc-summary", required=True, type=Path)
    queue.add_argument("--output", required=True, type=Path)

    instructions = subparsers.add_parser("instructions", help="write human CVAT review instructions")
    instructions.add_argument("--snapshot-manifest", required=True, type=Path)
    instructions.add_argument("--review-queue", required=True, type=Path)
    instructions.add_argument("--output", required=True, type=Path)
    return parser


def snapshot_output(args: argparse.Namespace, task_id: int) -> tuple[str, Path]:
    snapshot_id = args.snapshot_id or default_snapshot_id(task_id)
    output = args.output or (args.dataset_root / "cvat_snapshots" / snapshot_id)
    return snapshot_id, output


def read_manifest_csv(path: Path) -> list[dict[str, str]]:
    import csv

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.command == "export":
        snapshot_id, output = snapshot_output(args, args.task_id)
        data = export_cvat_task_to_dict(args.host, args.username, args.password, args.task_id)
        manifest = write_snapshot_from_export(
            data,
            output,
            snapshot_id=snapshot_id,
            historical_backup_path=args.historical_backup,
            source_url=args.source_url,
            dataset_root=args.dataset_root,
        )
        print(f"Wrote CVAT snapshot: {output}")
        print(f"Frames: {manifest['frame_count']} Boxes: {manifest['box_count']}")
        return 0

    if args.command == "from-backup":
        snapshot_id, output = snapshot_output(args, args.task_id)
        data = read_json(args.backup_json)
        manifest = write_snapshot_from_export(
            data,
            output,
            snapshot_id=snapshot_id,
            historical_backup_path=args.historical_backup,
            source_url=args.source_url,
            dataset_root=args.dataset_root,
        )
        print(f"Wrote backup-derived snapshot: {output}")
        print(f"Frames: {manifest['frame_count']} Boxes: {manifest['box_count']}")
        return 0

    if args.command == "manifest":
        snapshot_manifest = read_json(args.snapshot_manifest)
        rows = seed_review_manifest(snapshot_manifest, args.qc_summary, args.output)
        print(f"Wrote review manifest: {args.output}")
        print(f"Rows: {len(rows)}")
        return 0

    if args.command == "queue":
        rows = build_qc_review_queue(read_manifest_csv(args.review_manifest), args.qc_summary, args.output)
        print(f"Wrote QC review queue: {args.output}")
        print(f"Rows: {len(rows)}")
        return 0

    if args.command == "instructions":
        write_cvat_review_instructions(args.output, read_json(args.snapshot_manifest), args.review_queue)
        print(f"Wrote review instructions: {args.output}")
        return 0

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
