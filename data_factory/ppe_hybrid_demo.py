#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a first-pass PPE demo: YOLO for person/helmet plus color-rule vest status."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np
from ultralytics import YOLO

from data_factory.ppe_auto_review import Label, detect_vest_candidate, xyxy_to_label


PERSON = 0
HELMET = 1
VEST = 2


@dataclass(frozen=True)
class Detection:
    class_id: int
    confidence: float
    box: tuple[int, int, int, int]


@dataclass(frozen=True)
class PersonFilterConfig:
    enabled: bool = True
    min_confidence: float = 0.45
    min_height: int = 80
    min_aspect: float = 1.25
    max_aspect: float = 5.0
    duplicate_iou: float = 0.35
    duplicate_containment: float = 0.65


@dataclass(frozen=True)
class ReviewConfig:
    auto_ok_min_confidence: float = 0.70
    rejected_review_min_confidence: float = 0.25
    rejected_aspect_review_min_confidence: float = 0.45


def center_inside(box: tuple[int, int, int, int], region: tuple[int, int, int, int]) -> bool:
    x1, y1, x2, y2 = box
    rx1, ry1, rx2, ry2 = region
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    return rx1 <= cx <= rx2 and ry1 <= cy <= ry2


def helmet_matches_person(helmet: Detection, person: Detection) -> bool:
    px1, py1, px2, py2 = person.box
    person_w = px2 - px1
    person_h = py2 - py1
    head_region = (
        round(px1 - person_w * 0.25),
        round(py1 - person_h * 0.18),
        round(px2 + person_w * 0.25),
        round(py1 + person_h * 0.42),
    )
    return center_inside(helmet.box, head_region)


def status_text(helmet_present: bool, vest_present: bool) -> str:
    missing = []
    if not helmet_present:
        missing.append("no_helmet")
    if not vest_present:
        missing.append("no_vest")
    return "ok" if not missing else "+".join(missing)


def box_area(box: tuple[int, int, int, int]) -> int:
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    width = max(0, min(ax2, bx2) - max(ax1, bx1))
    height = max(0, min(ay2, by2) - max(ay1, by1))
    return width * height


def box_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    intersection = intersection_area(a, b)
    union = box_area(a) + box_area(b) - intersection
    return 0.0 if union <= 0 else intersection / union


def smaller_box_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    intersection = intersection_area(a, b)
    smaller = min(box_area(a), box_area(b))
    return 0.0 if smaller <= 0 else intersection / smaller


def person_quality_rejection_reason(person: Detection, config: PersonFilterConfig) -> str | None:
    if not config.enabled:
        return None
    x1, y1, x2, y2 = person.box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    aspect = height / width
    if person.confidence < config.min_confidence:
        return "low_confidence"
    if height < config.min_height:
        return "too_small"
    if aspect < config.min_aspect:
        return "bad_aspect_too_square"
    if aspect > config.max_aspect:
        return "bad_aspect_too_thin"
    return None


def filter_persons(
    persons: Sequence[Detection],
    config: PersonFilterConfig,
) -> tuple[list[Detection], list[tuple[Detection, str]]]:
    accepted: list[Detection] = []
    rejected: list[tuple[Detection, str]] = []
    for person in sorted(persons, key=lambda item: item.confidence, reverse=True):
        reason = person_quality_rejection_reason(person, config)
        if reason is None and config.enabled:
            for kept in accepted:
                if (
                    box_iou(person.box, kept.box) >= config.duplicate_iou
                    or smaller_box_overlap(person.box, kept.box) >= config.duplicate_containment
                ):
                    reason = "duplicate_person"
                    break
        if reason is None:
            accepted.append(person)
        else:
            rejected.append((person, reason))
    return accepted, rejected


def parse_result_detections(result: Any, conf_threshold: float) -> list[Detection]:
    detections: list[Detection] = []
    if result.boxes is None:
        return detections
    for box in result.boxes:
        class_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        if confidence < conf_threshold:
            continue
        x1, y1, x2, y2 = [int(round(value)) for value in box.xyxy[0].tolist()]
        detections.append(Detection(class_id, confidence, (x1, y1, x2, y2)))
    return detections


def draw_label(
    image: np.ndarray,
    box: tuple[int, int, int, int],
    label: str,
    color: tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = box
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
    y_text = max(18, y1 - 6)
    cv2.putText(image, label, (x1, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)


def detect_helmet_candidate(
    image_bgr: np.ndarray,
    person: Detection,
) -> tuple[int, int, int, int] | None:
    height, width = image_bgr.shape[:2]
    px1, py1, px2, py2 = person.box
    person_w = max(1, px2 - px1)
    person_h = max(1, py2 - py1)
    if person_w < 18 or person_h < 35:
        return None

    hx1 = max(0, round(px1 - person_w * 0.12))
    hx2 = min(width, round(px2 + person_w * 0.12))
    hy1 = max(0, round(py1 - person_h * 0.16))
    hy2 = min(height, round(py1 + person_h * 0.28))
    if hx2 <= hx1 or hy2 <= hy1:
        return None

    head = image_bgr[hy1:hy2, hx1:hx2]
    if head.size == 0:
        return None
    hsv = cv2.cvtColor(head, cv2.COLOR_BGR2HSV)

    yellow_orange = (hsv[:, :, 0] >= 12) & (hsv[:, :, 0] <= 42) & (hsv[:, :, 1] >= 70) & (hsv[:, :, 2] >= 90)
    blue = (hsv[:, :, 0] >= 88) & (hsv[:, :, 0] <= 132) & (hsv[:, :, 1] >= 50) & (hsv[:, :, 2] >= 65)
    red = ((hsv[:, :, 0] <= 8) | (hsv[:, :, 0] >= 170)) & (hsv[:, :, 1] >= 80) & (hsv[:, :, 2] >= 80)
    mask = (yellow_orange | blue | red).astype("uint8") * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    head_area = max(1, head.shape[0] * head.shape[1])
    if int(np.count_nonzero(mask)) < max(12, head_area * 0.012):
        return None

    num_labels, _components, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates: list[tuple[int, tuple[int, int, int, int]]] = []
    for component_id in range(1, num_labels):
        x, y, w, h, area = stats[component_id]
        if area < max(12, head_area * 0.018):
            continue
        if w < 5 or h < 5:
            continue
        abs_x1, abs_y1, abs_x2, abs_y2 = hx1 + x, hy1 + y, hx1 + x + w, hy1 + y + h
        center_x = (abs_x1 + abs_x2) / 2
        center_y = (abs_y1 + abs_y2) / 2
        if not (px1 + person_w * 0.05 <= center_x <= px2 - person_w * 0.05):
            continue
        if center_y > py1 + person_h * 0.24:
            continue
        candidates.append((int(area), (abs_x1, abs_y1, abs_x2, abs_y2)))

    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def analyze_image(
    image_path: Path,
    detections: Sequence[Detection],
    output_path: Path,
    person_filter: PersonFilterConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    height, width = image.shape[:2]

    person_candidates = [d for d in detections if d.class_id == PERSON]
    persons, rejected_persons = filter_persons(person_candidates, person_filter)
    helmets = [d for d in detections if d.class_id == HELMET]
    rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []

    for helmet in helmets:
        draw_label(image, helmet.box, f"helmet {helmet.confidence:.2f}", (0, 220, 255))

    for index, person in enumerate(persons, start=1):
        helmet_present_model = any(helmet_matches_person(helmet, person) for helmet in helmets)
        helmet_candidate = None if helmet_present_model else detect_helmet_candidate(image, person)
        helmet_present = helmet_present_model or helmet_candidate is not None
        person_label = xyxy_to_label(PERSON, person.box, width, height)
        vest_candidate = detect_vest_candidate(image, person_label)
        vest_present = vest_candidate is not None
        state = status_text(helmet_present, vest_present)
        color = (70, 210, 70) if state == "ok" else (40, 40, 240)
        draw_label(image, person.box, f"person {index} {state}", color)

        if vest_candidate is not None:
            vx1 = round((vest_candidate.x - vest_candidate.w / 2) * width)
            vy1 = round((vest_candidate.y - vest_candidate.h / 2) * height)
            vx2 = round((vest_candidate.x + vest_candidate.w / 2) * width)
            vy2 = round((vest_candidate.y + vest_candidate.h / 2) * height)
            draw_label(image, (vx1, vy1, vx2, vy2), "vest-rule", (60, 200, 80))

        if helmet_candidate is not None:
            draw_label(image, helmet_candidate, "helmet-rule", (0, 210, 255))

        rows.append(
            {
                "image_name": image_path.name,
                "person_index": index,
                "person_confidence": f"{person.confidence:.4f}",
                "x1": person.box[0],
                "y1": person.box[1],
                "x2": person.box[2],
                "y2": person.box[3],
                "helmet_present": str(helmet_present).lower(),
                "helmet_present_model": str(helmet_present_model).lower(),
                "helmet_present_rule": str(helmet_candidate is not None).lower(),
                "vest_present_rule": str(vest_present).lower(),
                "status": state,
            }
        )

    for index, (person, reason) in enumerate(rejected_persons, start=1):
        rejected_rows.append(
            {
                "image_name": image_path.name,
                "candidate_index": index,
                "person_confidence": f"{person.confidence:.4f}",
                "x1": person.box[0],
                "y1": person.box[1],
                "x2": person.box[2],
                "y2": person.box[3],
                "reason": reason,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), image)
    return rows, rejected_rows


def write_event_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fieldnames = [
        "image_name",
        "person_index",
        "person_confidence",
        "x1",
        "y1",
        "x2",
        "y2",
        "helmet_present",
        "helmet_present_model",
        "helmet_present_rule",
        "vest_present_rule",
        "status",
        "event_decision",
        "review_reason",
        "evidence_summary",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_rejected_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fieldnames = [
        "image_name",
        "candidate_index",
        "person_confidence",
        "x1",
        "y1",
        "x2",
        "y2",
        "reason",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def event_review_reasons(row: Mapping[str, Any], config: ReviewConfig) -> list[str]:
    reasons: list[str] = []
    confidence = float(row["person_confidence"])
    if row["status"] != "ok":
        reasons.append("suspected_ppe_issue")
    if row["helmet_present_model"] == "false" and row["helmet_present_rule"] == "true":
        reasons.append("helmet_rule_only")
    if confidence < config.auto_ok_min_confidence:
        reasons.append("medium_person_confidence")
    return reasons


def event_evidence_summary(row: Mapping[str, Any]) -> str:
    helmet = "helmet_model" if row["helmet_present_model"] == "true" else "helmet_rule"
    if row["helmet_present"] == "false":
        helmet = "helmet_missing"
    vest = "vest_rule" if row["vest_present_rule"] == "true" else "vest_missing_or_unconfirmed"
    return f"person_model|{helmet}|{vest}"


def enrich_event_rows(
    rows: Sequence[Mapping[str, Any]],
    config: ReviewConfig,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        updated = dict(row)
        reasons = event_review_reasons(row, config)
        updated["event_decision"] = "needs_review" if reasons else "auto_demo_ok"
        updated["review_reason"] = "|".join(reasons)
        updated["evidence_summary"] = event_evidence_summary(row)
        enriched.append(updated)
    return enriched


def rejected_manual_review_reason(row: Mapping[str, Any], config: ReviewConfig) -> str | None:
    confidence = float(row["person_confidence"])
    reason = str(row["reason"])
    if reason == "duplicate_person":
        return None
    if reason == "low_confidence" and confidence >= config.rejected_review_min_confidence:
        return "possible_worker_low_confidence"
    if reason.startswith("bad_aspect") and confidence >= config.rejected_aspect_review_min_confidence:
        return "possible_worker_or_hard_negative"
    if reason == "too_small" and confidence >= config.rejected_aspect_review_min_confidence:
        return "small_worker_check"
    return None


def build_review_queue(
    event_rows: Sequence[Mapping[str, Any]],
    rejected_rows: Sequence[Mapping[str, Any]],
    config: ReviewConfig,
) -> list[dict[str, Any]]:
    review_rows: list[dict[str, Any]] = []
    for row in event_rows:
        if row["event_decision"] != "needs_review":
            continue
        review_rows.append(
            {
                "image_name": row["image_name"],
                "queue_source": "accepted_event",
                "source_index": row["person_index"],
                "person_confidence": row["person_confidence"],
                "x1": row["x1"],
                "y1": row["y1"],
                "x2": row["x2"],
                "y2": row["y2"],
                "status": row["status"],
                "review_reason": row["review_reason"],
                "recommendation": "manual_check_event",
            }
        )

    for row in rejected_rows:
        review_reason = rejected_manual_review_reason(row, config)
        if review_reason is None:
            continue
        recommendation = "label_as_hard_negative_or_fix_person"
        if review_reason == "possible_worker_low_confidence":
            recommendation = "check_if_worker_then_fix_label"
        review_rows.append(
            {
                "image_name": row["image_name"],
                "queue_source": "rejected_candidate",
                "source_index": row["candidate_index"],
                "person_confidence": row["person_confidence"],
                "x1": row["x1"],
                "y1": row["y1"],
                "x2": row["x2"],
                "y2": row["y2"],
                "status": "suppressed",
                "review_reason": review_reason,
                "recommendation": recommendation,
            }
        )
    return review_rows


def write_review_queue_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fieldnames = [
        "image_name",
        "queue_source",
        "source_index",
        "person_confidence",
        "x1",
        "y1",
        "x2",
        "y2",
        "status",
        "review_reason",
        "recommendation",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def crop_sheet_color(row: Mapping[str, Any]) -> tuple[int, int, int]:
    if str(row.get("queue_source", "")) == "rejected_candidate":
        return (0, 170, 255)
    if str(row.get("status", "")) == "ok":
        return (60, 180, 60)
    if str(row.get("status", "")) == "suppressed":
        return (80, 80, 220)
    return (40, 40, 230)


def build_row_crop_sheet(
    rows: Sequence[Mapping[str, Any]],
    images_dir: Path,
    output_path: Path,
    columns: int = 5,
    tile_width: int = 300,
    tile_height: int = 300,
) -> None:
    if not rows:
        return

    caption_height = 64
    margin = 8
    tiles: list[np.ndarray] = []
    for index, row in enumerate(rows, start=1):
        image = cv2.imread(str(images_dir / str(row["image_name"])))
        if image is None:
            continue
        height, width = image.shape[:2]
        x1, y1, x2, y2 = (int(row[key]) for key in ("x1", "y1", "x2", "y2"))
        pad_x = max(30, int((x2 - x1) * 0.40))
        pad_y = max(30, int((y2 - y1) * 0.30))
        cx1 = max(0, x1 - pad_x)
        cy1 = max(0, y1 - pad_y)
        cx2 = min(width, x2 + pad_x)
        cy2 = min(height, y2 + pad_y)
        crop = image[cy1:cy2, cx1:cx2].copy()
        if crop.size == 0:
            continue

        color = crop_sheet_color(row)
        cv2.rectangle(crop, (x1 - cx1, y1 - cy1), (x2 - cx1, y2 - cy1), color, 2)
        scale = min(tile_width / crop.shape[1], tile_height / crop.shape[0])
        resized_width = max(1, int(crop.shape[1] * scale))
        resized_height = max(1, int(crop.shape[0] * scale))
        resized = cv2.resize(crop, (resized_width, resized_height), interpolation=cv2.INTER_AREA)

        tile = np.full((tile_height + caption_height, tile_width, 3), 255, dtype=np.uint8)
        y_offset = (tile_height - resized_height) // 2
        x_offset = (tile_width - resized_width) // 2
        tile[y_offset : y_offset + resized_height, x_offset : x_offset + resized_width] = resized

        title = str(row.get("status", row.get("reason", "")))
        reason = str(row.get("review_reason", row.get("reason", "")))
        cv2.putText(tile, f"#{index} {title[:28]}", (6, tile_height + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.46, color, 1, cv2.LINE_AA)
        cv2.putText(tile, f"conf {row['person_confidence']} {reason[:32]}", (6, tile_height + 39), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (30, 30, 30), 1, cv2.LINE_AA)
        cv2.putText(tile, str(row["image_name"])[:46], (6, tile_height + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (30, 30, 30), 1, cv2.LINE_AA)
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


def build_contact_sheet(
    image_paths: Sequence[Path],
    output_path: Path,
    columns: int = 3,
    tile_width: int = 640,
    tile_height: int = 360,
) -> None:
    if not image_paths:
        return

    caption_height = 28
    tiles: list[np.ndarray] = []
    for image_path in image_paths:
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        resized = cv2.resize(image, (tile_width, tile_height), interpolation=cv2.INTER_AREA)
        tile = np.full((tile_height + caption_height, tile_width, 3), 255, dtype=np.uint8)
        tile[:tile_height, :, :] = resized
        cv2.putText(
            tile,
            image_path.name[:70],
            (8, tile_height + 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (30, 30, 30),
            1,
            cv2.LINE_AA,
        )
        tiles.append(tile)

    if not tiles:
        return

    rows = int(np.ceil(len(tiles) / columns))
    sheet = np.full(
        (rows * (tile_height + caption_height), columns * tile_width, 3),
        255,
        dtype=np.uint8,
    )
    for index, tile in enumerate(tiles):
        row = index // columns
        col = index % columns
        y1 = row * (tile_height + caption_height)
        x1 = col * tile_width
        sheet[y1 : y1 + tile.shape[0], x1 : x1 + tile.shape[1], :] = tile

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), sheet)


def status_counts(rows: Sequence[Mapping[str, Any]]) -> Counter[str]:
    return Counter(str(row["status"]) for row in rows)


def write_readme(
    output_dir: Path,
    weights: Path,
    images_dir: Path,
    conf: float,
    rows: Sequence[Mapping[str, Any]],
    rejected_rows: Sequence[Mapping[str, Any]],
    review_rows: Sequence[Mapping[str, Any]],
    annotated_count: int,
) -> None:
    counts = status_counts(rows)
    rejected_counts = Counter(str(row["reason"]) for row in rejected_rows)
    review_counts = Counter(str(row["review_reason"]) for row in review_rows)
    decision_counts = Counter(str(row["event_decision"]) for row in rows)
    count_lines = [f"- {name}: {count}" for name, count in sorted(counts.items())]
    if not count_lines:
        count_lines = ["- no person rows"]
    rejected_count_lines = [f"- {name}: {count}" for name, count in sorted(rejected_counts.items())]
    if not rejected_count_lines:
        rejected_count_lines = ["- no rejected candidates"]
    review_count_lines = [f"- {name}: {count}" for name, count in sorted(review_counts.items())]
    if not review_count_lines:
        review_count_lines = ["- no review queue rows"]
    decision_count_lines = [f"- {name}: {count}" for name, count in sorted(decision_counts.items())]
    if not decision_count_lines:
        decision_count_lines = ["- no event decisions"]

    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# PPE Hybrid Demo",
                "",
                f"- Weights: {weights}",
                f"- Images: {images_dir}",
                f"- Confidence threshold: {conf}",
                f"- Annotated images: {annotated_count}",
                f"- Person event rows: {len(rows)}",
                f"- Rejected person candidates: {len(rejected_rows)}",
                f"- Manual review queue rows: {len(review_rows)}",
                "",
                "## Status Counts",
                "",
                *count_lines,
                "",
                "## Event Decision Counts",
                "",
                *decision_count_lines,
                "",
                "## Rejected Candidate Counts",
                "",
                *rejected_count_lines,
                "",
                "## Review Queue Counts",
                "",
                *review_count_lines,
                "",
                "## Interpretation",
                "",
                "Person comes from YOLO. Helmet status uses YOLO first, then a conservative color-rule fallback in the head area.",
                "Vest status is a first-pass color rule inside each detected person torso box.",
                "Rows marked needs_review should not be treated as confirmed automatic events.",
                "This is suitable for a first technical demo and label-fix workflow, not for claiming mature automatic violation detection.",
                "",
                "## Outputs",
                "",
                "- annotated/",
                "- ppe_events.csv",
                "- ppe_rejected_candidates.csv",
                "- ppe_review_queue.csv",
                "- demo_contact_sheet.jpg",
                "- person_event_crop_sheet.jpg",
                "- review_queue_crop_sheet.jpg",
                "- rejected_candidate_crop_sheet.jpg",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_demo(
    weights: Path,
    images_dir: Path,
    output_dir: Path,
    conf: float,
    imgsz: int,
    person_filter: PersonFilterConfig,
    review_config: ReviewConfig,
) -> list[dict[str, Any]]:
    model = YOLO(str(weights))
    image_paths = sorted(images_dir.glob("*.jpg"))
    all_rows: list[dict[str, Any]] = []
    all_rejected_rows: list[dict[str, Any]] = []
    for result in model.predict(source=[str(path) for path in image_paths], conf=conf, imgsz=imgsz, device="cpu", verbose=False):
        image_path = Path(result.path)
        detections = parse_result_detections(result, conf)
        rows, rejected_rows = analyze_image(
            image_path=image_path,
            detections=detections,
            output_path=output_dir / "annotated" / image_path.name,
            person_filter=person_filter,
        )
        all_rows.extend(rows)
        all_rejected_rows.extend(rejected_rows)
    all_rows = enrich_event_rows(all_rows, review_config)
    review_rows = build_review_queue(all_rows, all_rejected_rows, review_config)
    write_event_csv(output_dir / "ppe_events.csv", all_rows)
    write_rejected_csv(output_dir / "ppe_rejected_candidates.csv", all_rejected_rows)
    write_review_queue_csv(output_dir / "ppe_review_queue.csv", review_rows)
    annotated_images = sorted((output_dir / "annotated").glob("*.jpg"))
    build_contact_sheet(
        annotated_images,
        output_dir / "demo_contact_sheet.jpg",
    )
    build_row_crop_sheet(
        all_rows,
        images_dir,
        output_dir / "person_event_crop_sheet.jpg",
    )
    build_row_crop_sheet(
        review_rows,
        images_dir,
        output_dir / "review_queue_crop_sheet.jpg",
    )
    build_row_crop_sheet(
        all_rejected_rows,
        images_dir,
        output_dir / "rejected_candidate_crop_sheet.jpg",
    )
    write_readme(
        output_dir=output_dir,
        weights=weights,
        images_dir=images_dir,
        conf=conf,
        rows=all_rows,
        rejected_rows=all_rejected_rows,
        review_rows=review_rows,
        annotated_count=len(annotated_images),
    )
    return all_rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--disable-person-filter", action="store_true")
    parser.add_argument("--person-min-conf", type=float, default=0.45)
    parser.add_argument("--person-min-height", type=int, default=80)
    parser.add_argument("--person-min-aspect", type=float, default=1.25)
    parser.add_argument("--person-max-aspect", type=float, default=5.0)
    parser.add_argument("--person-dedupe-iou", type=float, default=0.35)
    parser.add_argument("--person-dedupe-containment", type=float, default=0.65)
    parser.add_argument("--auto-ok-min-conf", type=float, default=0.70)
    parser.add_argument("--rejected-review-min-conf", type=float, default=0.25)
    parser.add_argument("--rejected-aspect-review-min-conf", type=float, default=0.45)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    person_filter = PersonFilterConfig(
        enabled=not args.disable_person_filter,
        min_confidence=args.person_min_conf,
        min_height=args.person_min_height,
        min_aspect=args.person_min_aspect,
        max_aspect=args.person_max_aspect,
        duplicate_iou=args.person_dedupe_iou,
        duplicate_containment=args.person_dedupe_containment,
    )
    review_config = ReviewConfig(
        auto_ok_min_confidence=args.auto_ok_min_conf,
        rejected_review_min_confidence=args.rejected_review_min_conf,
        rejected_aspect_review_min_confidence=args.rejected_aspect_review_min_conf,
    )
    rows = run_demo(args.weights, args.images, args.output, args.conf, args.imgsz, person_filter, review_config)
    print(f"Created PPE demo output: {args.output}")
    print(f"Person rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
