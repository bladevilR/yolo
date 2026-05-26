import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from data_factory.supervision_ppe import (
    DEFAULT_CLASSES,
    load_yolo_detections,
    render_qc_outputs,
    summarize_yolo_directory,
)


class SupervisionPpeTests(unittest.TestCase):
    def test_load_yolo_detections_converts_normalized_boxes_to_pixel_xyxy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            label_path = root / "a.txt"
            label_path.write_text(
                "0 0.500000 0.500000 0.200000 0.600000\n"
                "2 0.250000 0.300000 0.100000 0.200000\n",
                encoding="utf-8",
            )

            detections, issues = load_yolo_detections(
                label_path,
                image_size=(100, 50),
                class_names=DEFAULT_CLASSES,
            )

            self.assertEqual([], issues)
            self.assertEqual(detections.class_id.tolist(), [0, 2])
            self.assertEqual(detections.xyxy.round(2).tolist(), [[40.0, 10.0, 60.0, 40.0], [20.0, 10.0, 30.0, 20.0]])

    def test_summarize_yolo_directory_reports_label_quality_issues_without_mutating_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = root / "images"
            labels = root / "labels"
            images.mkdir()
            labels.mkdir()
            Image.new("RGB", (100, 100), "white").save(images / "a.jpg")
            Image.new("RGB", (100, 100), "white").save(images / "b.jpg")
            original = (
                "0 0.500000 0.500000 0.400000 0.800000\n"
                "0 0.500000 0.500000 0.400000 0.800000\n"
                "1 0.100000 0.100000 0.100000 0.100000\n"
                "9 0.500000 0.500000 0.100000 0.100000\n"
                "2 0.500000 0.500000 0.000000 0.100000\n"
                "bad row\n"
            )
            (labels / "a.txt").write_text(original, encoding="utf-8")
            (labels / "b.txt").write_text("", encoding="utf-8")

            summary = summarize_yolo_directory(images, labels, class_names=DEFAULT_CLASSES)

            self.assertEqual(summary["image_count"], 2)
            self.assertEqual(summary["label_file_count"], 2)
            self.assertEqual(summary["empty_label_files"], 1)
            self.assertEqual(summary["class_counts"], {"person": 2, "helmet": 1, "vest": 0})
            self.assertEqual(summary["malformed_rows"], 1)
            self.assertEqual(summary["invalid_class_rows"], 1)
            self.assertEqual(summary["non_positive_boxes"], 1)
            self.assertEqual(summary["duplicate_boxes"], 1)
            self.assertEqual(summary["orphan_ppe_boxes"], 1)
            self.assertEqual((labels / "a.txt").read_text(encoding="utf-8"), original)

    def test_render_qc_outputs_writes_overlays_contact_sheets_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = root / "images"
            labels = root / "labels"
            output = root / "qc"
            images.mkdir()
            labels.mkdir()
            Image.new("RGB", (120, 80), "white").save(images / "a.jpg")
            (labels / "a.txt").write_text(
                "0 0.500000 0.500000 0.400000 0.700000\n"
                "1 0.500000 0.200000 0.120000 0.120000\n",
                encoding="utf-8",
            )

            result = render_qc_outputs(
                images,
                labels,
                output,
                class_names=DEFAULT_CLASSES,
                columns=1,
                rows=1,
            )

            self.assertTrue((output / "overlays" / "a.jpg").exists())
            self.assertTrue((output / "contact_sheets" / "boxed_contact_sheet_001.jpg").exists())
            self.assertTrue((output / "qc_summary.json").exists())
            self.assertEqual(result["summary_path"], str(output / "qc_summary.json"))
            summary = json.loads((output / "qc_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["class_counts"]["person"], 1)


if __name__ == "__main__":
    unittest.main()
