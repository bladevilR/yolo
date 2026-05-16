import unittest

from data_factory.error_review import detection_stats, review_reason


class ErrorReviewTests(unittest.TestCase):
    def test_detection_stats_counts_classes(self):
        lines = [
            "0 0.5 0.5 0.2 0.2",
            "2 0.5 0.5 0.1 0.1",
            "5 0.5 0.5 0.1 0.1",
        ]

        stats = detection_stats(lines)

        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["person"], 1)
        self.assertEqual(stats["helmet"], 1)
        self.assertEqual(stats["no_vest"], 1)

    def test_review_reason_flags_violation_and_empty(self):
        self.assertEqual(review_reason({"total": 0}), "empty_detection")
        self.assertEqual(review_reason({"total": 2, "no_helmet": 1}), "violation_class")
        self.assertEqual(review_reason({"total": 16}), "many_boxes")
        self.assertEqual(review_reason({"total": 3}), "routine_sample")


if __name__ == "__main__":
    unittest.main()
