import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from data_factory.rebar_material_counter import (
    analyze_material_count_image,
    run_material_counting_demo,
)


def make_endpoint_fixture(path: Path, count: int = 5) -> None:
    image = Image.new("RGB", (220, 150), (48, 62, 60))
    draw = ImageDraw.Draw(image)
    centers = [(45, 48), (92, 44), (139, 48), (68, 96), (118, 96), (166, 94)]
    for center in centers[:count]:
        x, y = center
        draw.ellipse((x - 15, y - 15, x + 15, y + 15), fill=(184, 107, 35), outline=(85, 47, 18), width=3)
        draw.line((x - 9, y, x + 9, y), fill=(222, 160, 74), width=2)
    image.save(path)


def make_endpoint_with_decoys(path: Path) -> None:
    image = Image.new("RGB", (320, 220), (56, 66, 62))
    draw = ImageDraw.Draw(image)
    for x, y in [(132, 82), (178, 82), (110, 128), (156, 130), (202, 128)]:
        draw.ellipse((x - 15, y - 15, x + 15, y + 15), fill=(184, 107, 35), outline=(85, 47, 18), width=3)
    draw.ellipse((14, 18, 44, 48), fill=(184, 107, 35), outline=(85, 47, 18), width=3)
    draw.rectangle((242, 160, 308, 202), fill=(174, 102, 38))
    draw.ellipse((260, 22, 306, 80), fill=(168, 38, 48))
    image.save(path)


def make_off_center_rust_cluster(path: Path) -> None:
    image = Image.new("RGB", (420, 280), (56, 66, 62))
    draw = ImageDraw.Draw(image)
    for x, y in [(40, 210), (74, 210), (108, 210), (142, 210), (176, 210)]:
        draw.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(184, 107, 35), outline=(85, 47, 18), width=3)
    image.save(path)


def make_dense_endpoint_fixture(path: Path) -> None:
    image = Image.new("RGB", (640, 420), (54, 64, 61))
    draw = ImageDraw.Draw(image)
    centers = []
    for row, y in enumerate(range(80, 320, 42)):
        offset = 0 if row % 2 == 0 else 22
        for x in range(115 + offset, 525, 46):
            centers.append((x, y))
    for x, y in centers:
        draw.ellipse((x - 19, y - 18, x + 20, y + 19), fill=(184, 107, 35), outline=(75, 43, 18), width=3)
        draw.line((x - 10, y, x + 10, y), fill=(220, 160, 74), width=2)
    image.save(path)


def make_manifest(path: Path, image_path: Path, *, tags: str = "endpoint_face;material_label") -> None:
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
                "media_id": "field-qc-0001",
                "file_path": str(image_path),
                "file_name": image_path.name,
                "media_type": "image",
                "scenario_candidate": "rebar_material_counting",
                "capture_tags": tags,
                "quality_flags": "",
            }
        )


class RebarMaterialCounterTests(unittest.TestCase):
    def test_analyze_material_count_image_counts_clear_endpoint_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "bars.jpg"
            output_dir = root / "predictions"
            make_endpoint_fixture(image_path, count=5)

            result = analyze_material_count_image(
                image_path,
                media_id="field-qc-0001",
                file_name="bars.jpg",
                capture_tags=["endpoint_face"],
                existing_quality_flags=[],
                output_dir=output_dir,
            )

            self.assertEqual(result.analysis_status, "counted")
            self.assertEqual(result.detected_count, 5)
            self.assertGreaterEqual(result.confidence, 0.7)
            self.assertEqual(result.human_review_state, "awaiting_review")
            self.assertTrue(Path(result.annotated_image_path).exists())

    def test_analyze_material_count_image_ignores_far_color_decoys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "bars_with_decoys.jpg"
            make_endpoint_with_decoys(image_path)

            result = analyze_material_count_image(
                image_path,
                media_id="field-qc-0003",
                file_name="bars_with_decoys.jpg",
                capture_tags=["endpoint_face"],
                existing_quality_flags=[],
                output_dir=root / "predictions",
            )

            self.assertEqual(result.analysis_status, "counted")
            self.assertEqual(result.detected_count, 5)

    def test_analyze_material_count_image_marks_off_center_cluster_for_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "off_center.jpg"
            make_off_center_rust_cluster(image_path)

            result = analyze_material_count_image(
                image_path,
                media_id="field-qc-0004",
                file_name="off_center.jpg",
                capture_tags=["endpoint_face"],
                existing_quality_flags=[],
                output_dir=root / "predictions",
            )

            self.assertEqual(result.analysis_status, "needs_review")
            self.assertIn("endpoint_cluster_off_center", result.review_flags)

    def test_analyze_material_count_image_marks_dense_endpoint_counts_for_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "dense_endpoint.jpg"
            make_dense_endpoint_fixture(image_path)

            result = analyze_material_count_image(
                image_path,
                media_id="field-qc-0005",
                file_name="dense_endpoint.jpg",
                capture_tags=["endpoint_face"],
                existing_quality_flags=[],
                output_dir=root / "predictions",
            )

            self.assertEqual(result.analysis_status, "needs_review")
            self.assertGreaterEqual(result.detected_count, 30)
            self.assertIn("high_density_count_requires_manual_review", result.review_flags)

    def test_analyze_material_count_image_rejects_side_view_for_exact_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "side_view.jpg"
            make_endpoint_fixture(image_path, count=5)

            result = analyze_material_count_image(
                image_path,
                media_id="field-qc-0002",
                file_name="side_view.jpg",
                capture_tags=["side_view", "occlusion"],
                existing_quality_flags=["endpoint_face_required_for_exact_count"],
                output_dir=root / "predictions",
            )

            self.assertEqual(result.analysis_status, "recapture_required")
            self.assertEqual(result.detected_count, 0)
            self.assertIn("endpoint_face_required_for_exact_count", result.review_flags)
            self.assertIn("occlusion_present", result.review_flags)

    def test_run_material_counting_demo_writes_csv_json_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "bars.jpg"
            manifest_path = root / "media_manifest.csv"
            output_dir = root / "material_counting"
            make_endpoint_fixture(image_path, count=6)
            make_manifest(manifest_path, image_path)

            paths = run_material_counting_demo(manifest_path, output_dir)

            self.assertTrue(paths.report_csv.exists())
            self.assertTrue(paths.report_json.exists())
            self.assertTrue(paths.summary_md.exists())
            with paths.report_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["media_id"], "field-qc-0001")
            self.assertEqual(rows[0]["detected_count"], "6")
            self.assertEqual(rows[0]["analysis_status"], "counted")
            summary = paths.summary_md.read_text(encoding="utf-8-sig")
            self.assertIn("field-qc-0001", summary)
            self.assertIn("Typical Error Cases", summary)


if __name__ == "__main__":
    unittest.main()
