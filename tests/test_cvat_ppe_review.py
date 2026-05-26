import csv
import json
import tempfile
import unittest
from pathlib import Path

from data_factory.cvat_ppe_review import (
    build_qc_review_queue,
    ensure_safe_snapshot_output,
    seed_review_manifest,
    write_cvat_review_instructions,
    write_snapshot_from_export,
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sample_cvat_export() -> dict:
    return {
        "task_id": 1,
        "labels": [[1, "person"], [2, "helmet"], [3, "vest"]],
        "frames": [
            {"name": "a.jpg", "width": 100, "height": 50},
            {"name": "b.jpg", "width": 200, "height": 100},
        ],
        "annotations": {
            "version": 0,
            "tags": [],
            "tracks": [],
            "shapes": [
                {
                    "type": "rectangle",
                    "label_id": 1,
                    "frame": 0,
                    "outside": False,
                    "points": [40, 10, 60, 40],
                },
                {
                    "type": "rectangle",
                    "label_id": 3,
                    "frame": 0,
                    "outside": False,
                    "points": [20, 10, 40, 30],
                },
            ],
        },
    }


class CvatPpeReviewTests(unittest.TestCase):
    def test_write_snapshot_from_export_preserves_backup_and_writes_yolo_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            historical = root / "task1_manual_backup.json"
            historical.write_text("{}", encoding="utf-8")
            output = root / "cvat_snapshots" / "task1_20260522_120000"

            manifest = write_snapshot_from_export(
                sample_cvat_export(),
                output,
                snapshot_id="task1_20260522_120000",
                historical_backup_path=historical,
                source_url="http://localhost:8080/tasks/1/jobs/1",
            )

            self.assertTrue((output / "annotations_backup.json").exists())
            self.assertEqual((output / "labels_yolo" / "a.txt").read_text(encoding="utf-8").splitlines(), [
                "0 0.50000000 0.50000000 0.20000000 0.60000000",
                "2 0.30000000 0.40000000 0.20000000 0.40000000",
            ])
            self.assertEqual((output / "labels_yolo" / "b.txt").read_text(encoding="utf-8"), "")
            self.assertEqual(manifest["frame_count"], 2)
            self.assertEqual(manifest["label_file_count"], 2)
            self.assertEqual(manifest["box_count"], 2)
            self.assertEqual(manifest["empty_label_files"], 1)
            self.assertEqual(manifest["class_counts"], {"person": 1, "helmet": 0, "vest": 1})
            self.assertEqual(manifest["historical_backups"][0]["path"], str(historical))

    def test_safe_snapshot_output_rejects_live_import_and_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live_import_child = root / "cvat_import" / "task1_snapshot"
            existing = root / "cvat_snapshots" / "task1_existing"
            existing.mkdir(parents=True)

            with self.assertRaises(ValueError):
                ensure_safe_snapshot_output(live_import_child, dataset_root=root)
            with self.assertRaises(FileExistsError):
                ensure_safe_snapshot_output(existing, dataset_root=root)

    def test_seed_review_manifest_merges_supervision_qc_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = write_snapshot_from_export(sample_cvat_export(), root / "snapshot", snapshot_id="s1")
            qc_dir = root / "qc"
            qc_dir.mkdir()
            summary = {
                "images": [
                    {"image_name": "a.jpg", "label_name": "a.txt", "detections": 2, "issues": 2},
                    {"image_name": "b.jpg", "label_name": "b.txt", "detections": 0, "issues": 0},
                ],
                "issues": [
                    {"issue": "duplicate_box", "image_name": "a.jpg", "label_name": "a.txt", "detection_index": 1},
                    {"issue": "orphan_ppe_box", "image_name": "a.jpg", "label_name": "a.txt", "detection_index": 2},
                ],
            }
            (qc_dir / "qc_summary.json").write_text(json.dumps(summary), encoding="utf-8")

            rows = seed_review_manifest(snapshot, qc_dir / "qc_summary.json", root / "review_manifest.csv")

            self.assertEqual(len(rows), 2)
            a_row = next(row for row in rows if row["image_name"] == "a.jpg")
            b_row = next(row for row in rows if row["image_name"] == "b.jpg")
            self.assertEqual(a_row["manual_status"], "todo")
            self.assertEqual(a_row["qc_flags"], "duplicate_box|orphan_ppe_box")
            self.assertEqual(a_row["duplicate_box_count"], 1)
            self.assertEqual(a_row["orphan_ppe_box_count"], 1)
            self.assertEqual(b_row["qc_flags"], "empty_label")
            self.assertEqual(Path(a_row["overlay_path"]).name, "a.jpg")
            self.assertEqual(Path(a_row["contact_sheet_path"]).name, "boxed_contact_sheet_001.jpg")

    def test_build_review_queue_writes_issue_rows_and_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = write_snapshot_from_export(sample_cvat_export(), root / "snapshot", snapshot_id="s1")
            qc_dir = root / "qc"
            qc_dir.mkdir()
            summary = {
                "images": [
                    {"image_name": "a.jpg", "label_name": "a.txt", "detections": 2, "issues": 2},
                    {"image_name": "b.jpg", "label_name": "b.txt", "detections": 0, "issues": 0},
                ],
                "issues": [
                    {"issue": "duplicate_box", "image_name": "a.jpg", "label_name": "a.txt", "detection_index": 1},
                    {"issue": "orphan_ppe_box", "image_name": "a.jpg", "label_name": "a.txt", "detection_index": 2},
                ],
            }
            summary_path = qc_dir / "qc_summary.json"
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            manifest_rows = seed_review_manifest(snapshot, summary_path, root / "review_manifest.csv")

            queue_rows = build_qc_review_queue(
                manifest_rows,
                summary_path,
                root / "qc_review_queue.csv",
            )
            write_cvat_review_instructions(root / "CVAT_REVIEW_INSTRUCTIONS.md", snapshot, root / "qc_review_queue.csv")

            self.assertEqual([row["issue_type"] for row in queue_rows], ["duplicate_box", "orphan_ppe_box", "empty_label"])
            self.assertEqual(queue_rows[0]["manual_status"], "todo")
            self.assertEqual(queue_rows[0]["recommended_action"], "Check whether this is a duplicate same-class box; remove or merge in CVAT if confirmed.")
            self.assertTrue((root / "qc_review_queue.csv").exists())
            instructions = (root / "CVAT_REVIEW_INSTRUCTIONS.md").read_text(encoding="utf-8")
            self.assertIn("manual_status=done", instructions)
            self.assertIn("stress-only", instructions)


if __name__ == "__main__":
    unittest.main()
