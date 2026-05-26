"""Rulebook configuration for the field AI QC pilot."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from data_factory.field_qc_inventory import (
    CONCRETE_SURFACE_QC,
    REBAR_COUPLER_THREAD_QC,
    REBAR_MATERIAL_COUNTING,
    REQUIRED_METADATA_FIELDS,
)


CONCRETE_SURFACE_CLASSES = (
    "honeycombing",
    "pitting",
    "exposed_aggregate",
    "exposed_rebar",
    "hole",
    "crack",
    "leakage_mark",
    "repair_patch",
    "color_difference",
    "formwork_seam",
    "surface_damage",
    "surface_anomaly_needs_review",
)


@dataclass(frozen=True)
class MaterialCountingRule:
    unit: str
    status: str
    exact_count_requires_endpoint_face: bool
    occluded_or_side_view_behavior: str


@dataclass(frozen=True)
class CouplerThreadRule:
    threshold_status: str
    max_visible_threads_per_side: int | None
    max_exposed_length_mm: float | None
    measurement_requires_scale: bool
    missing_threshold_behavior: str


@dataclass(frozen=True)
class ConcreteSurfaceRule:
    classes: tuple[str, ...]
    unknown_anomaly_behavior: str
    measurement_requires_scale: bool


@dataclass(frozen=True)
class FieldQcRulebook:
    required_metadata_fields: tuple[str, ...]
    material_counting: MaterialCountingRule
    coupler_thread_qc: CouplerThreadRule
    concrete_surface_qc: ConcreteSurfaceRule
    capture_guidance: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldQcRulebook":
        return cls(
            required_metadata_fields=tuple(data["required_metadata_fields"]),
            material_counting=MaterialCountingRule(**data["material_counting"]),
            coupler_thread_qc=CouplerThreadRule(**data["coupler_thread_qc"]),
            concrete_surface_qc=ConcreteSurfaceRule(
                classes=tuple(data["concrete_surface_qc"]["classes"]),
                unknown_anomaly_behavior=data["concrete_surface_qc"]["unknown_anomaly_behavior"],
                measurement_requires_scale=data["concrete_surface_qc"]["measurement_requires_scale"],
            ),
            capture_guidance=dict(data["capture_guidance"]),
        )


def build_default_rulebook() -> FieldQcRulebook:
    return FieldQcRulebook(
        required_metadata_fields=tuple(REQUIRED_METADATA_FIELDS),
        material_counting=MaterialCountingRule(
            unit="bar",
            status="pilot_default_pending_confirmation",
            exact_count_requires_endpoint_face=True,
            occluded_or_side_view_behavior="estimate_only_or_manual_review",
        ),
        coupler_thread_qc=CouplerThreadRule(
            threshold_status="requires_project_confirmation",
            max_visible_threads_per_side=None,
            max_exposed_length_mm=None,
            measurement_requires_scale=True,
            missing_threshold_behavior="needs_standard_confirmation",
        ),
        concrete_surface_qc=ConcreteSurfaceRule(
            classes=CONCRETE_SURFACE_CLASSES,
            unknown_anomaly_behavior="surface_anomaly_needs_review",
            measurement_requires_scale=True,
        ),
        capture_guidance={
            REBAR_MATERIAL_COUNTING: (
                "Capture the full endpoint face of the bundle, keep every bar end in frame, "
                "avoid straps/gloves/tarps covering endpoints, and include material label or batch context."
            ),
            REBAR_COUPLER_THREAD_QC: (
                "Capture the complete coupler from a side-on angle with both sides visible, "
                "avoid glare and motion blur, and include a scale reference when exposed length is required."
            ),
            CONCRETE_SURFACE_QC: (
                "Capture one overview image for location and one close-up for the anomaly; "
                "include a ruler or known-size reference when width, length, or area measurement is required."
            ),
        },
    )


def find_pending_confirmations(rulebook: FieldQcRulebook) -> list[str]:
    pending: list[str] = []
    if rulebook.material_counting.status.endswith("pending_confirmation"):
        pending.append("material_counting.unit")
    if rulebook.coupler_thread_qc.max_visible_threads_per_side is None:
        pending.append("coupler_thread_qc.max_visible_threads_per_side")
    if rulebook.coupler_thread_qc.max_exposed_length_mm is None:
        pending.append("coupler_thread_qc.max_exposed_length_mm")
    return pending


def write_rulebook_outputs(output_dir: Path, rulebook: FieldQcRulebook) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "field_qc_rulebook.json"
    markdown_path = output_dir / "field_qc_rulebook.md"

    json_path.write_text(json.dumps(rulebook.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_rulebook_markdown(rulebook), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def build_rulebook_markdown(rulebook: FieldQcRulebook) -> str:
    pending = find_pending_confirmations(rulebook)
    lines = [
        "# Field QC Rulebook",
        "",
        "## Required Metadata",
        "",
    ]
    for field in rulebook.required_metadata_fields:
        lines.append(f"- {field}")
    lines.extend(
        [
            "",
            "## Material Counting",
            "",
            f"- Unit: {rulebook.material_counting.unit}",
            f"- Status: {rulebook.material_counting.status}",
            f"- Exact Count Requires Endpoint Face: {rulebook.material_counting.exact_count_requires_endpoint_face}",
            f"- Occluded Or Side View Behavior: {rulebook.material_counting.occluded_or_side_view_behavior}",
            "",
            "## Coupler Thread QC",
            "",
            f"- Threshold Status: {rulebook.coupler_thread_qc.threshold_status}",
            f"- Max Visible Threads Per Side: {rulebook.coupler_thread_qc.max_visible_threads_per_side}",
            f"- Max Exposed Length Mm: {rulebook.coupler_thread_qc.max_exposed_length_mm}",
            f"- Measurement Requires Scale: {rulebook.coupler_thread_qc.measurement_requires_scale}",
            f"- Missing Threshold Behavior: {rulebook.coupler_thread_qc.missing_threshold_behavior}",
            "",
            "## Concrete Surface Classes",
            "",
        ]
    )
    for class_name in rulebook.concrete_surface_qc.classes:
        lines.append(f"- {class_name}")
    lines.extend(["", "## Capture Guidance", ""])
    for scenario, guidance in sorted(rulebook.capture_guidance.items()):
        lines.append(f"- {scenario}: {guidance}")
    lines.extend(["", "## Pending Confirmations", ""])
    if pending:
        for item in pending:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)
