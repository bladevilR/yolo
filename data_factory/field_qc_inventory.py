"""Field QC media inventory helpers for the AI inspection pilot."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from PIL import Image, ImageFilter, ImageOps, ImageStat


FIELD_QC_CAPTURE_WORKFLOW = "field_qc_capture_workflow"
REBAR_MATERIAL_COUNTING = "rebar_material_counting"
REBAR_COUPLER_THREAD_QC = "rebar_coupler_thread_qc"
CONCRETE_SURFACE_QC = "concrete_surface_qc"
UNKNOWN_SCENARIO = "unknown"

SCENARIOS = (
    REBAR_MATERIAL_COUNTING,
    REBAR_COUPLER_THREAD_QC,
    CONCRETE_SURFACE_QC,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

REQUIRED_METADATA_FIELDS = (
    "project",
    "inspection_area",
    "floor_or_zone",
    "component_or_material_id",
    "photographer",
    "timestamp",
    "scenario",
)

REVIEW_STATES = ("awaiting_review", "accepted", "rejected", "corrected")

UNDEREXPOSED_MEAN_THRESHOLD = 15.0
OVEREXPOSED_MEAN_THRESHOLD = 245.0
LOW_DETAIL_STDDEV_THRESHOLD = 2.0
LOW_EDGE_MEAN_THRESHOLD = 1.0


@dataclass(frozen=True)
class QualityAssessment:
    review_status: str
    quality_flags: list[str]


@dataclass(frozen=True)
class MediaItem:
    media_id: str
    file_path: str
    file_name: str
    media_type: str
    scenario_candidate: str
    width: int | None
    height: int | None
    bytes: int
    capture_tags: list[str]
    capture_notes: str
    review_status: str
    quality_flags: list[str]


@dataclass(frozen=True)
class InventoryOutputPaths:
    manifest_csv: Path
    manifest_json: Path
    review_csv: Path
    summary_md: Path


def validate_metadata(metadata: Mapping[str, str]) -> list[str]:
    return [field for field in REQUIRED_METADATA_FIELDS if not str(metadata.get(field, "")).strip()]


def assess_capture_quality(
    scenario: str,
    capture_tags: Sequence[str] | None = None,
    *,
    requires_measurement: bool = False,
) -> QualityAssessment:
    tags = set(capture_tags or [])
    flags: list[str] = []
    status = "ready"

    for tag, flag in (
        ("blur", "blur_present"),
        ("glare", "glare_present"),
        ("occlusion", "occlusion_present"),
        ("cropped", "target_cropped"),
        ("target_missing", "target_missing"),
        ("overexposed", "overexposed"),
        ("underexposed", "underexposed"),
    ):
        if tag in tags:
            flags.append(flag)
            if tag == "target_missing":
                status = "needs_recapture"
            elif status == "ready":
                status = "needs_review"

    if scenario == REBAR_MATERIAL_COUNTING:
        if "endpoint_face" not in tags:
            flags.append("endpoint_face_required_for_exact_count")
            status = "needs_recapture" if "side_view" in tags else "needs_review"
    elif scenario == REBAR_COUPLER_THREAD_QC:
        if "coupler_closeup" not in tags:
            flags.append("coupler_closeup_required")
            status = "needs_recapture"
        if "both_sides_visible" not in tags:
            flags.append("both_coupler_sides_required")
            status = "needs_review" if status == "ready" else status
    elif scenario == CONCRETE_SURFACE_QC:
        if "concrete_overview" not in tags and "concrete_closeup" not in tags:
            flags.append("concrete_surface_view_required")
            status = "needs_recapture"
    else:
        flags.append("scenario_unassigned")
        status = "needs_review"

    if requires_measurement and "scale_reference" not in tags:
        flags.append("scale_reference_required_for_measurement")
        status = "needs_review" if status == "ready" else status

    return QualityAssessment(review_status=status, quality_flags=flags)


def infer_image_quality_tags(path: Path) -> list[str]:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("L")
        stats = ImageStat.Stat(image)
        mean = stats.mean[0]
        stddev = stats.stddev[0]
        edge_mean = ImageStat.Stat(image.filter(ImageFilter.FIND_EDGES)).mean[0]

    tags: list[str] = []
    if mean < UNDEREXPOSED_MEAN_THRESHOLD:
        tags.append("underexposed")
    if mean > OVEREXPOSED_MEAN_THRESHOLD:
        tags.append("overexposed")
    if stddev < LOW_DETAIL_STDDEV_THRESHOLD or (
        stddev < LOW_DETAIL_STDDEV_THRESHOLD * 2 and edge_mean < LOW_EDGE_MEAN_THRESHOLD
    ):
        tags.append("blur")
    return tags


def build_media_manifest(
    source_dir: Path,
    *,
    overrides: Mapping[str, Mapping[str, object]] | None = None,
) -> list[MediaItem]:
    overrides = overrides or {}
    items: list[MediaItem] = []
    supported = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
    files = sorted(path for path in Path(source_dir).iterdir() if path.is_file() and path.suffix.lower() in supported)

    for index, path in enumerate(files, start=1):
        item_override = overrides.get(path.name, {})
        scenario = str(item_override.get("scenario_candidate", UNKNOWN_SCENARIO))
        capture_tags = list(item_override.get("capture_tags", []))
        media_type = _media_type(path)
        width, height = _image_size(path) if media_type == "image" else (None, None)
        if media_type == "image":
            capture_tags = _dedupe_tags([*capture_tags, *infer_image_quality_tags(path)])
        requires_measurement = bool(item_override.get("requires_measurement", False))
        assessment = assess_capture_quality(
            scenario,
            capture_tags,
            requires_measurement=requires_measurement,
        )
        items.append(
            MediaItem(
                media_id=f"field-qc-{index:04d}",
                file_path=str(path),
                file_name=path.name,
                media_type=media_type,
                scenario_candidate=scenario,
                width=width,
                height=height,
                bytes=path.stat().st_size,
                capture_tags=capture_tags,
                capture_notes=str(item_override.get("capture_notes", "")),
                review_status=assessment.review_status,
                quality_flags=assessment.quality_flags,
            )
        )

    return items


def build_current_survey_overrides(file_names: Iterable[str]) -> dict[str, dict[str, object]]:
    image_names = sorted(name for name in file_names if Path(name).suffix.lower() in IMAGE_EXTENSIONS)
    overrides: dict[str, dict[str, object]] = {}

    for index, name in enumerate(image_names, start=1):
        if 1 <= index <= 10:
            overrides[name] = {
                "scenario_candidate": CONCRETE_SURFACE_QC,
                "capture_tags": ["concrete_overview" if index in {1, 2, 3, 4, 5, 8, 9} else "concrete_closeup"],
                "capture_notes": "concrete surface survey photo",
            }
        elif 11 <= index <= 14:
            overrides[name] = {
                "scenario_candidate": REBAR_MATERIAL_COUNTING,
                "capture_tags": ["side_view", "occlusion"],
                "capture_notes": "side-view rebar pile; exact count needs endpoint recapture",
            }
        elif 15 <= index <= 19:
            overrides[name] = {
                "scenario_candidate": REBAR_COUPLER_THREAD_QC,
                "capture_tags": ["coupler_closeup", "both_sides_visible" if index in {15, 17, 19} else "occlusion"],
                "capture_notes": "coupler exposed-thread close-up",
            }
        elif 20 <= index <= 22:
            overrides[name] = {
                "scenario_candidate": REBAR_MATERIAL_COUNTING,
                "capture_tags": ["endpoint_face" if index == 22 else "side_view", "occlusion" if index in {20, 21} else "material_label"],
                "capture_notes": "rebar material counting candidate",
            }
        else:
            overrides[name] = {
                "scenario_candidate": UNKNOWN_SCENARIO,
                "capture_tags": ["site_note"],
                "capture_notes": "site note or handwritten context photo",
            }

    return overrides


def write_inventory_outputs(output_dir: Path, manifest: Sequence[MediaItem]) -> InventoryOutputPaths:
    output_dir = Path(output_dir)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    for scenario in SCENARIOS:
        (output_dir / scenario / "raw").mkdir(parents=True, exist_ok=True)
        (output_dir / scenario / "labels").mkdir(parents=True, exist_ok=True)
        (output_dir / scenario / "predictions").mkdir(parents=True, exist_ok=True)
        (output_dir / scenario / "reports").mkdir(parents=True, exist_ok=True)

    manifest_csv = reports_dir / "media_manifest.csv"
    manifest_json = reports_dir / "media_manifest.json"
    review_csv = reports_dir / "capture_quality_review.csv"
    summary_md = reports_dir / "current_survey_summary.md"

    rows = [_row_for_csv(item) for item in manifest]
    _write_csv(manifest_csv, rows)
    manifest_json.write_text(
        json.dumps([asdict(item) for item in manifest], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(
        review_csv,
        [
            {
                "media_id": item.media_id,
                "file_name": item.file_name,
                "scenario_candidate": item.scenario_candidate,
                "review_status": item.review_status,
                "quality_flags": ";".join(item.quality_flags),
                "capture_tags": ";".join(item.capture_tags),
                "capture_notes": item.capture_notes,
            }
            for item in manifest
        ],
    )
    summary_md.write_text(build_summary_markdown(manifest), encoding="utf-8-sig")

    return InventoryOutputPaths(
        manifest_csv=manifest_csv,
        manifest_json=manifest_json,
        review_csv=review_csv,
        summary_md=summary_md,
    )


def build_summary_markdown(manifest: Sequence[MediaItem]) -> str:
    scenario_counts = _count_by(item.scenario_candidate for item in manifest)
    status_counts = _count_by(item.review_status for item in manifest)
    lines = [
        "# AI质检现场素材初评汇总",
        "",
        f"媒体总数: {len(manifest)}",
        "",
        "## 场景数量",
        "",
    ]
    for scenario in sorted(scenario_counts):
        lines.append(f"- {scenario}: {scenario_counts[scenario]}")
    lines.extend(["", "## 初评状态数量", ""])
    for status in sorted(status_counts):
        lines.append(f"- {status}: {status_counts[status]}")
    lines.extend(
        [
            "",
            "## 初步交付判断",
            "",
            "- 钢筋材料点数优先适配端面照片；侧面堆放或遮挡严重的素材需要补拍或人工复核。",
            "- 钢筋套筒露丝检查具备试点基础，但需要两侧可见，并配置项目认可的露丝阈值。",
            "- 混凝土面检查建议先做疑似异常提示，待补充更多蜂窝、麻面、露筋、裂缝等正样本后再做稳定判定。",
            "- 未归类的视频或现场记录照片需要人工指定场景后，再进入模型评估。",
            "",
        ]
    )
    return "\n".join(lines)


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "other"


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        return image.size


def _dedupe_tags(tags: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)
    return deduped


def _row_for_csv(item: MediaItem) -> dict[str, str]:
    return {
        "media_id": item.media_id,
        "file_path": item.file_path,
        "file_name": item.file_name,
        "media_type": item.media_type,
        "scenario_candidate": item.scenario_candidate,
        "width": "" if item.width is None else str(item.width),
        "height": "" if item.height is None else str(item.height),
        "bytes": str(item.bytes),
        "capture_tags": ";".join(item.capture_tags),
        "capture_notes": item.capture_notes,
        "review_status": item.review_status,
        "quality_flags": ";".join(item.quality_flags),
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _count_by(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts
