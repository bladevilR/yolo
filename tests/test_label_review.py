import csv
import tempfile
import unittest
from pathlib import Path

from data_factory.label_review import create_review_workspace, main, promote_reviewed_dataset


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class LabelReviewTests(unittest.TestCase):
    def test_create_review_workspace_copies_editable_labels_and_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "priority"
            (package / "images").mkdir(parents=True)
            (package / "labels_pseudo").mkdir()
            (package / "images" / "a.jpg").write_bytes(b"fake-image-a")
            (package / "labels_pseudo" / "a.txt").write_text("0 0.5 0.5 0.2 0.3\n", encoding="utf-8")
            write_csv(
                package / "priority_label_fix.csv",
                [
                    {
                        "priority_rank": "1",
                        "image_name": "a.jpg",
                        "label_name": "a.txt",
                        "profile": "main_train",
                        "source_video": "camera01.mp4",
                    }
                ],
            )

            rows = create_review_workspace(package, root / "review")

            self.assertEqual(len(rows), 1)
            self.assertTrue((root / "review" / "images" / "a.jpg").exists())
            self.assertEqual(
                (root / "review" / "labels_reviewed" / "a.txt").read_text(encoding="utf-8"),
                "0 0.5 0.5 0.2 0.3\n",
            )
            self.assertTrue((root / "review" / "labels_pseudo_original" / "a.txt").exists())
            queue = read_csv(root / "review" / "labeling_queue.csv")
            self.assertEqual(queue[0]["manual_status"], "todo")
            self.assertIn("a.jpg", (root / "review" / "labelimg_file_list.txt").read_text(encoding="utf-8"))

    def test_promote_reviewed_dataset_writes_yolo_splits_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "review"
            (workspace / "images").mkdir(parents=True)
            (workspace / "labels_reviewed").mkdir()
            rows = []
            for index in range(1, 11):
                image_name = f"{index:04d}.jpg"
                label_name = f"{index:04d}.txt"
                (workspace / "images" / image_name).write_bytes(f"image-{index}".encode("utf-8"))
                (workspace / "labels_reviewed" / label_name).write_text(
                    "0 0.5 0.5 0.2 0.3\n",
                    encoding="utf-8",
                )
                rows.append(
                    {
                        "priority_rank": str(index),
                        "image_name": image_name,
                        "label_name": label_name,
                        "profile": "main_train",
                        "source_video": "camera01.mp4",
                        "manual_status": "done",
                    }
                )
            write_csv(workspace / "labeling_queue.csv", rows)

            copied = promote_reviewed_dataset(
                workspace,
                root / "dataset",
                val_ratio=0.2,
                test_ratio=0.1,
            )

            split_counts = {split: sum(row["split"] == split for row in copied) for split in ("train", "val", "test")}
            self.assertEqual(split_counts, {"train": 7, "val": 2, "test": 1})
            self.assertTrue((root / "dataset" / "images" / "train" / "0001.jpg").exists())
            self.assertTrue((root / "dataset" / "labels" / "val").exists())
            self.assertIn("names:", (root / "dataset" / "data.yaml").read_text(encoding="utf-8"))
            manifest = read_csv(root / "dataset" / "manifest.csv")
            self.assertEqual(len(manifest), 10)
            self.assertEqual({row["manual_status"] for row in manifest}, {"done"})

    def test_main_returns_error_when_no_rows_match_required_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "review"
            (workspace / "images").mkdir(parents=True)
            (workspace / "labels_reviewed").mkdir()
            (workspace / "images" / "0001.jpg").write_bytes(b"image")
            (workspace / "labels_reviewed" / "0001.txt").write_text("", encoding="utf-8")
            write_csv(
                workspace / "labeling_queue.csv",
                [
                    {
                        "priority_rank": "1",
                        "image_name": "0001.jpg",
                        "label_name": "0001.txt",
                        "manual_status": "todo",
                    }
                ],
            )

            exit_code = main(
                [
                    "promote",
                    "--review-workspace",
                    str(workspace),
                    "--output",
                    str(root / "dataset"),
                    "--require-status",
                    "done",
                ]
            )

            self.assertEqual(exit_code, 2)
            self.assertFalse((root / "dataset" / "data.yaml").exists())


if __name__ == "__main__":
    unittest.main()
