import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from data_factory.field_qc_inventory import (
    CONCRETE_SURFACE_QC,
    REBAR_COUPLER_THREAD_QC,
    REBAR_MATERIAL_COUNTING,
    REVIEW_STATES,
    UNKNOWN_SCENARIO,
    assess_capture_quality,
    build_current_survey_overrides,
    build_media_manifest,
    infer_image_quality_tags,
    validate_metadata,
    write_inventory_outputs,
)
from scripts.build_field_qc_inventory import main as inventory_cli


def make_image(path: Path, size: tuple[int, int] = (64, 48)) -> None:
    image = Image.new("RGB", size, (128, 128, 128))
    draw = ImageDraw.Draw(image)
    for x in range(0, size[0], 8):
        draw.line((x, 0, x, size[1]), fill=(40, 40, 40), width=2)
    for y in range(0, size[1], 8):
        draw.line((0, y, size[0], y), fill=(220, 220, 220), width=1)
    image.save(path)


def make_solid_image(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (64, 48)) -> None:
    Image.new("RGB", size, color).save(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class FieldQcInventoryTests(unittest.TestCase):
    def test_build_media_manifest_uses_overrides_and_reads_image_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_image(root / "concrete.jpg", (120, 80))
            (root / "walkthrough.mp4").write_bytes(b"fake-video")

            manifest = build_media_manifest(
                root,
                overrides={
                    "concrete.jpg": {
                        "scenario_candidate": CONCRETE_SURFACE_QC,
                        "capture_tags": ["concrete_closeup", "scale_reference"],
                        "capture_notes": "surface close-up",
                    }
                },
            )

            concrete = next(item for item in manifest if item.file_name == "concrete.jpg")
            video = next(item for item in manifest if item.file_name == "walkthrough.mp4")

            self.assertEqual(concrete.scenario_candidate, CONCRETE_SURFACE_QC)
            self.assertEqual(concrete.media_type, "image")
            self.assertEqual((concrete.width, concrete.height), (120, 80))
            self.assertEqual(concrete.capture_notes, "surface close-up")
            self.assertIn("concrete_closeup", concrete.capture_tags)
            self.assertEqual(video.media_type, "video")
            self.assertIsNone(video.width)
            self.assertEqual(video.scenario_candidate, UNKNOWN_SCENARIO)

    def test_assess_capture_quality_marks_scenario_specific_review_flags(self):
        material = assess_capture_quality(
            REBAR_MATERIAL_COUNTING,
            capture_tags=["side_view", "occlusion"],
        )
        coupler = assess_capture_quality(
            REBAR_COUPLER_THREAD_QC,
            capture_tags=["coupler_closeup", "glare"],
        )
        concrete = assess_capture_quality(
            CONCRETE_SURFACE_QC,
            capture_tags=["concrete_closeup"],
            requires_measurement=True,
        )

        self.assertEqual(material.review_status, "needs_recapture")
        self.assertIn("endpoint_face_required_for_exact_count", material.quality_flags)
        self.assertIn("occlusion_present", material.quality_flags)
        self.assertEqual(coupler.review_status, "needs_review")
        self.assertIn("glare_present", coupler.quality_flags)
        self.assertEqual(concrete.review_status, "needs_review")
        self.assertIn("scale_reference_required_for_measurement", concrete.quality_flags)

    def test_assess_capture_quality_marks_cropped_and_missing_target(self):
        assessment = assess_capture_quality(
            CONCRETE_SURFACE_QC,
            capture_tags=["concrete_closeup", "cropped", "target_missing"],
        )

        self.assertEqual(assessment.review_status, "needs_recapture")
        self.assertIn("target_cropped", assessment.quality_flags)
        self.assertIn("target_missing", assessment.quality_flags)

    def test_infer_image_quality_tags_flags_exposure_and_low_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_solid_image(root / "too_dark.jpg", (0, 0, 0))
            make_solid_image(root / "too_bright.jpg", (255, 255, 255))
            make_solid_image(root / "flat_gray.jpg", (128, 128, 128))

            dark_tags = infer_image_quality_tags(root / "too_dark.jpg")
            bright_tags = infer_image_quality_tags(root / "too_bright.jpg")
            gray_tags = infer_image_quality_tags(root / "flat_gray.jpg")

            self.assertIn("underexposed", dark_tags)
            self.assertIn("overexposed", bright_tags)
            self.assertIn("blur", gray_tags)

    def test_build_media_manifest_adds_auto_quality_tags_to_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_solid_image(root / "surface.jpg", (255, 255, 255))

            manifest = build_media_manifest(
                root,
                overrides={
                    "surface.jpg": {
                        "scenario_candidate": CONCRETE_SURFACE_QC,
                        "capture_tags": ["concrete_closeup"],
                    }
                },
            )

            item = manifest[0]
            self.assertIn("overexposed", item.capture_tags)
            self.assertEqual(item.review_status, "needs_review")
            self.assertIn("overexposed", item.quality_flags)

    def test_assess_capture_quality_flags_unknown_scenario(self):
        assessment = assess_capture_quality(UNKNOWN_SCENARIO, capture_tags=[])

        self.assertEqual(assessment.review_status, "needs_review")
        self.assertEqual(assessment.quality_flags, ["scenario_unassigned"])

    def test_validate_metadata_reports_missing_required_fields(self):
        missing = validate_metadata(
            {
                "project": "demo",
                "inspection_area": "",
                "floor_or_zone": "B1",
                "component_or_material_id": "wall-01",
                "photographer": "qc",
                "timestamp": "2026-05-22T12:00:00",
                "scenario": CONCRETE_SURFACE_QC,
            }
        )

        self.assertEqual(missing, ["inspection_area"])

    def test_review_state_contract_includes_human_decision_states(self):
        self.assertEqual(
            REVIEW_STATES,
            ("awaiting_review", "accepted", "rejected", "corrected"),
        )

    def test_write_inventory_outputs_creates_layout_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "field_qc"
            source.mkdir()
            make_image(source / "bars.jpg")

            manifest = build_media_manifest(
                source,
                overrides={
                    "bars.jpg": {
                        "scenario_candidate": REBAR_MATERIAL_COUNTING,
                        "capture_tags": ["endpoint_face"],
                    }
                },
            )

            paths = write_inventory_outputs(output, manifest)

            self.assertTrue((output / REBAR_MATERIAL_COUNTING / "raw").is_dir())
            self.assertTrue((output / REBAR_COUPLER_THREAD_QC / "raw").is_dir())
            self.assertTrue((output / CONCRETE_SURFACE_QC / "raw").is_dir())
            self.assertTrue(paths.manifest_csv.exists())
            self.assertTrue(paths.review_csv.exists())
            self.assertTrue(paths.summary_md.exists())
            rows = read_csv(paths.manifest_csv)
            self.assertEqual(rows[0]["file_name"], "bars.jpg")
            self.assertEqual(rows[0]["scenario_candidate"], REBAR_MATERIAL_COUNTING)
            review_rows = read_csv(paths.review_csv)
            self.assertEqual(review_rows[0]["review_status"], "ready")
            summary = paths.summary_md.read_text(encoding="utf-8")
            self.assertIn("rebar_material_counting: 1", summary)
            self.assertIn("ready: 1", summary)

    def test_current_survey_overrides_match_known_photo_groups_by_sorted_order(self):
        names = [f"photo_{index:02d}.jpg" for index in range(1, 24)]

        overrides = build_current_survey_overrides(names)

        self.assertEqual(overrides["photo_01.jpg"]["scenario_candidate"], CONCRETE_SURFACE_QC)
        self.assertEqual(overrides["photo_11.jpg"]["scenario_candidate"], REBAR_MATERIAL_COUNTING)
        self.assertEqual(overrides["photo_15.jpg"]["scenario_candidate"], REBAR_COUPLER_THREAD_QC)
        self.assertEqual(overrides["photo_20.jpg"]["scenario_candidate"], REBAR_MATERIAL_COUNTING)
        self.assertEqual(overrides["photo_23.jpg"]["scenario_candidate"], UNKNOWN_SCENARIO)

    def test_cli_builds_inventory_outputs_with_current_survey_presets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "field_qc"
            source.mkdir()
            for index in range(1, 4):
                make_image(source / f"photo_{index:02d}.jpg")

            exit_code = inventory_cli(
                [
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                    "--current-survey-presets",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output / "reports" / "media_manifest.csv").exists())
            rows = read_csv(output / "reports" / "media_manifest.csv")
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["scenario_candidate"], CONCRETE_SURFACE_QC)

    def test_cli_file_path_execution_can_import_project_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "field_qc"
            source.mkdir()
            make_image(source / "photo_01.jpg")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(Path("scripts") / "build_field_qc_inventory.py"),
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                    "--current-survey-presets",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((output / "reports" / "media_manifest.csv").exists())


if __name__ == "__main__":
    unittest.main()
