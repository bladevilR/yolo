import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from data_factory.rebar_coupler_qc import (
    CouplerThresholdConfig,
    analyze_coupler_thread_image,
    run_coupler_qc_demo,
)


def make_coupler_fixture(path: Path, *, left_threads: int = 5, right_threads: int = 2) -> None:
    image = Image.new("RGB", (360, 180), (232, 232, 222))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 74, 350, 112), fill=(34, 36, 36))
    draw.rectangle((92, 54, 268, 130), fill=(176, 174, 160), outline=(70, 70, 66), width=3)
    for offset in range(left_threads):
        x = 104 + offset * 8
        draw.line((x, 58, x, 126), fill=(45, 45, 42), width=2)
    for offset in range(right_threads):
        x = 242 + offset * 8
        draw.line((x, 58, x, 126), fill=(45, 45, 42), width=2)
    image.save(path)


def make_manifest(path: Path, image_path: Path, *, tags: str = "coupler_closeup;both_sides_visible") -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "media_id",
                "file_path",
                "file_name",
                "media_type",
                "scenario_candidate",
                "capture_tags",
                "quality_flags",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "media_id": "field-qc-0101",
                "file_path": str(image_path),
                "file_name": image_path.name,
                "media_type": "image",
                "scenario_candidate": "rebar_coupler_thread_qc",
                "capture_tags": tags,
                "quality_flags": "",
            }
        )


class RebarCouplerQcTests(unittest.TestCase):
    def test_analyze_coupler_thread_image_applies_visible_thread_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "coupler.jpg"
            make_coupler_fixture(image_path, left_threads=5, right_threads=2)

            result = analyze_coupler_thread_image(
                image_path,
                media_id="field-qc-0101",
                file_name="coupler.jpg",
                capture_tags=["coupler_closeup", "both_sides_visible"],
                existing_quality_flags=[],
                threshold_config=CouplerThresholdConfig(max_visible_threads_per_side=3),
                output_dir=root / "predictions",
            )

            self.assertEqual(result.analysis_status, "screened")
            self.assertEqual(result.decision, "suspected_non_compliant")
            self.assertGreaterEqual(result.left_visible_thread_count, 5)
            self.assertGreaterEqual(result.right_visible_thread_count, 2)
            self.assertTrue(Path(result.annotated_image_path).exists())

    def test_analyze_coupler_thread_image_requires_standard_when_threshold_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "coupler.jpg"
            make_coupler_fixture(image_path)

            result = analyze_coupler_thread_image(
                image_path,
                media_id="field-qc-0102",
                file_name="coupler.jpg",
                capture_tags=["coupler_closeup", "both_sides_visible"],
                existing_quality_flags=[],
                threshold_config=CouplerThresholdConfig(),
                output_dir=root / "predictions",
            )

            self.assertEqual(result.decision, "needs_standard_confirmation")
            self.assertIn("exposed_thread_threshold_missing", result.review_flags)

    def test_analyze_coupler_thread_image_flags_missing_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "cropped_coupler.jpg"
            make_coupler_fixture(image_path)

            result = analyze_coupler_thread_image(
                image_path,
                media_id="field-qc-0103",
                file_name="cropped_coupler.jpg",
                capture_tags=["coupler_closeup", "occlusion"],
                existing_quality_flags=["both_coupler_sides_required"],
                threshold_config=CouplerThresholdConfig(max_visible_threads_per_side=3),
                output_dir=root / "predictions",
            )

            self.assertEqual(result.analysis_status, "needs_review")
            self.assertIn("both_coupler_sides_required", result.review_flags)

    def test_analyze_coupler_thread_image_maps_ambiguity_capture_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "ambiguous_coupler.jpg"
            make_coupler_fixture(image_path, left_threads=2, right_threads=2)

            result = analyze_coupler_thread_image(
                image_path,
                media_id="field-qc-0104",
                file_name="ambiguous_coupler.jpg",
                capture_tags=[
                    "coupler_closeup",
                    "both_sides_visible",
                    "cropped",
                    "glare",
                    "blur",
                    "rust",
                    "overlapping_bars",
                    "occlusion",
                ],
                existing_quality_flags=[],
                threshold_config=CouplerThresholdConfig(max_visible_threads_per_side=4),
                output_dir=root / "predictions",
            )

            self.assertEqual(result.analysis_status, "needs_review")
            self.assertIn("target_cropped", result.review_flags)
            self.assertIn("glare_present", result.review_flags)
            self.assertIn("blur_present", result.review_flags)
            self.assertIn("rust_present", result.review_flags)
            self.assertIn("overlapping_bars_present", result.review_flags)
            self.assertIn("occlusion_present", result.review_flags)

    def test_run_coupler_qc_demo_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "coupler.jpg"
            manifest_path = root / "media_manifest.csv"
            output_dir = root / "coupler_qc"
            make_coupler_fixture(image_path)
            make_manifest(manifest_path, image_path)

            paths = run_coupler_qc_demo(
                manifest_path,
                output_dir,
                threshold_config=CouplerThresholdConfig(max_visible_threads_per_side=3),
            )

            self.assertTrue(paths.report_csv.exists())
            self.assertTrue(paths.report_json.exists())
            self.assertTrue(paths.summary_md.exists())
            with paths.report_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["media_id"], "field-qc-0101")
            self.assertEqual(rows[0]["decision"], "suspected_non_compliant")


if __name__ == "__main__":
    unittest.main()
