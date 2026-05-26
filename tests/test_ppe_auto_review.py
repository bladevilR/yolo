import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from data_factory.ppe_auto_review import Label, auto_review_workspace, deduplicate_labels


def write_queue(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_queue(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class PpeAutoReviewTests(unittest.TestCase):
    def test_deduplicate_labels_removes_overlapping_same_class_boxes(self):
        labels = [
            Label(0, 0.5, 0.5, 0.4, 0.4),
            Label(0, 0.502, 0.5, 0.4, 0.4),
            Label(2, 0.5, 0.5, 0.4, 0.4),
        ]

        deduped = deduplicate_labels(labels, iou_threshold=0.8)

        self.assertEqual([label.class_id for label in deduped], [0, 2])

    def test_auto_review_workspace_adds_vest_candidate_and_marks_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "review"
            images = workspace / "images"
            labels = workspace / "labels_reviewed"
            original = workspace / "labels_pseudo_original"
            images.mkdir(parents=True)
            labels.mkdir()
            original.mkdir()

            image = Image.new("RGB", (200, 200), "gray")
            draw = ImageDraw.Draw(image)
            draw.rectangle([80, 95, 120, 150], fill=(255, 120, 0))
            image.save(images / "a.jpg")
            (labels / "a.txt").write_text("0 0.5 0.6 0.4 0.7\n", encoding="utf-8")
            (original / "a.txt").write_text("0 0.5 0.6 0.4 0.7\n", encoding="utf-8")
            write_queue(
                workspace / "labeling_queue.csv",
                [
                    {
                        "priority_rank": "1",
                        "image_name": "a.jpg",
                        "label_name": "a.txt",
                        "manual_status": "todo",
                        "manual_notes": "",
                    }
                ],
            )

            summary = auto_review_workspace(workspace)

            reviewed = (labels / "a.txt").read_text(encoding="utf-8")
            self.assertIn("\n3 ", "\n" + reviewed)
            queue = read_queue(workspace / "labeling_queue.csv")
            self.assertEqual(queue[0]["manual_status"], "codex_reviewed")
            self.assertEqual(summary["vest_added"], 1)


if __name__ == "__main__":
    unittest.main()
