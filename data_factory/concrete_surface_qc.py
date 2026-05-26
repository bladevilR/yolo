"""Prototype concrete surface anomaly screening for field QC."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from data_factory.field_qc_inventory import CONCRETE_SURFACE_QC


MAX_ANALYSIS_DIMENSION = 900


@dataclass(frozen=True)
class ConcreteQcConfig:
    defect_classes: tuple[str, ...]


@dataclass(frozen=True)
class ConcreteAnomaly:
    anomaly_class: str
    confidence: float
    bbox: tuple[int, int, int, int]
    pixel_area: int


@dataclass(frozen=True)
class ConcreteSurfaceResult:
    media_id: str
    file_name: str
    analysis_status: str
    measurement_status: str
    human_review_state: str
    review_flags: list[str]
    annotated_image_path: str
    anomalies: list[ConcreteAnomaly]


@dataclass(frozen=True)
class ConcreteSurfaceOutputPaths:
    report_csv: Path
    report_json: Path
    summary_md: Path


def analyze_concrete_surface_image(
    image_path: Path,
    *,
    media_id: str,
    file_name: str,
    capture_tags: Sequence[str],
    existing_quality_flags: Sequence[str],
    config: ConcreteQcConfig,
    output_dir: Path,
    requires_measurement: bool = False,
) -> ConcreteSurfaceResult:
    tags = set(capture_tags)
    flags = _dedupe([*existing_quality_flags])
    analysis_status = "screened"

    if "concrete_overview" not in tags and "concrete_closeup" not in tags:
        flags = _dedupe([*flags, "concrete_surface_view_required"])
        analysis_status = "recapture_required"

    measurement_status = "not_requested"
    if requires_measurement and "scale_reference" in tags:
        measurement_status = "calibrated_estimate_available"
    elif requires_measurement:
        measurement_status = "visual_only_no_scale"
        flags = _dedupe([*flags, "scale_reference_required_for_measurement"])

    anomalies = detect_surface_anomalies(image_path, config)
    if not anomalies:
        flags = _dedupe([*flags, "no_visible_anomaly_detected"])
    elif analysis_status == "screened":
        analysis_status = "screened"

    annotated_path = _write_annotated_image(
        image_path,
        output_dir,
        media_id,
        file_name,
        anomalies=anomalies,
        note=f"anomalies={len(anomalies)} {measurement_status}",
    )
    return ConcreteSurfaceResult(
        media_id=media_id,
        file_name=file_name,
        analysis_status=analysis_status,
        measurement_status=measurement_status,
        human_review_state="awaiting_review",
        review_flags=flags,
        annotated_image_path=str(annotated_path),
        anomalies=anomalies,
    )


def detect_surface_anomalies(image_path: Path, config: ConcreteQcConfig) -> list[ConcreteAnomaly]:
    image, scale = _load_analysis_image(image_path)
    array = np.asarray(image).astype(np.float32)
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    gray = (red + green + blue) / 3.0
    median_gray = float(np.median(gray))
    dark_mask = gray < median_gray - 35.0
    bright_mask = gray > median_gray + 35.0
    color_spread = np.maximum.reduce([red, green, blue]) - np.minimum.reduce([red, green, blue])
    stain_mask = color_spread > 45.0
    mask = dark_mask | bright_mask | stain_mask
    mask_image = Image.fromarray(mask.astype(np.uint8) * 255)
    mask_image = mask_image.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(5))
    components = _connected_components(np.asarray(mask_image) > 0)

    width, height = image.size
    image_area = width * height
    min_area = max(18, int(image_area * 0.0005))
    max_area = max(180, int(image_area * 0.35))
    anomalies: list[ConcreteAnomaly] = []
    for component in components:
        area = int(component["area"])
        if area < min_area or area > max_area:
            continue
        x1, y1, x2, y2 = component["bbox"]
        box_width = x2 - x1 + 1
        box_height = y2 - y1 + 1
        if box_width < 4 or box_height < 4:
            continue
        anomaly_class = _classify_anomaly(box_width, box_height, area, config.defect_classes)
        confidence = round(min(0.95, 0.5 + min(0.4, area / max(1, image_area) * 20)), 3)
        anomalies.append(
            ConcreteAnomaly(
                anomaly_class=anomaly_class,
                confidence=confidence,
                bbox=(
                    int(round(x1 / scale)),
                    int(round(y1 / scale)),
                    int(round(x2 / scale)),
                    int(round(y2 / scale)),
                ),
                pixel_area=int(round(area / (scale * scale))),
            )
        )

    anomalies.sort(key=lambda anomaly: anomaly.pixel_area, reverse=True)
    return anomalies[:12]


def link_concrete_overview_closeups(rows: Sequence[Mapping[str, str]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    current_overview: dict[str, object] | None = None
    for row in rows:
        if row.get("scenario_candidate") != CONCRETE_SURFACE_QC:
            continue
        tags = set(_split_semicolon(str(row.get("capture_tags", ""))))
        if "concrete_overview" in tags or current_overview is None:
            current_overview = {"overview_media_id": row.get("media_id", ""), "closeup_media_ids": []}
            records.append(current_overview)
        elif "concrete_closeup" in tags:
            current_overview["closeup_media_ids"].append(row.get("media_id", ""))
    return records


def run_concrete_surface_qc_demo(
    manifest_csv: Path,
    output_dir: Path,
    *,
    config: ConcreteQcConfig,
) -> ConcreteSurfaceOutputPaths:
    output_dir = Path(output_dir)
    predictions_dir = output_dir / "predictions"
    reports_dir = output_dir / "reports"
    predictions_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_manifest_rows(manifest_csv)
    evidence_links = link_concrete_overview_closeups(rows)
    results: list[ConcreteSurfaceResult] = []
    for row in rows:
        if row.get("scenario_candidate") != CONCRETE_SURFACE_QC:
            continue
        if row.get("media_type") != "image":
            continue
        capture_tags = _split_semicolon(row.get("capture_tags", ""))
        results.append(
            analyze_concrete_surface_image(
                Path(row["file_path"]),
                media_id=row["media_id"],
                file_name=row["file_name"],
                capture_tags=capture_tags,
                existing_quality_flags=_split_semicolon(row.get("quality_flags", "")),
                config=config,
                output_dir=predictions_dir,
                requires_measurement="scale_reference" in capture_tags,
            )
        )

    report_csv = reports_dir / "concrete_surface_qc_report.csv"
    report_json = reports_dir / "concrete_surface_qc_report.json"
    summary_md = reports_dir / "concrete_surface_qc_summary.md"
    _write_csv(report_csv, [_result_csv_row(result) for result in results])
    report_json.write_text(
        json.dumps(
            {"evidence_links": evidence_links, "results": [asdict(result) for result in results]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8-sig",
    )
    summary_md.write_text(_build_summary(results, evidence_links), encoding="utf-8-sig")
    return ConcreteSurfaceOutputPaths(report_csv=report_csv, report_json=report_json, summary_md=summary_md)


def _load_analysis_image(image_path: Path) -> tuple[Image.Image, float]:
    with Image.open(image_path) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        width, height = source.size
        scale = min(1.0, MAX_ANALYSIS_DIMENSION / max(width, height))
        if scale < 1.0:
            source = source.resize((int(width * scale), int(height * scale)), Image.Resampling.BILINEAR)
        return source, scale


def _classify_anomaly(width: int, height: int, area: int, classes: Sequence[str]) -> str:
    aspect = max(width, height) / max(1, min(width, height))
    fill_ratio = area / max(1, width * height)
    if "crack" in classes and aspect >= 4.0 and fill_ratio < 0.38:
        return "crack"
    if "repair_patch" in classes and area > width * height * 0.55:
        return "repair_patch"
    if "color_difference" in classes:
        return "color_difference"
    if "surface_anomaly_needs_review" in classes:
        return "surface_anomaly_needs_review"
    return classes[0] if classes else "surface_anomaly_needs_review"


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


def _write_annotated_image(
    image_path: Path,
    output_dir: Path,
    media_id: str,
    file_name: str,
    *,
    anomalies: Sequence[ConcreteAnomaly],
    note: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    for index, anomaly in enumerate(anomalies, start=1):
        draw.rectangle(anomaly.bbox, outline=(255, 210, 0), width=4)
        x1, y1, _, _ = anomaly.bbox
        draw.text((x1, max(0, y1 - 16)), f"{index}:{anomaly.anomaly_class}", fill=(255, 210, 0))
    draw.rectangle((8, 8, 560, 40), fill=(0, 0, 0))
    draw.text((16, 16), note, fill=(255, 255, 255))
    path = output_dir / f"{media_id}_{Path(file_name).stem}_concrete_qc.jpg"
    image.save(path, quality=92)
    return path


def _read_manifest_rows(manifest_csv: Path) -> list[dict[str, str]]:
    with Path(manifest_csv).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _split_semicolon(value: str) -> list[str]:
    return [part for part in value.split(";") if part]


def _result_csv_row(result: ConcreteSurfaceResult) -> dict[str, str]:
    top_anomaly = result.anomalies[0] if result.anomalies else None
    return {
        "media_id": result.media_id,
        "file_name": result.file_name,
        "analysis_status": result.analysis_status,
        "measurement_status": result.measurement_status,
        "anomaly_count": str(len(result.anomalies)),
        "top_anomaly_class": "" if top_anomaly is None else top_anomaly.anomaly_class,
        "top_confidence": "" if top_anomaly is None else f"{top_anomaly.confidence:.3f}",
        "human_review_state": result.human_review_state,
        "review_flags": ";".join(result.review_flags),
        "annotated_image_path": result.annotated_image_path,
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    fieldnames = [
        "media_id",
        "file_name",
        "analysis_status",
        "measurement_status",
        "anomaly_count",
        "top_anomaly_class",
        "top_confidence",
        "human_review_state",
        "review_flags",
        "annotated_image_path",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_summary(results: Sequence[ConcreteSurfaceResult], evidence_links: Sequence[Mapping[str, object]]) -> str:
    lines = [
        "# Concrete Surface QC Demo Summary",
        "",
        f"Analyzed images: {len(results)}",
        "",
        "## Evidence Links",
        "",
    ]
    for record in evidence_links:
        lines.append(f"- overview {record['overview_media_id']}: closeups={','.join(record['closeup_media_ids'])}")
    lines.extend(["", "## Results", ""])
    for result in results:
        top = result.anomalies[0].anomaly_class if result.anomalies else "none"
        lines.append(
            f"- {result.media_id} {result.file_name}: anomalies={len(result.anomalies)}, "
            f"top={top}, measurement={result.measurement_status}, flags={';'.join(result.review_flags) or 'none'}"
        )
    lines.extend(
        [
            "",
            "## Sample Gap",
            "",
            "- Current field photos are enough for visual-anomaly screening, but more positive samples are needed for honeycombing, pitting, exposed rebar, holes, and cracks.",
            "- Outputs are suspected regions for human review, not final concrete quality acceptance.",
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
