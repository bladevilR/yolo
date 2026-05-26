"""Prototype endpoint-visible rebar material counting for field QC."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from data_factory.field_qc_inventory import REBAR_MATERIAL_COUNTING


MAX_ANALYSIS_DIMENSION = 1400


@dataclass(frozen=True)
class BarEndDetection:
    index: int
    center_x: float
    center_y: float
    radius: float
    confidence: float
    bbox: tuple[int, int, int, int]


@dataclass(frozen=True)
class MaterialCountResult:
    media_id: str
    file_name: str
    analysis_status: str
    detected_count: int
    confidence: float
    human_review_state: str
    review_flags: list[str]
    annotated_image_path: str
    detections: list[BarEndDetection]


@dataclass(frozen=True)
class MaterialCountingOutputPaths:
    report_csv: Path
    report_json: Path
    summary_md: Path


def analyze_material_count_image(
    image_path: Path,
    *,
    media_id: str,
    file_name: str,
    capture_tags: Sequence[str],
    existing_quality_flags: Sequence[str],
    output_dir: Path,
) -> MaterialCountResult:
    tags = set(capture_tags)
    flags = _dedupe([*existing_quality_flags])

    if "endpoint_face" not in tags:
        flags = _dedupe([*flags, "endpoint_face_required_for_exact_count"])
        if "side_view" in tags:
            flags.append("side_view_not_exact_count")
        if "occlusion" in tags and "occlusion_present" not in flags:
            flags.append("occlusion_present")
        annotated_path = _write_annotated_image(
            image_path,
            output_dir,
            media_id,
            file_name,
            detections=[],
            note="recapture endpoint face",
        )
        return MaterialCountResult(
            media_id=media_id,
            file_name=file_name,
            analysis_status="recapture_required",
            detected_count=0,
            confidence=0.0,
            human_review_state="awaiting_review",
            review_flags=_dedupe(flags),
            annotated_image_path=str(annotated_path),
            detections=[],
        )

    detections = detect_bar_end_candidates(image_path)
    confidence = round(sum(d.confidence for d in detections) / len(detections), 3) if detections else 0.0
    if not detections:
        analysis_status = "needs_review"
        flags = _dedupe([*flags, "no_bar_ends_detected"])
    else:
        analysis_status = "counted"
        if confidence < 0.7:
            flags = _dedupe([*flags, "low_confidence_count"])
        if len(detections) >= 30:
            analysis_status = "needs_review"
            flags = _dedupe([*flags, "high_density_count_requires_manual_review"])
        plausibility_flags = _count_plausibility_flags(image_path, detections)
        if plausibility_flags:
            analysis_status = "needs_review"
            flags = _dedupe([*flags, *plausibility_flags])

    annotated_path = _write_annotated_image(
        image_path,
        output_dir,
        media_id,
        file_name,
        detections=detections,
        note=f"candidate_count={len(detections)}" if len(detections) >= 30 else f"count={len(detections)}",
    )
    return MaterialCountResult(
        media_id=media_id,
        file_name=file_name,
        analysis_status=analysis_status,
        detected_count=len(detections),
        confidence=confidence,
        human_review_state="awaiting_review",
        review_flags=flags,
        annotated_image_path=str(annotated_path),
        detections=detections,
    )


def detect_bar_end_candidates(image_path: Path) -> list[BarEndDetection]:
    image, scale = _load_analysis_image(image_path)
    dense_candidates = _dense_endpoint_response_candidates(image, scale)
    mask = _rust_endpoint_mask(image)
    components = _connected_components(mask)
    detections: list[BarEndDetection] = []

    image_height, image_width = mask.shape
    image_area = image_width * image_height
    min_area = max(35, int(image_area * 0.00008))
    max_area = max(900, int(image_area * 0.01))
    max_component_side = max(40, int(min(image_width, image_height) * 0.12))

    for component in components:
        area = component["area"]
        min_x, min_y, max_x, max_y = component["bbox"]
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        if area < min_area or area > max_area:
            continue
        if width < 6 or height < 6 or width > max_component_side or height > max_component_side:
            continue
        aspect = width / height
        if aspect < 0.45 or aspect > 2.2:
            continue
        fill_ratio = area / (width * height)
        if fill_ratio < 0.28:
            continue

        aspect_score = 1.0 - min(abs(1.0 - aspect), 1.0)
        confidence = round(min(0.99, 0.45 + fill_ratio * 0.35 + aspect_score * 0.2), 3)
        center_x = component["sum_x"] / area / scale
        center_y = component["sum_y"] / area / scale
        radius = max(width, height) / 2 / scale
        original_bbox = (
            int(round(min_x / scale)),
            int(round(min_y / scale)),
            int(round(max_x / scale)),
            int(round(max_y / scale)),
        )
        detections.append(
            BarEndDetection(
                index=0,
                center_x=round(center_x, 2),
                center_y=round(center_y, 2),
                radius=round(radius, 2),
                confidence=confidence,
                bbox=original_bbox,
            )
        )

    detections = _keep_largest_spatial_cluster(detections)
    if len(dense_candidates) >= max(20, len(detections) * 3):
        detections = dense_candidates
    detections.sort(key=lambda detection: (detection.center_y, detection.center_x))
    return [
        BarEndDetection(
            index=index,
            center_x=detection.center_x,
            center_y=detection.center_y,
            radius=detection.radius,
            confidence=detection.confidence,
            bbox=detection.bbox,
        )
        for index, detection in enumerate(detections, start=1)
    ]


def _dense_endpoint_response_candidates(image: Image.Image, scale: float) -> list[BarEndDetection]:
    """Detect crowded endpoint faces by smoothed rust-color response.

    The first prototype used connected rust-color components. On field-qc-0026
    adjacent rusty end faces merge into large components, so it under-counted.
    This detector finds local maxima in a blurred endpoint-color response and is
    intentionally marked for human review when the result is dense.
    """

    array = np.asarray(image).astype(np.float32)
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    score = np.minimum.reduce(
        [
            (red - 70) / 110,
            (green - 35) / 90,
            (150 - blue) / 120,
            (red - blue) / 110,
            (green - blue + 10) / 90,
        ]
    )
    score = np.clip(score, 0, 1)
    score *= np.clip((green - 35) / 70, 0, 1)

    height, width = score.shape
    roi = np.zeros_like(score, dtype=bool)
    roi[int(height * 0.10) : int(height * 0.80), int(width * 0.08) : int(width * 0.92)] = True
    score *= roi

    blur_radius = max(4, int(min(width, height) * 0.012))
    response_image = Image.fromarray(np.uint8(score * 255)).filter(ImageFilter.GaussianBlur(radius=blur_radius))
    response = np.asarray(response_image).astype(np.float32)

    threshold = 100
    min_distance = max(18, int(min(width, height) * 0.052))
    raw_candidates = [
        (float(response[y, x]), int(x), int(y))
        for y, x in np.argwhere(response > threshold)
    ]
    raw_candidates.sort(reverse=True)

    selected: list[tuple[float, int, int]] = []
    for value, x, y in raw_candidates:
        if any((x - existing_x) ** 2 + (y - existing_y) ** 2 < min_distance**2 for _, existing_x, existing_y in selected):
            continue
        selected.append((value, x, y))

    radius = max(8, int(min_distance * 0.42))
    detections: list[BarEndDetection] = []
    for value, x, y in selected:
        original_x = x / scale
        original_y = y / scale
        original_radius = radius / scale
        bbox = (
            int(round((x - radius) / scale)),
            int(round((y - radius) / scale)),
            int(round((x + radius) / scale)),
            int(round((y + radius) / scale)),
        )
        detections.append(
            BarEndDetection(
                index=0,
                center_x=round(original_x, 2),
                center_y=round(original_y, 2),
                radius=round(original_radius, 2),
                confidence=round(min(0.95, 0.52 + (value / 255) * 0.38), 3),
                bbox=bbox,
            )
        )
    return detections


def run_material_counting_demo(manifest_csv: Path, output_dir: Path) -> MaterialCountingOutputPaths:
    output_dir = Path(output_dir)
    predictions_dir = output_dir / "predictions"
    reports_dir = output_dir / "reports"
    predictions_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    results: list[MaterialCountResult] = []
    for row in _read_manifest_rows(manifest_csv):
        if row.get("scenario_candidate") != REBAR_MATERIAL_COUNTING:
            continue
        if row.get("media_type") != "image":
            continue
        results.append(
            analyze_material_count_image(
                Path(row["file_path"]),
                media_id=row["media_id"],
                file_name=row["file_name"],
                capture_tags=_split_semicolon(row.get("capture_tags", "")),
                existing_quality_flags=_split_semicolon(row.get("quality_flags", "")),
                output_dir=predictions_dir,
            )
        )

    report_csv = reports_dir / "rebar_material_count_report.csv"
    report_json = reports_dir / "rebar_material_count_report.json"
    summary_md = reports_dir / "rebar_material_count_summary.md"

    _write_csv(report_csv, [_result_csv_row(result) for result in results])
    report_json.write_text(
        json.dumps([_result_json_row(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )
    summary_md.write_text(_build_summary(results), encoding="utf-8-sig")
    return MaterialCountingOutputPaths(report_csv=report_csv, report_json=report_json, summary_md=summary_md)


def _load_analysis_image(image_path: Path) -> tuple[Image.Image, float]:
    with Image.open(image_path) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        width, height = source.size
        scale = min(1.0, MAX_ANALYSIS_DIMENSION / max(width, height))
        if scale < 1.0:
            source = source.resize((int(width * scale), int(height * scale)), Image.Resampling.BILINEAR)
        return source, scale


def _count_plausibility_flags(image_path: Path, detections: Sequence[BarEndDetection]) -> list[str]:
    if not detections:
        return []
    with Image.open(image_path) as source:
        source = ImageOps.exif_transpose(source)
        width, height = source.size
    center_x = sum(detection.center_x for detection in detections) / len(detections)
    center_y = sum(detection.center_y for detection in detections) / len(detections)
    flags: list[str] = []
    if center_x < width * 0.25 or center_x > width * 0.75 or center_y < height * 0.18 or center_y > height * 0.72:
        flags.append("endpoint_cluster_off_center")
    return flags


def _rust_endpoint_mask(image: Image.Image) -> np.ndarray:
    array = np.asarray(image).astype(np.int16)
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    mask = (
        (red > 70)
        & (green > 35)
        & (blue < 145)
        & ((red - blue) > 30)
        & ((green - blue) > 5)
        & (red >= green)
        & ((green * 100) >= (red * 38))
    )
    image_mask = Image.fromarray(mask.astype(np.uint8) * 255)
    image_mask = image_mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    return np.asarray(image_mask) > 0


def _connected_components(mask: np.ndarray) -> list[dict[str, int | tuple[int, int, int, int]]]:
    height, width = mask.shape
    visited = np.zeros(mask.shape, dtype=bool)
    components: list[dict[str, int | tuple[int, int, int, int]]] = []
    for start_y, start_x in zip(*np.where(mask)):
        if visited[start_y, start_x]:
            continue
        stack = [(int(start_x), int(start_y))]
        visited[start_y, start_x] = True
        area = 0
        sum_x = 0
        sum_y = 0
        min_x = max_x = int(start_x)
        min_y = max_y = int(start_y)

        while stack:
            x, y = stack.pop()
            area += 1
            sum_x += x
            sum_y += y
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            for next_y in range(max(0, y - 1), min(height, y + 2)):
                for next_x in range(max(0, x - 1), min(width, x + 2)):
                    if visited[next_y, next_x] or not mask[next_y, next_x]:
                        continue
                    visited[next_y, next_x] = True
                    stack.append((next_x, next_y))

        components.append(
            {
                "area": area,
                "sum_x": sum_x,
                "sum_y": sum_y,
                "bbox": (min_x, min_y, max_x, max_y),
            }
        )
    return components


def _keep_largest_spatial_cluster(detections: Sequence[BarEndDetection]) -> list[BarEndDetection]:
    if len(detections) <= 2:
        return list(detections)

    median_radius = float(np.median([detection.radius for detection in detections]))
    neighbor_distance = max(45.0, median_radius * 4.0)
    remaining = set(range(len(detections)))
    clusters: list[list[int]] = []

    while remaining:
        start = remaining.pop()
        cluster = [start]
        stack = [start]
        while stack:
            current = stack.pop()
            current_detection = detections[current]
            for candidate in list(remaining):
                candidate_detection = detections[candidate]
                distance = (
                    (current_detection.center_x - candidate_detection.center_x) ** 2
                    + (current_detection.center_y - candidate_detection.center_y) ** 2
                ) ** 0.5
                if distance <= neighbor_distance:
                    remaining.remove(candidate)
                    cluster.append(candidate)
                    stack.append(candidate)
        clusters.append(cluster)

    largest_cluster = max(clusters, key=len)
    if len(largest_cluster) < 3:
        return list(detections)
    return [detections[index] for index in largest_cluster]


def _write_annotated_image(
    image_path: Path,
    output_dir: Path,
    media_id: str,
    file_name: str,
    *,
    detections: Sequence[BarEndDetection],
    note: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    show_indexes = len(detections) <= 40
    for detection in detections:
        x1, y1, x2, y2 = detection.bbox
        draw.ellipse((x1, y1, x2, y2), outline=(255, 230, 0), width=6 if not show_indexes else 4)
        if show_indexes:
            draw.text((x1, max(0, y1 - 16)), str(detection.index), fill=(255, 230, 0))
    if show_indexes:
        draw.rectangle((8, 8, 460, 48), fill=(0, 0, 0))
        draw.text((16, 16), note, fill=(255, 255, 255))
    annotated_path = output_dir / f"{media_id}_{Path(file_name).stem}_bar_count.jpg"
    image.save(annotated_path, quality=92)
    return annotated_path


def _read_manifest_rows(manifest_csv: Path) -> list[dict[str, str]]:
    with Path(manifest_csv).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _split_semicolon(value: str) -> list[str]:
    return [part for part in value.split(";") if part]


def _result_csv_row(result: MaterialCountResult) -> dict[str, str]:
    return {
        "media_id": result.media_id,
        "file_name": result.file_name,
        "analysis_status": result.analysis_status,
        "detected_count": str(result.detected_count),
        "confidence": f"{result.confidence:.3f}",
        "human_review_state": result.human_review_state,
        "review_flags": ";".join(result.review_flags),
        "annotated_image_path": result.annotated_image_path,
    }


def _result_json_row(result: MaterialCountResult) -> dict[str, object]:
    row = asdict(result)
    row["detections"] = [asdict(detection) for detection in result.detections]
    return row


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "media_id",
        "file_name",
        "analysis_status",
        "detected_count",
        "confidence",
        "human_review_state",
        "review_flags",
        "annotated_image_path",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_summary(results: Sequence[MaterialCountResult]) -> str:
    counted = [result for result in results if result.analysis_status == "counted"]
    recapture = [result for result in results if result.analysis_status == "recapture_required"]
    lines = [
        "# Rebar Material Counting Demo Summary",
        "",
        f"Analyzed images: {len(results)}",
        f"Counted endpoint images: {len(counted)}",
        f"Recapture required: {len(recapture)}",
        "",
        "## Results",
        "",
    ]
    for result in results:
        lines.append(
            f"- {result.media_id} {result.file_name}: {result.analysis_status}, "
            f"count={result.detected_count}, confidence={result.confidence:.3f}, "
            f"flags={';'.join(result.review_flags) or 'none'}"
        )
    lines.extend(
        [
            "",
            "## Typical Error Cases",
            "",
            "- Side-view or occluded piles are unsuitable for exact counting and should be recaptured from the endpoint face.",
            "- Rust-colored wood, straps, distant bars, or background clutter can become false candidates; off-center clusters are kept for review rather than accepted as counts.",
            "- Adjacent bar ends may merge in simple color segmentation, so the first demo output remains assisted evidence pending human review.",
        ]
    )
    return "\n".join(lines) + "\n"


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
