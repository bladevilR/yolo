import unittest
from pathlib import Path

from data_factory.qa_package import allocate_group_counts, pick_evenly_spaced, resolve_label_source


class QaPackageTests(unittest.TestCase):
    def test_pick_evenly_spaced_keeps_edges_and_middle(self):
        items = list(range(10))

        self.assertEqual(pick_evenly_spaced(items, 5), [0, 2, 4, 7, 9])

    def test_pick_evenly_spaced_returns_all_when_limit_exceeds_size(self):
        self.assertEqual(pick_evenly_spaced(["a", "b"], 5), ["a", "b"])

    def test_allocate_group_counts_preserves_total_and_minimum_per_group(self):
        counts = allocate_group_counts({"a": 100, "b": 50, "c": 10}, total=16)

        self.assertEqual(sum(counts.values()), 16)
        self.assertGreaterEqual(counts["a"], counts["b"])
        self.assertGreaterEqual(counts["b"], counts["c"])
        self.assertGreaterEqual(counts["c"], 1)

    def test_allocate_group_counts_handles_more_groups_than_requested_samples(self):
        counts = allocate_group_counts({"a": 10, "b": 10, "c": 10}, total=2)

        self.assertEqual(sum(counts.values()), 2)
        self.assertEqual(sorted(counts.values()), [0, 1, 1])

    def test_resolve_label_source_prefers_parallel_label_root(self):
        self.assertEqual(
            resolve_label_source(
                image_path=Path("dataset/images/train/a.jpg"),
                dataset_images_root=Path("dataset/images"),
                default_label_path=Path("dataset/labels/train/a.txt"),
                label_root=Path("dataset/pseudo_labels"),
            ),
            Path("dataset/pseudo_labels/train/a.txt"),
        )

    def test_resolve_label_source_uses_default_without_label_root(self):
        self.assertEqual(
            resolve_label_source(
                image_path=Path("dataset/images/train/a.jpg"),
                dataset_images_root=Path("dataset/images"),
                default_label_path=Path("dataset/labels/train/a.txt"),
                label_root=None,
            ),
            Path("dataset/labels/train/a.txt"),
        )


if __name__ == "__main__":
    unittest.main()
