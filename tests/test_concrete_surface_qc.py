import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from data_factory.concrete_surface_qc import (
    ConcreteQcConfig,
    analyze_concrete_surface_image,
    link_concrete_overview_closeups,
    run_concrete_surface_qc_demo,
)


def make_crack_fixture(path: Path) -> None:
    image = Image.new("RGB", (260, 180), (154, 154, 146))
    draw = ImageDraw.Draw(image)
    draw.rectangle((150, 28, 226, 84), fill=(190, 188, 176))
    draw.line((42, 52, 84, 82, 118, 78, 170, 124, 220, 132), fill=(42, 42, 40), width=5)
    image.save(path)


def make_surface_stain_fixture(path: Path) -> None:
    image = Image.new("RGB", (260, 180), (154, 154, 146))
    draw = ImageDraw.Draw(image)
    draw.ellipse((74, 48, 178, 126), fill=(108, 116, 112))
    image.save(path)


def make_long_formwork_mark_fixture(path: Path) -> None:
    image = Image.new("RGB", (260, 180), (154, 154, 146))
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 76, 228, 102), fill=(104, 108, 104))
    image.save(path)


def make_manifest(path: Path, overview_path: Path, closeup_path: Path) -> None:
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
                "media_id": "field-qc-0201",
                "file_path": str(overview_path),
                "file_name": overview_path.name,
                "media_type": "image",
                "scenario_candidate": "concrete_surface_qc",
                "capture_tags": "concrete_overview",
                "quality_flags": "",
            }
        )
        writer.writerow(
            {
                "media_id": "field-qc-0202",
                "file_path": str(closeup_path),
                "file_name": closeup_path.name,
                "media_type": "image",
                "scenario_candidate": "concrete_surface_qc",
                "capture_tags": "concrete_closeup",
                "quality_flags": "",
            }
        )


class ConcreteSurfaceQcTests(unittest.TestCase):
    def test_analyze_concrete_surface_image_detects_visible_anomaly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "crack.jpg"
            make_crack_fixture(image_path)

            result = analyze_concrete_surface_image(
                image_path,
                media_id="field-qc-0202",
                file_name="crack.jpg",
                capture_tags=["concrete_closeup"],
                existing_quality_flags=[],
                config=ConcreteQcConfig(defect_classes=("crack", "repair_patch", "surface_anomaly_needs_review")),
                output_dir=root / "predictions",
                requires_measurement=True,
            )

            self.assertEqual(result.analysis_status, "screened")
            self.assertGreaterEqual(len(result.anomalies), 1)
            self.assertIn(result.anomalies[0].anomaly_class, {"crack", "surface_anomaly_needs_review"})
            self.assertEqual(result.measurement_status, "visual_only_no_scale")
            self.assertTrue(Path(result.annotated_image_path).exists())

    def test_analyze_concrete_surface_image_keeps_unclear_anomaly_generic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "stain.jpg"
            make_surface_stain_fixture(image_path)

            result = analyze_concrete_surface_image(
                image_path,
                media_id="field-qc-0204",
                file_name="stain.jpg",
                capture_tags=["concrete_closeup"],
                existing_quality_flags=[],
                config=ConcreteQcConfig(defect_classes=("crack", "surface_anomaly_needs_review")),
                output_dir=root / "predictions",
            )

            self.assertGreaterEqual(len(result.anomalies), 1)
            self.assertEqual(result.anomalies[0].anomaly_class, "surface_anomaly_needs_review")

    def test_analyze_concrete_surface_image_does_not_call_broad_mark_crack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "formwork_mark.jpg"
            make_long_formwork_mark_fixture(image_path)

            result = analyze_concrete_surface_image(
                image_path,
                media_id="field-qc-0205",
                file_name="formwork_mark.jpg",
                capture_tags=["concrete_closeup"],
                existing_quality_flags=[],
                config=ConcreteQcConfig(defect_classes=("crack", "surface_anomaly_needs_review")),
                output_dir=root / "predictions",
            )

            self.assertGreaterEqual(len(result.anomalies), 1)
            self.assertEqual(result.anomalies[0].anomaly_class, "surface_anomaly_needs_review")

    def test_analyze_concrete_surface_image_allows_measurement_only_with_scale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "scaled_crack.jpg"
            make_crack_fixture(image_path)

            result = analyze_concrete_surface_image(
                image_path,
                media_id="field-qc-0203",
                file_name="scaled_crack.jpg",
                capture_tags=["concrete_closeup", "scale_reference"],
                existing_quality_flags=[],
                config=ConcreteQcConfig(defect_classes=("crack", "surface_anomaly_needs_review")),
                output_dir=root / "predictions",
                requires_measurement=True,
            )

            self.assertEqual(result.measurement_status, "calibrated_estimate_available")

    def test_link_concrete_overview_closeups_pairs_nearby_media(self):
        records = link_concrete_overview_closeups(
            [
                {
                    "media_id": "field-qc-0201",
                    "scenario_candidate": "concrete_surface_qc",
                    "capture_tags": "concrete_overview",
                },
                {
                    "media_id": "field-qc-0202",
                    "scenario_candidate": "concrete_surface_qc",
                    "capture_tags": "concrete_closeup",
                },
            ]
        )

        self.assertEqual(records[0]["overview_media_id"], "field-qc-0201")
        self.assertEqual(records[0]["closeup_media_ids"], ["field-qc-0202"])

    def test_run_concrete_surface_qc_demo_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            overview_path = root / "overview.jpg"
            closeup_path = root / "closeup.jpg"
            manifest_path = root / "media_manifest.csv"
            output_dir = root / "concrete_qc"
            make_crack_fixture(overview_path)
            make_crack_fixture(closeup_path)
            make_manifest(manifest_path, overview_path, closeup_path)

            paths = run_concrete_surface_qc_demo(
                manifest_path,
                output_dir,
                config=ConcreteQcConfig(defect_classes=("crack", "repair_patch", "surface_anomaly_needs_review")),
            )

            self.assertTrue(paths.report_csv.exists())
            self.assertTrue(paths.report_json.exists())
            self.assertTrue(paths.summary_md.exists())
            with paths.report_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["media_id"], "field-qc-0202")
            self.assertIn("overview field-qc-0201", paths.summary_md.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
