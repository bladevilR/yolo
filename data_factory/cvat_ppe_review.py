#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only CVAT snapshot and review-manifest helpers for station PPE training."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


CLASS_NAMES = ["person", "helmet", "vest"]
BLOCKING_QC_ISSUES = {
    "missing_label_file",
    "malformed_row",
    "invalid_class",
    "non_positive_box",
    "duplicate_box",
}
QC_FLAG_ORDER = [
    "missing_label_file",
    "malformed_row",
    "invalid_class",
    "non_positive_box",
    "duplicate_box",
    "orphan_ppe_box",
    "empty_label",
]


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def merge_fieldnames(rows: Sequence[Mapping[str, Any]], preferred: Sequence[str]) -> list[str]:
    names = list(preferred)
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def ensure_safe_snapshot_output(output_root: Path, dataset_root: Path | None = None) -> Path:
    output_root = output_root.resolve()
    if dataset_root is not None:
        live_import_dir = (dataset_root / "cvat_import").resolve()
        if output_root == live_import_dir or live_import_dir in output_root.parents:
            raise ValueError(f"Refusing to write snapshot inside live CVAT import directory: {output_root}")
    elif "cvat_import" in [part.lower() for part in output_root.parts]:
        raise ValueError(f"Refusing to write snapshot inside a cvat_import directory: {output_root}")

    if output_root.exists():
        raise FileExistsError(f"Snapshot output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    return output_root


def normalize_labels(raw_labels: Sequence[Any]) -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    for raw in raw_labels:
        if isinstance(raw, Mapping):
            label_id = raw.get("id") or raw.get("label_id")
            name = raw.get("name")
        else:
            label_id, name = raw[0], raw[1]
        labels.append({"id": int(label_id), "name": str(name)})
    return labels


def normalize_frames(raw_frames: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    for index, frame in enumerate(raw_frames):
        frames.append(
            {
                "frame_index": index,
                "name": str(frame.get("name", "")),
                "width": int(frame.get("width", 0)),
                "height": int(frame.get("height", 0)),
            }
        )
    return frames


def annotation_shapes(export_data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    annotations = export_data.get("annotations", {})
    if isinstance(annotations, Mapping):
        shapes = annotations.get("shapes", [])
    else:
        shapes = []
    return list(shapes or export_data.get("shapes", []) or [])


def label_id_to_class_id(labels: Sequence[Mapping[str, Any]]) -> dict[int, int]:
    name_to_class = {name: index for index, name in enumerate(CLASS_NAMES)}
    return {
        int(label["id"]): name_to_class[str(label["name"])]
        for label in labels
        if str(label["name"]) in name_to_class
    }


def shape_is_rectangle(shape: Mapping[str, Any]) -> bool:
    shape_type = str(shape.get("type", "")).lower()
    return shape_type.endswith("rectangle") or shape_type == "shape_type.rectangle"


def yolo_line_from_points(class_id: int, points: Sequence[float], image_width: int, image_height: int) -> str | None:
    if len(points) < 4 or image_width <= 0 or image_height <= 0:
        return None
    x1, y1, x2, y2 = [float(value) for value in points[:4]]
    x1, x2 = sorted((max(0.0, min(float(image_width), x1)), max(0.0, min(float(image_width), x2))))
    y1, y2 = sorted((max(0.0, min(float(image_height), y1)), max(0.0, min(float(image_height), y2))))
    width = x2 - x1
    height = y2 - y1
    if width <= 0 or height <= 0:
        return None
    x_center = (x1 + x2) / 2.0 / image_width
    y_center = (y1 + y2) / 2.0 / image_height
    return f"{class_id} {x_center:.8f} {y_center:.8f} {width / image_width:.8f} {height / image_height:.8f}"


def class_count_template() -> dict[str, int]:
    return {name: 0 for name in CLASS_NAMES}


def write_snapshot_from_export(
    export_data: Mapping[str, Any],
    output_root: Path,
    snapshot_id: str,
    historical_backup_path: Path | None = None,
    source_url: str = "",
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    output_root = ensure_safe_snapshot_output(output_root, dataset_root=dataset_root)
    labels = normalize_labels(export_data.get("labels", []))
    frames = normalize_frames(export_data.get("frames", []))
    class_by_label_id = label_id_to_class_id(labels)

    output_root.mkdir(parents=True)
    labels_dir = output_root / "labels_yolo"
    labels_dir.mkdir()
    backup_path = output_root / "annotations_backup.json"
    write_json(backup_path, dict(export_data))

    labels_by_frame: dict[int, list[str]] = defaultdict(list)
    for shape in annotation_shapes(export_data):
        if not shape_is_rectangle(shape) or bool(shape.get("outside", False)):
            continue
        label_id = int(shape.get("label_id", -1))
        class_id = class_by_label_id.get(label_id)
        frame_index = int(shape.get("frame", -1))
        if class_id is None or frame_index < 0 or frame_index >= len(frames):
            continue
        frame = frames[frame_index]
        line = yolo_line_from_points(class_id, shape.get("points", []), frame["width"], frame["height"])
        if line is not None:
            labels_by_frame[frame_index].append(line)

    class_counts = Counter({name: 0 for name in CLASS_NAMES})
    frame_summaries: list[dict[str, Any]] = []
    for frame in frames:
        frame_index = int(frame["frame_index"])
        image_name = frame["name"]
        label_name = f"{Path(image_name).stem}.txt"
        lines = labels_by_frame.get(frame_index, [])
        label_path = labels_dir / label_name
        label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

        per_frame_counts = Counter({name: 0 for name in CLASS_NAMES})
        for line in lines:
            class_id = int(line.split()[0])
            class_name = CLASS_NAMES[class_id]
            class_counts[class_name] += 1
            per_frame_counts[class_name] += 1
        frame_summaries.append(
            {
                "frame_index": frame_index,
                "image_name": image_name,
                "label_name": label_name,
                "width": frame["width"],
                "height": frame["height"],
                "box_count": len(lines),
                "class_counts": dict(per_frame_counts),
            }
        )

    historical_backups: list[dict[str, Any]] = []
    if historical_backup_path is not None:
        historical_backups.append(
            {
                "path": str(historical_backup_path),
                "exists": historical_backup_path.exists(),
                "purpose": "historical_user_manual_work_backup",
            }
        )

    manifest = {
        "snapshot_id": snapshot_id,
        "task_id": export_data.get("task_id", ""),
        "source_url": source_url,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "class_map": {str(index): name for index, name in enumerate(CLASS_NAMES)},
        "cvat_labels": labels,
        "frame_count": len(frames),
        "label_file_count": len(frames),
        "box_count": sum(len(lines) for lines in labels_by_frame.values()),
        "empty_label_files": sum(1 for frame in frames if not labels_by_frame.get(int(frame["frame_index"]))),
        "class_counts": dict(class_counts),
        "paths": {
            "snapshot_root": str(output_root),
            "annotations_backup": str(backup_path),
            "labels_yolo": str(labels_dir),
            "snapshot_manifest": str(output_root / "snapshot_manifest.json"),
        },
        "historical_backups": historical_backups,
        "frames": frame_summaries,
    }
    write_json(output_root / "snapshot_manifest.json", manifest)
    return manifest


def _model_to_plain(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_model_to_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_model_to_plain(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _model_to_plain(item) for key, item in value.items()}
    for method in ("model_dump", "to_dict", "dict"):
        if hasattr(value, method):
            try:
                return _model_to_plain(getattr(value, method)())
            except TypeError:
                continue
    if hasattr(value, "__dict__"):
        return {
            key: _model_to_plain(item)
            for key, item in value.__dict__.items()
            if not key.startswith("_")
        }
    return str(value)


def export_cvat_task_to_dict(host: str, username: str, password: str, task_id: int) -> dict[str, Any]:
    from cvat_sdk import make_client

    with make_client(host, credentials=(username, password)) as client:
        task = client.tasks.retrieve(task_id)
        meta = task.get_meta()
        labels = [{"id": int(label.id), "name": str(label.name)} for label in task.get_labels()]
        frames = [
            {
                "name": str(frame.name),
                "width": int(frame.width),
                "height": int(frame.height),
                "related_files": getattr(frame, "related_files", 0),
            }
            for frame in meta.frames
        ]
        annotations = task.get_annotations()
        return {
            "task_id": task_id,
            "labels": labels,
            "frames": frames,
            "annotations": {
                "version": _model_to_plain(getattr(annotations, "version", 0)),
                "tags": _model_to_plain(getattr(annotations, "tags", [])),
                "shapes": _model_to_plain(getattr(annotations, "shapes", [])),
                "tracks": _model_to_plain(getattr(annotations, "tracks", [])),
                "intervals": _model_to_plain(getattr(annotations, "intervals", [])),
            },
        }


def issue_counts_from_summary(qc_summary: Mapping[str, Any]) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for issue in qc_summary.get("issues", []):
        image_name = str(issue.get("image_name", ""))
        issue_type = str(issue.get("issue", ""))
        if image_name and issue_type:
            counts[image_name][issue_type] += 1
    return counts


def image_details_from_summary(qc_summary: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item.get("image_name", "")): item for item in qc_summary.get("images", [])}


def contact_sheet_path(qc_root: Path, frame_index: int, per_sheet: int = 12) -> Path:
    sheet_index = frame_index // per_sheet + 1
    return qc_root / "contact_sheets" / f"boxed_contact_sheet_{sheet_index:03d}.jpg"


def seed_review_manifest(
    snapshot_manifest: Mapping[str, Any],
    qc_summary_path: Path | None,
    output_csv: Path,
    reviewer: str = "",
    review_date: str = "",
) -> list[dict[str, Any]]:
    qc_summary = read_json(qc_summary_path) if qc_summary_path is not None and qc_summary_path.exists() else {}
    issue_counts = issue_counts_from_summary(qc_summary)
    image_details = image_details_from_summary(qc_summary)
    qc_root = qc_summary_path.parent if qc_summary_path is not None else Path("")

    rows: list[dict[str, Any]] = []
    for frame in snapshot_manifest.get("frames", []):
        image_name = str(frame["image_name"])
        label_name = str(frame["label_name"])
        counts = issue_counts.get(image_name, Counter())
        image_detail = image_details.get(image_name, {})
        is_empty_label = int(frame.get("box_count", 0)) == 0 or int(image_detail.get("detections", -1)) == 0
        flags = [flag for flag in QC_FLAG_ORDER if counts.get(flag, 0) > 0]
        if is_empty_label:
            flags.append("empty_label")

        row = {
            "snapshot_id": snapshot_manifest.get("snapshot_id", ""),
            "frame_index": frame.get("frame_index", ""),
            "image_name": image_name,
            "label_name": label_name,
            "image_width": frame.get("width", ""),
            "image_height": frame.get("height", ""),
            "box_count": frame.get("box_count", 0),
            "person_count": frame.get("class_counts", {}).get("person", 0),
            "helmet_count": frame.get("class_counts", {}).get("helmet", 0),
            "vest_count": frame.get("class_counts", {}).get("vest", 0),
            "manual_status": "todo",
            "manual_decision": "",
            "reviewer": reviewer,
            "review_date": review_date,
            "sample_profile": "normal_pending_review",
            "qc_flags": "|".join(flags),
            "qc_issue_count": sum(counts.values()) + (1 if is_empty_label else 0),
            "missing_label_file_count": counts.get("missing_label_file", 0),
            "malformed_row_count": counts.get("malformed_row", 0),
            "invalid_class_count": counts.get("invalid_class", 0),
            "non_positive_box_count": counts.get("non_positive_box", 0),
            "duplicate_box_count": counts.get("duplicate_box", 0),
            "orphan_ppe_box_count": counts.get("orphan_ppe_box", 0),
            "empty_label_count": 1 if is_empty_label else 0,
            "promotion_gate": "blocked_manual_status_done_required",
            "overlay_path": str(qc_root / "overlays" / image_name) if qc_root != Path("") else "",
            "contact_sheet_path": str(contact_sheet_path(qc_root, int(frame.get("frame_index", 0)))) if qc_root != Path("") else "",
            "notes": "",
        }
        rows.append(row)

    preferred = [
        "snapshot_id",
        "frame_index",
        "image_name",
        "label_name",
        "image_width",
        "image_height",
        "box_count",
        "person_count",
        "helmet_count",
        "vest_count",
        "manual_status",
        "manual_decision",
        "reviewer",
        "review_date",
        "sample_profile",
        "qc_flags",
        "qc_issue_count",
        "missing_label_file_count",
        "malformed_row_count",
        "invalid_class_count",
        "non_positive_box_count",
        "duplicate_box_count",
        "orphan_ppe_box_count",
        "empty_label_count",
        "promotion_gate",
        "overlay_path",
        "contact_sheet_path",
        "notes",
    ]
    write_csv(output_csv, rows, preferred)
    return rows


def recommended_action(issue_type: str) -> str:
    return {
        "duplicate_box": "Check whether this is a duplicate same-class box; remove or merge in CVAT if confirmed.",
        "orphan_ppe_box": "Check whether the PPE box belongs to a visible person; fix association by editing boxes or remove if false.",
        "empty_label": "Confirm this frame truly has no visible person, helmet, or vest; otherwise add missing boxes in CVAT.",
        "missing_label_file": "Create or export the missing label after confirming the frame status.",
        "malformed_row": "Fix malformed YOLO row by correcting the source annotation.",
        "invalid_class": "Map annotation back to person, helmet, or vest only.",
        "non_positive_box": "Fix or delete zero-area annotation.",
    }.get(issue_type, "Review and resolve this QC issue in CVAT before promotion.")


def issue_priority(issue_type: str) -> int:
    return {
        "missing_label_file": 10,
        "malformed_row": 11,
        "invalid_class": 12,
        "non_positive_box": 13,
        "duplicate_box": 20,
        "orphan_ppe_box": 30,
        "empty_label": 40,
    }.get(issue_type, 90)


def build_qc_review_queue(
    manifest_rows: Sequence[Mapping[str, Any]],
    qc_summary_path: Path,
    output_csv: Path,
) -> list[dict[str, Any]]:
    qc_summary = read_json(qc_summary_path)
    manifest_by_image = {str(row["image_name"]): row for row in manifest_rows}
    rows: list[dict[str, Any]] = []

    for issue in qc_summary.get("issues", []):
        issue_type = str(issue.get("issue", ""))
        image_name = str(issue.get("image_name", ""))
        manifest = manifest_by_image.get(image_name, {})
        rows.append(
            {
                "image_name": image_name,
                "label_name": issue.get("label_name", manifest.get("label_name", "")),
                "issue_type": issue_type,
                "issue_count": 1,
                "detection_index": issue.get("detection_index", ""),
                "priority": issue_priority(issue_type),
                "recommended_action": recommended_action(issue_type),
                "manual_status": "todo",
                "manual_decision": "",
                "reviewer": "",
                "review_date": "",
                "overlay_path": manifest.get("overlay_path", ""),
                "contact_sheet_path": manifest.get("contact_sheet_path", ""),
                "notes": "",
            }
        )

    for manifest in manifest_rows:
        if int(manifest.get("empty_label_count", 0) or 0) <= 0:
            continue
        rows.append(
            {
                "image_name": manifest.get("image_name", ""),
                "label_name": manifest.get("label_name", ""),
                "issue_type": "empty_label",
                "issue_count": 1,
                "detection_index": "",
                "priority": issue_priority("empty_label"),
                "recommended_action": recommended_action("empty_label"),
                "manual_status": "todo",
                "manual_decision": "",
                "reviewer": "",
                "review_date": "",
                "overlay_path": manifest.get("overlay_path", ""),
                "contact_sheet_path": manifest.get("contact_sheet_path", ""),
                "notes": "",
            }
        )

    rows = sorted(rows, key=lambda row: (int(row["priority"]), str(row["image_name"]), str(row.get("detection_index", ""))))
    for index, row in enumerate(rows, start=1):
        row["review_id"] = f"qc{index:04d}"

    preferred = [
        "review_id",
        "priority",
        "image_name",
        "label_name",
        "issue_type",
        "issue_count",
        "detection_index",
        "recommended_action",
        "manual_status",
        "manual_decision",
        "reviewer",
        "review_date",
        "overlay_path",
        "contact_sheet_path",
        "notes",
    ]
    write_csv(output_csv, rows, preferred)
    return rows


def write_cvat_review_instructions(
    output_path: Path,
    snapshot_manifest: Mapping[str, Any],
    review_queue_path: Path,
) -> None:
    lines = [
        "# CVAT Station PPE Review Instructions",
        "",
        f"- Snapshot ID: `{snapshot_manifest.get('snapshot_id', '')}`",
        f"- Source URL: `{snapshot_manifest.get('source_url', '')}`",
        f"- Review queue: `{review_queue_path}`",
        f"- Images: {snapshot_manifest.get('frame_count', 0)}",
        f"- Boxes: {snapshot_manifest.get('box_count', 0)}",
        "",
        "## Required status values",
        "",
        "- `manual_status=done`: labels are human-reviewed and may be promoted after QC gates pass.",
        "- `manual_status=skip`: image should not be used for training or normal metrics.",
        "- `manual_status=stress-only`: image is useful for hard-negative, many-box, tiny, edge, occluded, or clutter stress reporting.",
        "- Leave `manual_status=todo` until the image has been reviewed in CVAT.",
        "",
        "## Review decisions",
        "",
        "- `hard_negative`: false-person sources such as bags, covers, pipes, extinguishers, materials, or clutter were corrected.",
        "- `visible_vest`: visible vest labels were checked or corrected.",
        "- `partial_worker`: partial worker boxes were checked.",
        "- `tiny_worker`: tiny worker labels were checked and should usually be stress-tagged if unstable.",
        "- `unclear`: sample is too ambiguous; use `skip` unless it is intentionally stress-only.",
        "",
        "## Label rules",
        "",
        "- Detector classes remain exactly `person`, `helmet`, and visible `vest`.",
        "- Do not create `no_helmet` or `no_vest` boxes; those are event-layer states.",
        "- Resolve duplicate boxes by keeping one correct box per object.",
        "- Resolve orphan PPE by attaching it spatially to the correct visible worker or deleting false PPE boxes.",
        "",
        "Promotion is intentionally paused until this manifest is returned with explicit review statuses.",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

