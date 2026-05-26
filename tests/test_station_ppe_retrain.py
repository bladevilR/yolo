import csv
import json
import tempfile
import unittest
from pathlib import Path

from data_factory.station_ppe_retrain import (
    CLASS_MAP_3,
    build_acceptance_review_candidates,
    count_yolo_dataset,
    create_multimodal_draft_package,
    write_acceptance_review_package,
    write_baseline_report,
)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class StationPpeRetrainTests(unittest.TestCase):
    def test_count_yolo_dataset_counts_splits_classes_and_label_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for split in ("train", "val", "test"):
                (root / "images" / split).mkdir(parents=True)
                (root / "labels" / split).mkdir(parents=True)

            (root / "images" / "train" / "a.jpg").write_bytes(b"a")
            (root / "labels" / "train" / "a.txt").write_text(
                "0 0.5 0.5 0.2 0.3\n2 0.5 0.6 0.1 0.2\n",
                encoding="utf-8",
            )
            (root / "images" / "val" / "b.jpg").write_bytes(b"b")
            (root / "labels" / "val" / "b.txt").write_text("", encoding="utf-8")
            (root / "images" / "test" / "c.jpg").write_bytes(b"c")
            (root / "labels" / "test" / "c.txt").write_text("5 0.5 0.5 0.2 0.3\n", encoding="utf-8")

            summary = count_yolo_dataset(root, CLASS_MAP_3)

            self.assertEqual(summary["image_counts"], {"train": 1, "val": 1, "test": 1})
            self.assertEqual(summary["label_file_counts"], {"train": 1, "val": 1, "test": 1})
            self.assertEqual(summary["empty_label_files"], {"train": 0, "val": 1, "test": 0})
            self.assertEqual(summary["class_counts"], {"person": 1, "helmet": 0, "vest": 1})
            self.assertEqual(summary["class_counts_by_split"]["train"], {"person": 1, "helmet": 0, "vest": 1})
            self.assertEqual(len(summary["invalid_labels"]), 1)
            self.assertEqual(summary["invalid_labels"][0]["class_id"], "5")

    def test_build_acceptance_review_candidates_keeps_event_rows_and_adds_unique_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            priority = root / "priority"
            v5 = root / "v5"
            qa = root / "qa300" / "sample.csv"
            write_csv(
                priority / "labeling_queue.csv",
                [
                    {
                        "priority_rank": "1",
                        "profile": "main_train",
                        "source_video": "camera_a.mp4",
                        "image_name": "p0001__0001_camera_a.jpg",
                        "label_name": "p0001__0001_camera_a.txt",
                        "source_image_path": str(root / "qa300" / "images" / "0001_camera_a.jpg"),
                        "source_label_path": str(root / "qa300" / "labels" / "0001_camera_a.txt"),
                        "required_action": "Correct person/helmet boxes; manually add vest.",
                        "qc_flags": "vest_manual",
                        "visual_note": "vest mostly missing",
                        "manual_status": "codex_reviewed",
                        "manual_notes": "codex_auto_review",
                        "local_image_path": str(priority / "images" / "p0001__0001_camera_a.jpg"),
                        "reviewed_label_path": str(priority / "labels_reviewed" / "p0001__0001_camera_a.txt"),
                        "pseudo_original_label_path": str(priority / "labels_pseudo_original" / "p0001__0001_camera_a.txt"),
                    },
                    {
                        "priority_rank": "2",
                        "profile": "hard_case",
                        "source_video": "camera_b.mp4",
                        "image_name": "p0002__0002_camera_b.jpg",
                        "label_name": "p0002__0002_camera_b.txt",
                        "source_image_path": str(root / "qa300" / "images" / "0002_camera_b.jpg"),
                        "source_label_path": str(root / "qa300" / "labels" / "0002_camera_b.txt"),
                        "required_action": "Fix hard case.",
                        "qc_flags": "many_boxes",
                        "visual_note": "many boxes",
                        "manual_status": "done",
                        "manual_notes": "human reviewed",
                        "local_image_path": str(priority / "images" / "p0002__0002_camera_b.jpg"),
                        "reviewed_label_path": str(priority / "labels_reviewed" / "p0002__0002_camera_b.txt"),
                        "pseudo_original_label_path": str(priority / "labels_pseudo_original" / "p0002__0002_camera_b.txt"),
                    },
                ],
            )
            write_csv(
                v5 / "review_queue_workspace.csv",
                [
                    {
                        "image_name": "p0001__0001_camera_a.jpg",
                        "queue_source": "accepted_event",
                        "source_index": "1",
                        "status": "no_vest",
                        "review_reason": "suspected_ppe_issue",
                        "recommendation": "manual_check_event",
                        "review_id": "q0001",
                        "label_name": "p0001__0001_camera_a.txt",
                        "manual_decision": "todo",
                        "manual_status": "todo",
                        "manual_notes": "",
                        "local_image_path": str(v5 / "images" / "p0001__0001_camera_a.jpg"),
                        "crop_path": str(v5 / "crops" / "q0001.jpg"),
                        "current_label_path": str(v5 / "labels_current" / "p0001__0001_camera_a.txt"),
                        "reviewed_label_path": str(v5 / "labels_reviewed" / "p0001__0001_camera_a.txt"),
                        "codex_suggested_decision": "ppe_status_fix",
                        "codex_review_priority": "high",
                        "codex_visual_note": "confirm vest",
                    },
                    {
                        "image_name": "p0001__0001_camera_a.jpg",
                        "queue_source": "rejected_candidate",
                        "source_index": "2",
                        "status": "suppressed",
                        "review_reason": "possible_worker_low_confidence",
                        "recommendation": "check_if_worker_then_fix_label",
                        "review_id": "q0002",
                        "label_name": "p0001__0001_camera_a.txt",
                        "manual_decision": "todo",
                        "manual_status": "todo",
                        "manual_notes": "",
                        "local_image_path": str(v5 / "images" / "p0001__0001_camera_a.jpg"),
                        "crop_path": str(v5 / "crops" / "q0002.jpg"),
                        "current_label_path": str(v5 / "labels_current" / "p0001__0001_camera_a.txt"),
                        "reviewed_label_path": str(v5 / "labels_reviewed" / "p0001__0001_camera_a.txt"),
                        "codex_suggested_decision": "true_worker_fix_label",
                        "codex_review_priority": "high",
                        "codex_visual_note": "possible missed worker",
                    },
                ],
            )
            write_csv(
                qa,
                [
                    {
                        "sample_index": "1",
                        "sample_image_path": str(root / "qa300" / "images" / "0001_camera_a.jpg"),
                        "sample_label_path": str(root / "qa300" / "labels" / "0001_camera_a.txt"),
                        "video_name": "camera_a.mp4",
                        "frame_index": "0",
                        "timestamp_seconds": "0.0",
                        "split": "train",
                        "label_status": "empty_needs_annotation",
                    },
                    {
                        "sample_index": "2",
                        "sample_image_path": str(root / "qa300" / "images" / "0002_camera_b.jpg"),
                        "sample_label_path": str(root / "qa300" / "labels" / "0002_camera_b.txt"),
                        "video_name": "camera_b.mp4",
                        "frame_index": "10",
                        "timestamp_seconds": "1.0",
                        "split": "train",
                        "label_status": "empty_needs_annotation",
                    },
                    {
                        "sample_index": "3",
                        "sample_image_path": str(root / "qa300" / "images" / "0003_camera_c.jpg"),
                        "sample_label_path": str(root / "qa300" / "labels" / "0003_camera_c.txt"),
                        "video_name": "camera_c.mp4",
                        "frame_index": "20",
                        "timestamp_seconds": "2.0",
                        "split": "val",
                        "label_status": "empty_needs_annotation",
                    },
                    {
                        "sample_index": "4",
                        "sample_image_path": str(root / "qa300" / "images" / "0004_camera_c.jpg"),
                        "sample_label_path": str(root / "qa300" / "labels" / "0004_camera_c.txt"),
                        "video_name": "camera_c.mp4",
                        "frame_index": "30",
                        "timestamp_seconds": "3.0",
                        "split": "test",
                        "label_status": "empty_needs_annotation",
                    },
                ],
            )

            package = build_acceptance_review_candidates(
                priority_workspace=priority,
                v5_workspace=v5,
                qa_sample_csv=qa,
                min_unique_images=4,
            )

            self.assertEqual(len(package.rows), 6)
            self.assertEqual(package.summary["unique_images"], 4)
            self.assertEqual(package.summary["target_min_unique_images"], 4)
            self.assertEqual(package.summary["additional_unique_images_needed"], 0)
            self.assertEqual(package.summary["row_counts_by_source"]["priority_batch"], 2)
            self.assertEqual(package.summary["row_counts_by_source"]["v5_review_queue"], 2)
            self.assertEqual(package.summary["row_counts_by_source"]["qa300_additional"], 2)

            codex_row = next(row for row in package.rows if row["candidate_id"] == "priority-0001")
            human_row = next(row for row in package.rows if row["candidate_id"] == "priority-0002")
            event_row = next(row for row in package.rows if row["candidate_id"] == "v5-q0001")
            additional_row = next(row for row in package.rows if row["candidate_id"] == "additional-0001")

            self.assertEqual(codex_row["eligible_for_v3_training"], "no")
            self.assertEqual(human_row["eligible_for_v3_training"], "yes")
            self.assertEqual(event_row["review_intent"], "event_error_review")
            self.assertEqual(additional_row["manual_status"], "todo")
            self.assertEqual(additional_row["review_intent"], "human_review_full_label")

    def test_write_acceptance_review_package_writes_csv_summary_and_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                {
                    "candidate_id": "priority-0001",
                    "source_queue": "priority_batch",
                    "image_name": "a.jpg",
                    "manual_status": "todo",
                    "eligible_for_v3_training": "no",
                }
            ]
            summary = {
                "total_rows": 1,
                "unique_images": 1,
                "target_min_unique_images": 200,
                "additional_unique_images_needed": 199,
            }

            write_acceptance_review_package(root / "out", rows, summary)

            written_rows = read_csv(root / "out" / "review_candidates.csv")
            self.assertEqual(written_rows[0]["candidate_id"], "priority-0001")
            written_summary = json.loads((root / "out" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(written_summary["unique_images"], 1)
            readme = (root / "out" / "README.md").read_text(encoding="utf-8")
            self.assertIn("manual_status=done", readme)
            self.assertIn("no_helmet", readme)

    def test_write_baseline_report_counts_strict_v5_event_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset"
            (dataset / "images" / "train").mkdir(parents=True)
            (dataset / "labels" / "train").mkdir(parents=True)
            (dataset / "images" / "train" / "a.jpg").write_bytes(b"a")
            (dataset / "labels" / "train" / "a.txt").write_text("0 0.5 0.5 0.2 0.3\n", encoding="utf-8")
            write_csv(
                dataset / "manifest.csv",
                [
                    {
                        "image_name": "a.jpg",
                        "split": "train",
                        "profile": "main_train",
                        "manual_status": "codex_reviewed",
                    }
                ],
            )
            write_csv(
                root / "results.csv",
                [
                    {
                        "epoch": "1",
                        "metrics/precision(B)": "0.8",
                        "metrics/recall(B)": "0.7",
                        "metrics/mAP50(B)": "0.6",
                        "metrics/mAP50-95(B)": "0.5",
                    }
                ],
            )
            strict_v5 = root / "strict_v5"
            write_csv(
                strict_v5 / "ppe_events.csv",
                [
                    {"image_name": "a.jpg", "status": "ok", "event_decision": "auto_demo_ok"},
                    {"image_name": "b.jpg", "status": "no_vest", "event_decision": "needs_review"},
                ],
            )
            write_csv(
                strict_v5 / "ppe_review_queue.csv",
                [{"image_name": "b.jpg", "queue_source": "accepted_event"}],
            )
            write_csv(
                strict_v5 / "ppe_rejected_candidates.csv",
                [{"image_name": "c.jpg", "reason": "hard_negative"}],
            )

            write_baseline_report(
                output_path=root / "baseline.md",
                dataset_root=dataset,
                model_path=root / "best.pt",
                results_csv=root / "results.csv",
                strict_v5_dir=strict_v5,
            )

            report = (root / "baseline.md").read_text(encoding="utf-8")
            self.assertIn("Event decision counts: `{'auto_demo_ok': 1, 'needs_review': 1}`", report)

    def test_create_multimodal_draft_package_copies_unique_images_and_converts_to_three_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            image_a = source / "a.jpg"
            image_b = source / "b.jpg"
            label_a = source / "a.txt"
            label_b = source / "b.txt"
            image_a.write_bytes(b"image-a")
            image_b.write_bytes(b"image-b")
            label_a.write_text(
                "0 0.5 0.5 0.2 0.3\n2 0.5 0.4 0.1 0.1\n3 0.5 0.6 0.1 0.1\n5 0.1 0.1 0.1 0.1\n",
                encoding="utf-8",
            )
            label_b.write_text("0 0.4 0.4 0.2 0.2\n1 0.4 0.3 0.1 0.1\n2 0.4 0.5 0.1 0.1\n", encoding="utf-8")
            rows = [
                {
                    "candidate_id": "priority-0001",
                    "source_queue": "priority_batch",
                    "image_name": "a.jpg",
                    "label_name": "a.txt",
                    "local_image_path": str(image_a),
                    "reviewed_label_path": str(label_a),
                },
                {
                    "candidate_id": "v5-q0001",
                    "source_queue": "v5_review_queue",
                    "image_name": "b.jpg",
                    "label_name": "b.txt",
                    "local_image_path": str(image_b),
                    "reviewed_label_path": str(label_b),
                },
                {
                    "candidate_id": "v5-q0002",
                    "source_queue": "v5_review_queue",
                    "image_name": "b.jpg",
                    "label_name": "b.txt",
                    "local_image_path": str(image_b),
                    "reviewed_label_path": str(label_b),
                },
            ]

            summary = create_multimodal_draft_package(rows, root / "draft")

            self.assertEqual(summary["unique_images"], 2)
            self.assertEqual(summary["candidate_rows"], 3)
            self.assertEqual(summary["manual_status"], "codex_multimodal_reviewed")
            self.assertTrue((root / "draft" / "images" / "a.jpg").exists())
            label_lines = (root / "draft" / "labels_codex_multimodal_3class" / "a.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(label_lines, [
                "0 0.500000 0.500000 0.200000 0.300000",
                "1 0.500000 0.400000 0.100000 0.100000",
                "2 0.500000 0.600000 0.100000 0.100000",
            ])
            manifest = read_csv(root / "draft" / "label_review_manifest.csv")
            self.assertEqual(len(manifest), 2)
            self.assertEqual({row["manual_status"] for row in manifest}, {"codex_multimodal_reviewed"})
            self.assertEqual({row["eligible_for_v3_training"] for row in manifest}, {"no"})


if __name__ == "__main__":
    unittest.main()
