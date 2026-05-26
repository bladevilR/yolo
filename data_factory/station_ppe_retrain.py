#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare station PPE acceptance-oriented retraining review artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence


CLASS_MAP_3 = {0: "person", 1: "helmet", 2: "vest"}
SIX_TO_THREE_CLASS_MAP = {0: 0, 2: 1, 3: 2}
THREE_CLASS_IDS = {0, 1, 2}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
DEFAULT_SPLITS = ("train", "val", "test")

CANDIDATE_FIELDS = [
    "candidate_id",
    "source_queue",
    "source_row_id",
    "image_name",
    "label_name",
    "source_video",
    "frame_index",
    "timestamp_seconds",
    "profile",
    "review_reason",
    "recommendation",
    "review_intent",
    "recommended_pool",
    "manual_status",
    "manual_decision",
    "reviewer",
    "review_date",
    "label_source",
    "eligible_for_v3_training",
    "promotion_gate",
    "local_image_path",
    "source_image_path",
    "source_label_path",
    "current_label_path",
    "reviewed_label_path",
    "pseudo_original_label_path",
    "crop_path",
    "qc_flags",
    "status",
    "queue_source",
    "codex_suggested_decision",
    "codex_review_priority",
    "codex_visual_note",
    "notes",
]


@dataclass(frozen=True)
class CandidatePackage:
    rows: list[dict[str, Any]]
    summary: dict[str, Any]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def safe_int(raw: Any, default: int = 0) -> int:
    try:
        return int(float(str(raw)))
    except (TypeError, ValueError):
        return default


def path_name(raw: Any) -> str:
    value = str(raw or "").strip()
    return Path(value).name if value else ""


def status_is_done(status: str) -> bool:
    return status.strip().lower() == "done"


def ensure_new_output(output_root: Path) -> None:
    if output_root.exists():
        raise FileExistsError(f"Output already exists: {output_root}")
    output_root.mkdir(parents=True)


def class_count_template(class_map: Mapping[int, str]) -> dict[str, int]:
    return {class_map[index]: 0 for index in sorted(class_map)}


def split_names(dataset_root: Path) -> list[str]:
    names: list[str] = []
    for split in DEFAULT_SPLITS:
        if (dataset_root / "images" / split).exists() or (dataset_root / "labels" / split).exists():
            names.append(split)
    extra_roots = [dataset_root / "images", dataset_root / "labels"]
    for root in extra_roots:
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.is_dir() and child.name not in names:
                names.append(child.name)
    return names or list(DEFAULT_SPLITS)


def image_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.iterdir() if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES)


def label_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.iterdir() if item.is_file() and item.suffix.lower() == ".txt")


def count_yolo_dataset(dataset_root: Path, class_map: Mapping[int, str]) -> dict[str, Any]:
    """Count images, labels, class instances, and obvious label issues."""
    splits = split_names(dataset_root)
    image_counts: dict[str, int] = {}
    label_file_counts: dict[str, int] = {}
    empty_label_files: dict[str, int] = {}
    class_counts = class_count_template(class_map)
    class_counts_by_split: dict[str, dict[str, int]] = {}
    invalid_labels: list[dict[str, str]] = []
    missing_label_files: list[str] = []
    orphan_label_files: list[str] = []

    for split in splits:
        split_images = image_files(dataset_root / "images" / split)
        split_labels = label_files(dataset_root / "labels" / split)
        image_counts[split] = len(split_images)
        label_file_counts[split] = len(split_labels)
        empty_label_files[split] = 0
        class_counts_by_split[split] = class_count_template(class_map)

        image_stems = {path.stem for path in split_images}
        label_stems = {path.stem for path in split_labels}
        missing_label_files.extend(str(path) for path in split_images if path.stem not in label_stems)
        orphan_label_files.extend(str(path) for path in split_labels if path.stem not in image_stems)

        for label_path in split_labels:
            text = label_path.read_text(encoding="utf-8").strip()
            if not text:
                empty_label_files[split] += 1
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                parts = stripped.split()
                if len(parts) < 5:
                    invalid_labels.append(
                        {
                            "path": str(label_path),
                            "split": split,
                            "line": str(line_number),
                            "class_id": parts[0] if parts else "",
                            "reason": "malformed_yolo_row",
                        }
                    )
                    continue
                try:
                    class_id = int(parts[0])
                except ValueError:
                    invalid_labels.append(
                        {
                            "path": str(label_path),
                            "split": split,
                            "line": str(line_number),
                            "class_id": parts[0],
                            "reason": "non_integer_class_id",
                        }
                    )
                    continue
                class_name = class_map.get(class_id)
                if class_name is None:
                    invalid_labels.append(
                        {
                            "path": str(label_path),
                            "split": split,
                            "line": str(line_number),
                            "class_id": str(class_id),
                            "reason": "class_id_not_in_class_map",
                        }
                    )
                    continue
                class_counts[class_name] += 1
                class_counts_by_split[split][class_name] += 1

    return {
        "dataset_root": str(dataset_root),
        "image_counts": image_counts,
        "label_file_counts": label_file_counts,
        "empty_label_files": empty_label_files,
        "class_counts": class_counts,
        "class_counts_by_split": class_counts_by_split,
        "invalid_labels": invalid_labels,
        "missing_label_files": missing_label_files,
        "orphan_label_files": orphan_label_files,
    }


def review_pool_for_profile(profile: str) -> str:
    lowered = profile.lower()
    stress_tokens = ("hard", "many", "empty", "edge", "tiny", "occluded", "low")
    if any(token in lowered for token in stress_tokens):
        return "stress_pool"
    return "normal_pool"


def review_pool_for_v5(queue_source: str) -> str:
    if queue_source == "accepted_event":
        return "demo_review_pool"
    return "stress_pool"


def eligibility_fields(manual_status: str) -> tuple[str, str]:
    if status_is_done(manual_status):
        return "yes", "eligible_manual_status_done"
    return "no", "blocked_manual_status_done_required"


def add_unique_image(unique_images: set[str], image_name: str) -> None:
    key = image_name.strip().lower()
    if key:
        unique_images.add(key)


def add_seen_source_key(seen_source_keys: set[str], raw: Any) -> None:
    key = path_name(raw).lower()
    if key:
        seen_source_keys.add(key)


def parse_yolo_line(line: str) -> tuple[int, float, float, float, float] | None:
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
    return class_id, x, y, w, h


def convert_label_line_to_three_class(line: str, source_queue: str) -> str | None:
    parsed = parse_yolo_line(line)
    if parsed is None:
        return None
    class_id, x, y, w, h = parsed
    if source_queue == "v5_review_queue":
        if class_id not in THREE_CLASS_IDS:
            return None
        mapped = class_id
    else:
        mapped = SIX_TO_THREE_CLASS_MAP.get(class_id)
        if mapped is None:
            return None
    return f"{mapped} {x:.6f} {y:.6f} {w:.6f} {h:.6f}"


def convert_label_file_to_three_class(source_label: Path, output_label: Path, source_queue: str) -> int:
    lines: list[str] = []
    if source_label.exists():
        for line in source_label.read_text(encoding="utf-8").splitlines():
            converted = convert_label_line_to_three_class(line, source_queue)
            if converted is not None:
                lines.append(converted)
    output_label.parent.mkdir(parents=True, exist_ok=True)
    output_label.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def preferred_label_path(row: Mapping[str, Any]) -> Path | None:
    label_name = str(row.get("label_name", "") or f"{Path(str(row.get('image_name', ''))).stem}.txt")
    reviewed = Path(str(row.get("reviewed_label_path", "") or ""))
    if row.get("source_queue") == "v5_review_queue" and reviewed.name:
        draft = reviewed.parent.parent / "labels_codex_draft" / label_name
        if draft.exists():
            return draft
    for key in ("reviewed_label_path", "current_label_path", "pseudo_original_label_path", "source_label_path"):
        raw = str(row.get(key, "") or "").strip()
        if raw:
            return Path(raw)
    return None


def preferred_image_path(row: Mapping[str, Any]) -> Path:
    for key in ("local_image_path", "source_image_path"):
        raw = str(row.get(key, "") or "").strip()
        if raw:
            return Path(raw)
    raise FileNotFoundError(f"No image path for candidate {row.get('candidate_id', '')}")


def create_multimodal_draft_package(
    candidate_rows: Sequence[Mapping[str, Any]],
    output_root: Path,
    reviewer: str = "codex_multimodal_ai",
    review_date: str | None = None,
) -> dict[str, Any]:
    """Create a reversible AI-multimodal reviewed draft package from candidate rows."""
    ensure_new_output(output_root)
    images_out = output_root / "images"
    labels_out = output_root / "labels_codex_multimodal_3class"
    images_out.mkdir()
    labels_out.mkdir()

    selected_by_image: dict[str, Mapping[str, Any]] = {}
    candidate_counts_by_image: Counter[str] = Counter()
    for row in candidate_rows:
        image_name = str(row.get("image_name", "")).strip()
        if not image_name:
            continue
        key = image_name.lower()
        candidate_counts_by_image[key] += 1
        selected_by_image.setdefault(key, row)

    manifest_rows: list[dict[str, Any]] = []
    total_labels = 0
    for index, row in enumerate(selected_by_image.values(), start=1):
        source_image = preferred_image_path(row)
        if not source_image.exists():
            raise FileNotFoundError(f"Image not found: {source_image}")
        image_name = str(row.get("image_name") or source_image.name)
        label_name = str(row.get("label_name") or f"{Path(image_name).stem}.txt")
        target_image = images_out / image_name
        target_label = labels_out / label_name
        shutil.copy2(source_image, target_image)

        source_label = preferred_label_path(row)
        label_count = convert_label_file_to_three_class(source_label or Path("__missing__"), target_label, str(row.get("source_queue", "")))
        total_labels += label_count

        updated = {
            "draft_id": f"mm-{index:04d}",
            "source_candidate_id": row.get("candidate_id", ""),
            "source_queue": row.get("source_queue", ""),
            "source_candidate_rows_for_image": candidate_counts_by_image[image_name.lower()],
            "image_name": image_name,
            "label_name": label_name,
            "source_image_path": str(source_image),
            "source_label_path": str(source_label or ""),
            "draft_image_path": str(target_image),
            "draft_label_path": str(target_label),
            "manual_status": "codex_multimodal_reviewed",
            "eligible_for_v3_training": "no",
            "promotion_gate": "blocked_human_reviewer_confirmation_required",
            "reviewer": reviewer,
            "review_date": review_date or date.today().isoformat(),
            "label_source": "codex_multimodal_draft_3class",
            "profile": row.get("profile", ""),
            "recommended_pool": row.get("recommended_pool", ""),
            "codex_visual_note": row.get("codex_visual_note", ""),
            "notes": "AI multimodal draft; requires human verification before manual_status=done.",
            "draft_label_count": label_count,
        }
        manifest_rows.append(updated)

    manifest_fields = merge_fieldnames(
        manifest_rows,
        [
            "draft_id",
            "source_candidate_id",
            "source_queue",
            "source_candidate_rows_for_image",
            "image_name",
            "label_name",
            "source_image_path",
            "source_label_path",
            "draft_image_path",
            "draft_label_path",
            "manual_status",
            "eligible_for_v3_training",
            "promotion_gate",
            "reviewer",
            "review_date",
            "label_source",
            "profile",
            "recommended_pool",
            "codex_visual_note",
            "notes",
            "draft_label_count",
        ],
    )
    write_csv(output_root / "label_review_manifest.csv", manifest_rows, manifest_fields)
    write_csv(output_root / "candidate_rows_used.csv", candidate_rows, merge_fieldnames(candidate_rows, CANDIDATE_FIELDS))
    summary = {
        "generated_date": date.today().isoformat(),
        "candidate_rows": len(candidate_rows),
        "unique_images": len(manifest_rows),
        "total_draft_labels": total_labels,
        "manual_status": "codex_multimodal_reviewed",
        "eligible_rows": 0,
        "human_confirmation_required": len(manifest_rows),
    }
    (output_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_multimodal_draft_readme(output_root, summary)
    return summary


def write_multimodal_draft_readme(output_root: Path, summary: Mapping[str, Any]) -> None:
    lines = [
        "# Station PPE Codex Multimodal Draft Review",
        "",
        f"- Candidate rows consumed: {summary.get('candidate_rows', 0)}",
        f"- Unique images drafted: {summary.get('unique_images', 0)}",
        f"- Draft labels: {summary.get('total_draft_labels', 0)}",
        "- Manual status written: `codex_multimodal_reviewed`",
        "- Training eligibility: `no` until a human reviewer confirms and changes accepted rows to `manual_status=done`.",
        "",
        "Folders:",
        "",
        "- `images/`: copied unique review images.",
        "- `labels_codex_multimodal_3class/`: 3-class YOLO draft labels using `person`, `helmet`, `vest`.",
        "- `label_review_manifest.csv`: image-level draft manifest for human复核.",
        "- `candidate_rows_used.csv`: original candidate rows retained for traceability.",
        "",
        "Important:",
        "",
        "- This is an AI-assisted draft pass, not final human gold labels.",
        "- `no_helmet` and `no_vest` are not detector classes and are not written to labels.",
        "- The user should review overlays/crops, fix labels as needed, and only then mark approved samples `done`.",
    ]
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def priority_candidate(row: Mapping[str, str], index: int) -> dict[str, Any]:
    rank = safe_int(row.get("priority_rank"), index)
    manual_status = str(row.get("manual_status", "") or "todo")
    eligible, gate = eligibility_fields(manual_status)
    label_source = "human_reviewed" if eligible == "yes" else "codex_auto_reviewed"
    return {
        "candidate_id": f"priority-{rank:04d}",
        "source_queue": "priority_batch",
        "source_row_id": str(row.get("priority_rank") or index),
        "image_name": row.get("image_name", ""),
        "label_name": row.get("label_name", ""),
        "source_video": row.get("source_video", ""),
        "frame_index": row.get("frame_index", ""),
        "timestamp_seconds": row.get("timestamp_seconds", ""),
        "profile": row.get("profile", ""),
        "review_reason": row.get("priority_reason", ""),
        "recommendation": row.get("required_action", ""),
        "review_intent": "human_review_full_label",
        "recommended_pool": review_pool_for_profile(row.get("profile", "")),
        "manual_status": manual_status,
        "manual_decision": row.get("manual_decision", ""),
        "reviewer": "",
        "review_date": "",
        "label_source": label_source,
        "eligible_for_v3_training": eligible,
        "promotion_gate": gate,
        "local_image_path": row.get("local_image_path", ""),
        "source_image_path": row.get("source_image_path", ""),
        "source_label_path": row.get("source_label_path", ""),
        "current_label_path": row.get("pseudo_original_label_path", ""),
        "reviewed_label_path": row.get("reviewed_label_path", ""),
        "pseudo_original_label_path": row.get("pseudo_original_label_path", ""),
        "crop_path": "",
        "qc_flags": row.get("qc_flags", ""),
        "status": "",
        "queue_source": "",
        "codex_suggested_decision": "",
        "codex_review_priority": "",
        "codex_visual_note": row.get("visual_note", ""),
        "notes": row.get("manual_notes", ""),
    }


def v5_candidate(row: Mapping[str, str], index: int) -> dict[str, Any]:
    review_id = row.get("review_id") or f"q{index:04d}"
    manual_status = str(row.get("manual_status", "") or "todo")
    eligible, gate = eligibility_fields(manual_status)
    queue_source = row.get("queue_source", "")
    return {
        "candidate_id": f"v5-{review_id}",
        "source_queue": "v5_review_queue",
        "source_row_id": review_id,
        "image_name": row.get("image_name", ""),
        "label_name": row.get("label_name", ""),
        "source_video": "",
        "frame_index": "",
        "timestamp_seconds": "",
        "profile": queue_source,
        "review_reason": row.get("review_reason", ""),
        "recommendation": row.get("recommendation", ""),
        "review_intent": "event_error_review",
        "recommended_pool": review_pool_for_v5(queue_source),
        "manual_status": manual_status,
        "manual_decision": row.get("manual_decision", ""),
        "reviewer": "",
        "review_date": "",
        "label_source": "v5_review_queue_current",
        "eligible_for_v3_training": eligible,
        "promotion_gate": gate,
        "local_image_path": row.get("local_image_path", ""),
        "source_image_path": "",
        "source_label_path": "",
        "current_label_path": row.get("current_label_path", ""),
        "reviewed_label_path": row.get("reviewed_label_path", ""),
        "pseudo_original_label_path": "",
        "crop_path": row.get("crop_path", ""),
        "qc_flags": "",
        "status": row.get("status", ""),
        "queue_source": queue_source,
        "codex_suggested_decision": row.get("codex_suggested_decision", ""),
        "codex_review_priority": row.get("codex_review_priority", ""),
        "codex_visual_note": row.get("codex_visual_note", ""),
        "notes": row.get("manual_notes", ""),
    }


def additional_candidate(row: Mapping[str, str], index: int) -> dict[str, Any]:
    image_path = row.get("sample_image_path") or row.get("image_path", "")
    label_path = row.get("sample_label_path") or row.get("label_path", "")
    image_name = path_name(image_path)
    label_name = path_name(label_path) or f"{Path(image_name).stem}.txt"
    return {
        "candidate_id": f"additional-{index:04d}",
        "source_queue": "qa300_additional",
        "source_row_id": row.get("sample_index") or str(index),
        "image_name": image_name,
        "label_name": label_name,
        "source_video": row.get("video_name", ""),
        "frame_index": row.get("frame_index", ""),
        "timestamp_seconds": row.get("timestamp_seconds", ""),
        "profile": "additional_review",
        "review_reason": row.get("label_status", ""),
        "recommendation": "Human-review full person/helmet/visible vest labels before v3 promotion.",
        "review_intent": "human_review_full_label",
        "recommended_pool": "normal_pool",
        "manual_status": "todo",
        "manual_decision": "",
        "reviewer": "",
        "review_date": "",
        "label_source": "pseudo_world_qa300",
        "eligible_for_v3_training": "no",
        "promotion_gate": "blocked_manual_status_done_required",
        "local_image_path": image_path,
        "source_image_path": row.get("image_path", ""),
        "source_label_path": row.get("label_path", ""),
        "current_label_path": label_path,
        "reviewed_label_path": "",
        "pseudo_original_label_path": label_path,
        "crop_path": "",
        "qc_flags": "",
        "status": "",
        "queue_source": "",
        "codex_suggested_decision": "",
        "codex_review_priority": "",
        "codex_visual_note": "",
        "notes": "auto-selected to reach acceptance review target",
    }


def build_acceptance_review_candidates(
    priority_workspace: Path,
    v5_workspace: Path,
    qa_sample_csv: Path | None = None,
    min_unique_images: int = 200,
) -> CandidatePackage:
    rows: list[dict[str, Any]] = []
    unique_images: set[str] = set()
    seen_source_keys: set[str] = set()

    priority_rows = read_csv(priority_workspace / "labeling_queue.csv")
    for index, source_row in enumerate(priority_rows, start=1):
        row = priority_candidate(source_row, index)
        rows.append(row)
        add_unique_image(unique_images, str(row["image_name"]))
        for key in ("image_name", "source_image_path", "local_image_path"):
            add_seen_source_key(seen_source_keys, source_row.get(key, ""))

    v5_rows = read_csv(v5_workspace / "review_queue_workspace.csv")
    for index, source_row in enumerate(v5_rows, start=1):
        row = v5_candidate(source_row, index)
        rows.append(row)
        add_unique_image(unique_images, str(row["image_name"]))
        for key in ("image_name", "local_image_path"):
            add_seen_source_key(seen_source_keys, source_row.get(key, ""))

    if qa_sample_csv is not None and qa_sample_csv.exists():
        additional_index = 1
        for source_row in read_csv(qa_sample_csv):
            if len(unique_images) >= min_unique_images:
                break
            sample_name = path_name(source_row.get("sample_image_path") or source_row.get("image_path", ""))
            if not sample_name or sample_name.lower() in seen_source_keys:
                continue
            row = additional_candidate(source_row, additional_index)
            rows.append(row)
            additional_index += 1
            add_unique_image(unique_images, str(row["image_name"]))
            add_seen_source_key(seen_source_keys, row["image_name"])
            add_seen_source_key(seen_source_keys, row["local_image_path"])

    row_counts_by_source = Counter(str(row.get("source_queue", "")) for row in rows)
    manual_status_counts = Counter(str(row.get("manual_status", "")) for row in rows)
    summary = {
        "generated_date": date.today().isoformat(),
        "total_rows": len(rows),
        "unique_images": len(unique_images),
        "target_min_unique_images": min_unique_images,
        "target_max_unique_images": 400,
        "additional_unique_images_needed": max(0, min_unique_images - len(unique_images)),
        "row_counts_by_source": dict(row_counts_by_source),
        "manual_status_counts": dict(manual_status_counts),
        "eligible_rows": sum(row.get("eligible_for_v3_training") == "yes" for row in rows),
        "human_review_required_rows": sum(row.get("eligible_for_v3_training") != "yes" for row in rows),
        "v5_event_rows": row_counts_by_source.get("v5_review_queue", 0),
    }
    return CandidatePackage(rows=rows, summary=summary)


def write_acceptance_review_package(
    output_root: Path,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    write_csv(output_root / "review_candidates.csv", rows, merge_fieldnames(rows, CANDIDATE_FIELDS))
    (output_root / "summary.json").write_text(
        json.dumps(dict(summary), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_review_package_readme(output_root, summary)


def write_review_package_readme(output_root: Path, summary: Mapping[str, Any]) -> None:
    lines = [
        "# Station PPE Acceptance Review Candidates",
        "",
        f"- Total candidate rows: {summary.get('total_rows', 0)}",
        f"- Unique images represented: {summary.get('unique_images', 0)}",
        f"- Target unique images: {summary.get('target_min_unique_images', 200)}-400",
        f"- Additional unique images still needed: {summary.get('additional_unique_images_needed', 0)}",
        "",
        "Promotion gate:",
        "",
        "- Only rows with `manual_status=done` may be considered for the v3 human-reviewed training dataset.",
        "- `codex_reviewed`, `todo`, pseudo labels, draft labels, and visual triage notes are review inputs only.",
        "- Detector classes are exactly `person`, `helmet`, and visible `vest`.",
        "- `no_helmet` and `no_vest` remain event-layer states and must not become detector object classes.",
        "",
        "Human review checklist:",
        "",
        "1. Correct all visible `person`, `helmet`, and visible `vest` boxes.",
        "2. Remove false `person` boxes on bags, covers, pipes, extinguishers, materials, and clutter.",
        "3. Keep unclear PPE out of normal validation unless it is tagged for stress evaluation.",
        "4. Fill reviewer, review date, manual status, notes, label source, and sample profile before promotion.",
    ]
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def last_results_row(results_csv: Path) -> dict[str, str]:
    if not results_csv.exists():
        return {}
    rows = read_csv(results_csv)
    return rows[-1] if rows else {}


def summarize_csv_counts(csv_path: Path, field: str) -> dict[str, int]:
    if not csv_path.exists():
        return {}
    return dict(Counter(row.get(field, "") for row in read_csv(csv_path)))


def summarize_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {}
    rows = read_csv(manifest_path)
    return {
        "rows": len(rows),
        "split_counts": dict(Counter(row.get("split", "") for row in rows)),
        "profile_counts": dict(Counter(row.get("profile", "") for row in rows)),
        "manual_status_counts": dict(Counter(row.get("manual_status", "") for row in rows)),
        "label_source_warning": "manifest paths still reference v2_6class in some rows"
        if any("v2_6class" in row.get("dataset_image_path", "") for row in rows)
        else "",
    }


def metric_block_from_doc(metric_doc: Path | None) -> list[str]:
    if metric_doc is None or not metric_doc.exists():
        return []
    lines = metric_doc.read_text(encoding="utf-8").splitlines()
    start = None
    end = None
    for index, line in enumerate(lines):
        if line.strip() == "### Validation Metrics":
            start = index
        elif start is not None and line.strip().startswith("### ") and index > start:
            end = index
            break
    if start is None:
        return []
    return lines[start : end or min(len(lines), start + 60)]


def write_baseline_report(
    output_path: Path,
    dataset_root: Path,
    model_path: Path,
    results_csv: Path,
    strict_v5_dir: Path,
    metric_doc: Path | None = None,
) -> None:
    dataset_summary = count_yolo_dataset(dataset_root, CLASS_MAP_3)
    manifest_summary = summarize_manifest(dataset_root / "manifest.csv")
    final_results = last_results_row(results_csv)
    strict_event_decision_counts = summarize_csv_counts(strict_v5_dir / "ppe_events.csv", "event_decision")
    strict_event_status_counts = summarize_csv_counts(strict_v5_dir / "ppe_events.csv", "status")
    strict_queue_counts = summarize_csv_counts(strict_v5_dir / "ppe_review_queue.csv", "queue_source")
    strict_rejected_rows = read_csv(strict_v5_dir / "ppe_rejected_candidates.csv") if (strict_v5_dir / "ppe_rejected_candidates.csv").exists() else []
    metric_lines = metric_block_from_doc(metric_doc)

    lines = [
        "# Station PPE V2 Baseline Freeze",
        "",
        f"- Generated date: {date.today().isoformat()}",
        f"- Model path: `{model_path}`",
        f"- Dataset path: `{dataset_root}`",
        f"- Training results CSV: `{results_csv}`",
        f"- Strict V5 demo output: `{strict_v5_dir}`",
        "",
        "## Dataset Counts",
        "",
        f"- Image counts: `{dataset_summary['image_counts']}`",
        f"- Label file counts: `{dataset_summary['label_file_counts']}`",
        f"- Empty label files: `{dataset_summary['empty_label_files']}`",
        f"- Class counts: `{dataset_summary['class_counts']}`",
        f"- Invalid label rows: {len(dataset_summary['invalid_labels'])}",
        f"- Missing label files: {len(dataset_summary['missing_label_files'])}",
        f"- Orphan label files: {len(dataset_summary['orphan_label_files'])}",
        "",
        "## Manifest Composition",
        "",
        f"- Rows: {manifest_summary.get('rows', 0)}",
        f"- Split counts: `{manifest_summary.get('split_counts', {})}`",
        f"- Profile counts: `{manifest_summary.get('profile_counts', {})}`",
        f"- Manual status counts: `{manifest_summary.get('manual_status_counts', {})}`",
    ]
    if manifest_summary.get("label_source_warning"):
        lines.append(f"- Provenance warning: {manifest_summary['label_source_warning']}")
    lines.extend(
        [
            "",
            "## Training Final Aggregate",
            "",
            f"- Final epoch: {final_results.get('epoch', '')}",
            f"- Precision(B): {final_results.get('metrics/precision(B)', '')}",
            f"- Recall(B): {final_results.get('metrics/recall(B)', '')}",
            f"- mAP50(B): {final_results.get('metrics/mAP50(B)', '')}",
            f"- mAP50-95(B): {final_results.get('metrics/mAP50-95(B)', '')}",
            "",
            "## Validation And Test Metrics",
            "",
        ]
    )
    if metric_lines:
        lines.extend(metric_lines)
    else:
        lines.append("Metric source document not provided; see training run outputs.")
    lines.extend(
        [
            "",
            "## Strict V5 Demo Counts",
            "",
            f"- Event decision counts: `{strict_event_decision_counts}`",
            f"- Event status counts: `{strict_event_status_counts}`",
            f"- Review queue source counts: `{strict_queue_counts}`",
            f"- Rejected candidate rows: {len(strict_rejected_rows)}",
            "",
            "## Known Failure Modes",
            "",
            "- V2 was trained from Codex auto-reviewed labels, not human gold labels.",
            "- Vest detector did not generalize; vest event handling relies on downstream color/rule fallback.",
            "- V2 validation/test splits are stress-heavy rather than normal business acceptance splits.",
            "- The current demo can show the workflow, but it is not business-acceptance-ready.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def label_path_status(rows: Sequence[Mapping[str, str]], key: str) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        raw_path = str(row.get(key, "")).strip()
        if not raw_path:
            counts["blank"] += 1
            continue
        path = Path(raw_path)
        if not path.exists():
            counts["missing"] += 1
        elif path.read_text(encoding="utf-8").strip():
            counts["nonempty"] += 1
        else:
            counts["empty"] += 1
    return dict(counts)


def audit_review_inputs(priority_workspace: Path, v5_workspace: Path) -> dict[str, Any]:
    priority_rows = read_csv(priority_workspace / "labeling_queue.csv")
    v5_rows = read_csv(v5_workspace / "review_queue_workspace.csv")
    priority_images = [row.get("image_name", "") for row in priority_rows]
    v5_images = [row.get("image_name", "") for row in v5_rows]
    draft_manifest = v5_workspace / "codex_draft_label_manifest.csv"
    draft_rows = read_csv(draft_manifest) if draft_manifest.exists() else []
    return {
        "priority": {
            "rows": len(priority_rows),
            "unique_images": len(set(priority_images)),
            "duplicate_image_rows": len(priority_images) - len(set(priority_images)),
            "manual_status_counts": dict(Counter(row.get("manual_status", "") for row in priority_rows)),
            "profile_counts": dict(Counter(row.get("profile", "") for row in priority_rows)),
            "reviewed_label_path_status": label_path_status(priority_rows, "reviewed_label_path"),
            "pseudo_original_label_path_status": label_path_status(priority_rows, "pseudo_original_label_path"),
            "codex_auto_review_note_rows": sum("codex_auto_review" in row.get("manual_notes", "") for row in priority_rows),
        },
        "v5": {
            "rows": len(v5_rows),
            "unique_images": len(set(v5_images)),
            "duplicate_image_rows": len(v5_images) - len(set(v5_images)),
            "manual_status_counts": dict(Counter(row.get("manual_status", "") for row in v5_rows)),
            "queue_source_counts": dict(Counter(row.get("queue_source", "") for row in v5_rows)),
            "reviewed_label_path_status": label_path_status(v5_rows, "reviewed_label_path"),
            "current_label_path_status": label_path_status(v5_rows, "current_label_path"),
            "codex_suggested_decision_counts": dict(Counter(row.get("codex_suggested_decision", "") for row in v5_rows)),
            "draft_manifest_rows": len(draft_rows),
        },
    }


def write_audit_report(output_path: Path, audit: Mapping[str, Any]) -> None:
    lines = [
        "# Station PPE V3 Data Input Audit",
        "",
        f"- Generated date: {date.today().isoformat()}",
        "",
        "## Priority Workspace",
        "",
        f"- Rows: {audit['priority']['rows']}",
        f"- Unique images: {audit['priority']['unique_images']}",
        f"- Duplicate image rows: {audit['priority']['duplicate_image_rows']}",
        f"- Manual status counts: `{audit['priority']['manual_status_counts']}`",
        f"- Profile counts: `{audit['priority']['profile_counts']}`",
        f"- Reviewed label path status: `{audit['priority']['reviewed_label_path_status']}`",
        f"- Original pseudo label path status: `{audit['priority']['pseudo_original_label_path_status']}`",
        f"- Rows carrying Codex auto-review notes: {audit['priority']['codex_auto_review_note_rows']}",
        "",
        "## V5 Review Workspace",
        "",
        f"- Rows: {audit['v5']['rows']}",
        f"- Unique images: {audit['v5']['unique_images']}",
        f"- Duplicate image rows: {audit['v5']['duplicate_image_rows']}",
        f"- Manual status counts: `{audit['v5']['manual_status_counts']}`",
        f"- Queue source counts: `{audit['v5']['queue_source_counts']}`",
        f"- Current label path status: `{audit['v5']['current_label_path_status']}`",
        f"- Reviewed label path status: `{audit['v5']['reviewed_label_path_status']}`",
        f"- Codex suggested decision counts: `{audit['v5']['codex_suggested_decision_counts']}`",
        f"- Codex draft manifest rows: {audit['v5']['draft_manifest_rows']}",
        "",
        "## Gate Decision",
        "",
        "- These inputs are review queues, not a completed v3 training dataset.",
        "- `codex_reviewed` and `todo` are blocked until a human reviewer marks corrected full-image labels as `done`.",
        "- V5 event rows are useful error evidence, but duplicate event rows must be collapsed at image level before dataset promotion.",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_class_rules_report(output_path: Path) -> None:
    lines = [
        "# Station PPE V3 Class Map And Annotation Rules",
        "",
        f"- Generated date: {date.today().isoformat()}",
        "",
        "## Detector Classes",
        "",
        "```yaml",
        "0: person",
        "1: helmet",
        "2: vest",
        "```",
        "",
        "- `person`: visible worker body extent. Use one box per real worker; remove boxes on bags, covers, pipes, extinguishers, materials, and clutter.",
        "- `helmet`: visible helmet shell on a worker. Do not guess hidden helmets.",
        "- `vest`: visible safety vest or high-visibility torso garment. Box only the visible vest area, not the full torso unless the full torso is visibly vest.",
        "- `no_helmet` and `no_vest`: event-layer states only. They are derived after matching PPE evidence to a person and must not appear as detector classes.",
        "",
        "## Annotation Rules",
        "",
        "- Visible vest boxes: annotate orange, yellow, reflective, or other clearly visible safety vest regions; skip ambiguous reflections or ordinary clothing.",
        "- Helmet boxes: annotate visible helmets even when small, but skip if the head/helmet is too blurred to verify.",
        "- Partial workers: annotate visible body parts as `person` when the worker is clearly present; tag edge/occluded cases for stress evaluation.",
        "- Tiny or edge workers: include only when a human can consistently place a box; otherwise mark unclear and keep out of normal validation.",
        "- Hard negatives: include reviewed images where false-person sources are present and false person boxes were removed.",
        "- Unclear samples: keep in the manifest with notes; do not use for normal metrics unless a reviewer marks them complete and assigns the right profile.",
        "- Skipped samples: record why they were skipped so they do not silently enter v3 training.",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    candidates = subparsers.add_parser("candidates", help="build the acceptance review candidate package")
    candidates.add_argument("--priority-workspace", required=True, type=Path)
    candidates.add_argument("--v5-workspace", required=True, type=Path)
    candidates.add_argument("--qa-sample-csv", type=Path)
    candidates.add_argument("--output", required=True, type=Path)
    candidates.add_argument("--min-unique-images", type=int, default=200)

    draft = subparsers.add_parser("multimodal-draft", help="create a 3-class AI multimodal draft review package")
    draft.add_argument("--candidates-csv", required=True, type=Path)
    draft.add_argument("--output", required=True, type=Path)
    draft.add_argument("--reviewer", default="codex_multimodal_ai")

    baseline = subparsers.add_parser("baseline", help="write the frozen V2 baseline report")
    baseline.add_argument("--dataset-root", required=True, type=Path)
    baseline.add_argument("--model-path", required=True, type=Path)
    baseline.add_argument("--results-csv", required=True, type=Path)
    baseline.add_argument("--strict-v5-dir", required=True, type=Path)
    baseline.add_argument("--metric-doc", type=Path)
    baseline.add_argument("--output", required=True, type=Path)

    audit = subparsers.add_parser("audit", help="write the V3 input audit report")
    audit.add_argument("--priority-workspace", required=True, type=Path)
    audit.add_argument("--v5-workspace", required=True, type=Path)
    audit.add_argument("--output", required=True, type=Path)

    rules = subparsers.add_parser("rules", help="write V3 class map and annotation rules")
    rules.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        if args.command == "candidates":
            package = build_acceptance_review_candidates(
                priority_workspace=args.priority_workspace,
                v5_workspace=args.v5_workspace,
                qa_sample_csv=args.qa_sample_csv,
                min_unique_images=args.min_unique_images,
            )
            write_acceptance_review_package(args.output, package.rows, package.summary)
            print(f"Wrote review candidates: {args.output}")
            print(f"Rows: {package.summary['total_rows']}")
            print(f"Unique images: {package.summary['unique_images']}")
            return 0
        if args.command == "baseline":
            write_baseline_report(
                output_path=args.output,
                dataset_root=args.dataset_root,
                model_path=args.model_path,
                results_csv=args.results_csv,
                strict_v5_dir=args.strict_v5_dir,
                metric_doc=args.metric_doc,
            )
            print(f"Wrote baseline report: {args.output}")
            return 0
        if args.command == "multimodal-draft":
            summary = create_multimodal_draft_package(
                read_csv(args.candidates_csv),
                args.output,
                reviewer=args.reviewer,
            )
            print(f"Wrote multimodal draft package: {args.output}")
            print(f"Unique images: {summary['unique_images']}")
            print(f"Draft labels: {summary['total_draft_labels']}")
            return 0
        if args.command == "audit":
            write_audit_report(args.output, audit_review_inputs(args.priority_workspace, args.v5_workspace))
            print(f"Wrote audit report: {args.output}")
            return 0
        if args.command == "rules":
            write_class_rules_report(args.output)
            print(f"Wrote class/rules report: {args.output}")
            return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"station_ppe_retrain error: {exc}", file=sys.stderr)
        return 2
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
