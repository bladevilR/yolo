import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from data_factory.ppe_apply_triage import apply_triage_to_workspace, read_labels


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_workspace(root: Path) -> Path:
    workspace = root / "workspace"
    (workspace / "images").mkdir(parents=True)
    (workspace / "labels_reviewed").mkdir()
    Image.new("RGB", (100, 100), "white").save(workspace / "images" / "sample.jpg")
    return workspace


class PpeApplyTriageTests(unittest.TestCase):
    def test_apply_triage_adds_true_worker_person_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = make_workspace(Path(tmp))
            (workspace / "labels_reviewed" / "sample.txt").write_text("", encoding="utf-8")
            write_csv(
                workspace / "triage.csv",
                [
                    {
                        "image_name": "sample.jpg",
                        "x1": "10",
                        "y1": "20",
                        "x2": "40",
                        "y2": "80",
                        "codex_suggested_decision": "true_worker_fix_label",
                    }
                ],
            )

            summary = apply_triage_to_workspace(workspace, workspace / "triage.csv")

            labels = read_labels(workspace / "labels_codex_draft" / "sample.txt")
            self.assertEqual(1, len(labels))
            self.assertEqual(0, labels[0].class_id)
            self.assertEqual(1, summary["person_added"])

    def test_apply_triage_removes_hard_negative_overlapping_person(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = make_workspace(Path(tmp))
            (workspace / "labels_reviewed" / "sample.txt").write_text("0 0.5 0.5 0.4 0.4\n1 0.1 0.1 0.1 0.1\n", encoding="utf-8")
            write_csv(
                workspace / "triage.csv",
                [
                    {
                        "image_name": "sample.jpg",
                        "x1": "30",
                        "y1": "30",
                        "x2": "70",
                        "y2": "70",
                        "codex_suggested_decision": "hard_negative_not_worker",
                    }
                ],
            )

            summary = apply_triage_to_workspace(workspace, workspace / "triage.csv")

            labels = read_labels(workspace / "labels_codex_draft" / "sample.txt")
            self.assertEqual([1], [label.class_id for label in labels])
            self.assertEqual(1, summary["person_removed"])

    def test_apply_triage_skips_unclear_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = make_workspace(Path(tmp))
            (workspace / "labels_reviewed" / "sample.txt").write_text("", encoding="utf-8")
            write_csv(
                workspace / "triage.csv",
                [
                    {
                        "image_name": "sample.jpg",
                        "x1": "10",
                        "y1": "20",
                        "x2": "40",
                        "y2": "80",
                        "codex_suggested_decision": "unclear_skip",
                    }
                ],
            )

            summary = apply_triage_to_workspace(workspace, workspace / "triage.csv")

            labels = read_labels(workspace / "labels_codex_draft" / "sample.txt")
            self.assertEqual([], labels)
            self.assertEqual(1, summary["skipped"])


if __name__ == "__main__":
    unittest.main()
