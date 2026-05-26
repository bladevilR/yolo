"""Prototype rebar coupler exposed-thread screening for field QC."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from data_factory.field_qc_inventory import REBAR_COUPLER_THREAD_QC


MAX_DETECTION_DIMENSION = 900

AMBIGUITY_TAG_FLAGS = {
    "cropped": "target_cropped",
    "glare": "glare_present",
    "blur": "blur_present",
    "rust": "rust_present",
    "overlapping_bars": "overlapping_bars_present",
    "occlusion": "occlusion_present",
}


@dataclass(frozen=True)
class CouplerThresholdConfig:
    max_visible_threads_per_side: int | None = None
    max_exposed_length_mm: float | None = None


@dataclass(frozen=True)
class CouplerThreadResult:
    media_id: str
    file_name: str
    analysis_status: str
    decision: str
    left_visible_thread_count: int
    right_visible_thread_count: int
    coupler_bbox: tuple[int, int, int, int]
    left_thread_region: tuple[int, int, int, int]
    right_thread_region: tuple[int, int, int, int]
    threshold_visible_threads: int | None
    human_review_state: str
    review_flags: list[str]
    annotated_image_path: str


@dataclass(frozen=True)
class CouplerQcOutputPaths:
    report_csv: Path
    report_json: Path
    summary_md: Path


def analyze_coupler_thread_image(
    image_path: Path,
    *,
    media_id: str,
    file_name: str,
    capture_tags: Sequence[str],
    existing_quality_flags: Sequence[str],
    threshold_config: CouplerThresholdConfig,
    output_dir: Path,
) -> CouplerThreadResult:
    tags = set(capture_tags)
    ambiguity_flags = [flag for tag, flag in AMBIGUITY_TAG_FLAGS.items() if tag in tags]
    flags = _dedupe([*existing_quality_flags, *ambiguity_flags])
    analysis_status = "screened"

    if "coupler_closeup" not in tags:
        flags = _dedupe([*flags, "coupler_closeup_required"])
        analysis_status = "recapture_required"
    if "both_sides_visible" not in tags:
        flags = _dedupe([*flags, "both_coupler_sides_required"])
        if analysis_status == "screened":
            analysis_status = "needs_review"

    coupler_bbox = detect_coupler_bbox(image_path)
    left_region, right_region = _thread_regions(coupler_bbox)
    left_count = estimate_visible_threads(image_path, left_region)
    right_count = estimate_visible_threads(image_path, right_region)

    if threshold_config.max_visible_threads_per_side is None:
        decision = "needs_standard_confirmation"
        flags = _dedupe([*flags, "exposed_thread_threshold_missing"])
    elif max(left_count, right_count) > threshold_config.max_visible_threads_per_side:
        decision = "suspected_non_compliant"
    else:
        decision = "pass_candidate"

    if flags and analysis_status == "screened" and decision in {"pass_candidate", "needs_standard_confirmation"}:
        analysis_status = "needs_review"

    annotated_path = _write_annotated_image(
        image_path,
        output_dir,
        media_id,
        file_name,
        coupler_bbox=coupler_bbox,
        left_region=left_region,
        right_region=right_region,
        note=f"L={left_count} R={right_count} {decision}",
    )
    return CouplerThreadResult(
        media_id=media_id,
        file_name=file_name,
        analysis_status=analysis_status,
        decision=decision,
        left_visible_thread_count=left_count,
        right_visible_thread_count=right_count,
        coupler_bbox=coupler_bbox,
        left_thread_region=left_region,
        right_thread_region=right_region,
        threshold_visible_threads=threshold_config.max_visible_threads_per_side,
        human_review_state="awaiting_review",
        review_flags=flags,
        annotated_image_path=str(annotated_path),
    )


def detect_coupler_bbox(image_path: Path) -> tuple[int, int, int, int]:
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    original_width, original_height = image.size
    scale = min(1.0, MAX_DETECTION_DIMENSION / max(original_width, original_height))
    if scale < 1.0:
        image = image.resize(
            (int(original_width * scale), int(original_height * scale)),
            Image.Resampling.BILINEAR,
        )
    array = np.asarray(image).astype(np.int16)
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    gray = ((red + green + blue) / 3).astype(np.int16)
    chroma = np.maximum.reduce([red, green, blue]) - np.minimum.reduce([red, green, blue])
    metal_mask = (gray > 95) & (chroma < 70)

    components = _connected_components(metal_mask)
    width, height = image.size
    image_area = width * height
    candidates: list[tuple[int, tuple[int, int, int, int]]] = []
    for component in components:
        area = component["area"]
        x1, y1, x2, y2 = component["bbox"]
        box_width = x2 - x1 + 1
        box_height = y2 - y1 + 1
        aspect = box_width / max(1, box_height)
        if area < image_area * 0.01 or area > image_area * 0.45:
            continue
        if aspect < 1.4 or aspect > 8.0:
            continue
        candidates.append((int(area), (x1, y1, x2, y2)))

    if candidates:
        x1, y1, x2, y2 = max(candidates, key=lambda candidate: candidate[0])[1]
        return (
            int(round(x1 / scale)),
            int(round(y1 / scale)),
            int(round(x2 / scale)),
            int(round(y2 / scale)),
        )

    return (
        int(original_width * 0.25),
        int(original_height * 0.35),
        int(original_width * 0.75),
        int(original_height * 0.65),
    )


def estimate_visible_threads(image_path: Path, region: tuple[int, int, int, int]) -> int:
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("L")
    crop = np.asarray(image.crop(region)).astype(np.float32)
    if crop.size == 0:
        return 0
    column_mean = crop.mean(axis=0)
    threshold = max(15.0, float(column_mean.mean() - column_mean.std() * 0.45))
    dark_columns = column_mean < threshold
    groups = _count_true_groups(dark_columns, min_width=1, max_width=max(2, crop.shape[1] // 8))
    return groups


def run_coupler_qc_demo(
    manifest_csv: Path,
    output_dir: Path,
    *,
    threshold_config: CouplerThresholdConfig,
) -> CouplerQcOutputPaths:
    output_dir = Path(output_dir)
    predictions_dir = output_dir / "predictions"
    reports_dir = output_dir / "reports"
    predictions_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    results: list[CouplerThreadResult] = []
    for row in _read_manifest_rows(manifest_csv):
        if row.get("scenario_candidate") != REBAR_COUPLER_THREAD_QC:
            continue
        if row.get("media_type") != "image":
            continue
        results.append(
            analyze_coupler_thread_image(
                Path(row["file_path"]),
                media_id=row["media_id"],
                file_name=row["file_name"],
                capture_tags=_split_semicolon(row.get("capture_tags", "")),
                existing_quality_flags=_split_semicolon(row.get("quality_flags", "")),
                threshold_config=threshold_config,
                output_dir=predictions_dir,
            )
        )

    report_csv = reports_dir / "rebar_coupler_thread_qc_report.csv"
    report_json = reports_dir / "rebar_coupler_thread_qc_report.json"
    summary_md = reports_dir / "rebar_coupler_thread_qc_summary.md"
    _write_csv(report_csv, [_result_csv_row(result) for result in results])
    report_json.write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )
    summary_md.write_text(_build_summary(results), encoding="utf-8-sig")
    return CouplerQcOutputPaths(report_csv=report_csv, report_json=report_json, summary_md=summary_md)


def _thread_regions(coupler_bbox: tuple[int, int, int, int]) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    x1, y1, x2, y2 = coupler_bbox
    width = x2 - x1
    left = (x1, y1, x1 + max(1, int(width * 0.28)), y2)
    right = (x2 - max(1, int(width * 0.28)), y1, x2, y2)
    return left, right


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
        min_x = max_x = int(start_x)
        min_y = max_y = int(start_y)
        while stack:
            x, y = stack.pop()
            area += 1
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
        components.append({"area": area, "bbox": (min_x, min_y, max_x, max_y)})
    return components


def _count_true_groups(values: np.ndarray, *, min_width: int, max_width: int) -> int:
    count = 0
    start: int | None = None
    for index, value in enumerate([*values.tolist(), False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            width = index - start
            if min_width <= width <= max_width:
                count += 1
            start = None
    return count


def _write_annotated_image(
    image_path: Path,
    output_dir: Path,
    media_id: str,
    file_name: str,
    *,
    coupler_bbox: tuple[int, int, int, int],
    left_region: tuple[int, int, int, int],
    right_region: tuple[int, int, int, int],
    note: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle(coupler_bbox, outline=(255, 230, 0), width=4)
    draw.rectangle(left_region, outline=(255, 80, 80), width=3)
    draw.rectangle(right_region, outline=(80, 180, 255), width=3)
    draw.rectangle((8, 8, 420, 40), fill=(0, 0, 0))
    draw.text((16, 16), note, fill=(255, 255, 255))
    path = output_dir / f"{media_id}_{Path(file_name).stem}_coupler_qc.jpg"
    image.save(path, quality=92)
    return path


def _read_manifest_rows(manifest_csv: Path) -> list[dict[str, str]]:
    with Path(manifest_csv).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _split_semicolon(value: str) -> list[str]:
    return [part for part in value.split(";") if part]


def _result_csv_row(result: CouplerThreadResult) -> dict[str, str]:
    return {
        "media_id": result.media_id,
        "file_name": result.file_name,
        "analysis_status": result.analysis_status,
        "decision": result.decision,
        "left_visible_thread_count": str(result.left_visible_thread_count),
        "right_visible_thread_count": str(result.right_visible_thread_count),
        "threshold_visible_threads": "" if result.threshold_visible_threads is None else str(result.threshold_visible_threads),
        "human_review_state": result.human_review_state,
        "review_flags": ";".join(result.review_flags),
        "annotated_image_path": result.annotated_image_path,
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    fieldnames = [
        "media_id",
        "file_name",
        "analysis_status",
        "decision",
        "left_visible_thread_count",
        "right_visible_thread_count",
        "threshold_visible_threads",
        "human_review_state",
        "review_flags",
        "annotated_image_path",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_summary(results: Sequence[CouplerThreadResult]) -> str:
    lines = [
        "# Rebar Coupler Thread QC Demo Summary",
        "",
        f"Analyzed images: {len(results)}",
        "",
        "## Results",
        "",
    ]
    for result in results:
        lines.append(
            f"- {result.media_id} {result.file_name}: {result.decision}, "
            f"L={result.left_visible_thread_count}, R={result.right_visible_thread_count}, "
            f"flags={';'.join(result.review_flags) or 'none'}"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- If the exposed-thread threshold is missing, the demo keeps the item in needs-standard-confirmation instead of pass/fail.",
            "- Cropped, occluded, blurred, or one-sided coupler photos require manual review or recapture.",
            "- Thread counts are visual screening evidence, not millimeter measurement, unless scale or calibration is provided.",
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
