import csv
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from data_factory.ppe_review_queue import create_review_queue_workspace


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_image(path: Path) -> None:
    image = np.full((120, 160, 3), 180, dtype=np.uint8)
    cv2.rectangle(image, (50, 20), (90, 100), (20, 80, 220), -1)
    cv2.imwrite(str(path), image)


class PpeReviewQueueTests(unittest.TestCase):
    def test_create_review_queue_workspace_copies_images_labels_and_crops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = root / "images"
            labels = root / "labels"
            images.mkdir()
            labels.mkdir()
            write_image(images / "sample.jpg")
            (labels / "sample.txt").write_text("0 0.5 0.5 0.2 0.6\n", encoding="utf-8")
            write_csv(
                root / "queue.csv",
                [
                    {
                        "image_name": "sample.jpg",
                        "queue_source": "accepted_event",
                        "source_index": "1",
                        "person_confidence": "0.9000",
                        "x1": "50",
                        "y1": "20",
                        "x2": "90",
                        "y2": "100",
                        "status": "ok",
                        "review_reason": "helmet_rule_only",
                        "recommendation": "manual_check_event",
                    }
                ],
            )

            rows = create_review_queue_workspace(root / "queue.csv", images, labels, root / "workspace")

            self.assertEqual(1, len(rows))
            self.assertTrue((root / "workspace" / "images" / "sample.jpg").exists())
            self.assertEqual(
                "0 0.5 0.5 0.2 0.6\n",
                (root / "workspace" / "labels_reviewed" / "sample.txt").read_text(encoding="utf-8"),
            )
            self.assertTrue(Path(rows[0]["crop_path"]).exists())
            queue = read_csv(root / "workspace" / "review_queue_workspace.csv")
            self.assertEqual("q0001", queue[0]["review_id"])
            self.assertEqual("todo", queue[0]["manual_status"])
            self.assertTrue((root / "workspace" / "crop_contact_sheets" / "review_queue_contact_sheet_001.jpg").exists())

    def test_create_review_queue_workspace_writes_empty_label_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = root / "images"
            labels = root / "labels"
            images.mkdir()
            labels.mkdir()
            write_image(images / "sample.jpg")
            write_csv(
                root / "queue.csv",
                [
                    {
                        "image_name": "sample.jpg",
                        "queue_source": "rejected_candidate",
                        "source_index": "1",
                        "person_confidence": "0.3000",
                        "x1": "10",
                        "y1": "15",
                        "x2": "50",
                        "y2": "90",
                        "status": "suppressed",
                        "review_reason": "possible_worker_low_confidence",
                        "recommendation": "check_if_worker_then_fix_label",
                    }
                ],
            )

            create_review_queue_workspace(root / "queue.csv", images, labels, root / "workspace")

            self.assertEqual("", (root / "workspace" / "labels_reviewed" / "sample.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
