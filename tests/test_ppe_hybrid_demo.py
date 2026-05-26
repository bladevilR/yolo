import unittest

from data_factory.ppe_hybrid_demo import (
    Detection,
    PersonFilterConfig,
    ReviewConfig,
    build_review_queue,
    enrich_event_rows,
    event_review_reasons,
    filter_persons,
    helmet_matches_person,
    rejected_manual_review_reason,
    status_text,
)


class PpeHybridDemoTests(unittest.TestCase):
    def test_helmet_matches_person_when_center_is_in_upper_body(self):
        person = Detection(0, 0.9, (100, 100, 200, 300))
        helmet = Detection(1, 0.8, (130, 110, 170, 150))

        self.assertTrue(helmet_matches_person(helmet, person))

    def test_status_text_reports_missing_ppe(self):
        self.assertEqual(status_text(True, True), "ok")
        self.assertEqual(status_text(False, True), "no_helmet")
        self.assertEqual(status_text(True, False), "no_vest")
        self.assertEqual(status_text(False, False), "no_helmet+no_vest")

    def test_filter_persons_rejects_square_false_positive(self):
        config = PersonFilterConfig(min_confidence=0.45, min_aspect=1.25)
        person_like_bag = Detection(0, 0.9, (100, 100, 220, 220))

        accepted, rejected = filter_persons([person_like_bag], config)

        self.assertEqual([], accepted)
        self.assertEqual("bad_aspect_too_square", rejected[0][1])

    def test_filter_persons_removes_nested_duplicate(self):
        config = PersonFilterConfig(min_confidence=0.2)
        large = Detection(0, 0.9, (100, 100, 200, 320))
        nested = Detection(0, 0.4, (115, 130, 190, 280))

        accepted, rejected = filter_persons([nested, large], config)

        self.assertEqual([large], accepted)
        self.assertEqual("duplicate_person", rejected[0][1])

    def test_rule_only_helmet_goes_to_review(self):
        row = {
            "person_confidence": "0.9000",
            "status": "ok",
            "helmet_present": "true",
            "helmet_present_model": "false",
            "helmet_present_rule": "true",
            "vest_present_rule": "true",
        }

        self.assertEqual(["helmet_rule_only"], event_review_reasons(row, ReviewConfig()))

    def test_low_confidence_rejected_candidate_goes_to_review_queue(self):
        row = {
            "person_confidence": "0.3000",
            "reason": "low_confidence",
        }

        self.assertEqual("possible_worker_low_confidence", rejected_manual_review_reason(row, ReviewConfig()))

    def test_build_review_queue_includes_uncertain_events_and_probable_rejected_workers(self):
        events = enrich_event_rows(
            [
                {
                    "image_name": "sample.jpg",
                    "person_index": 1,
                    "person_confidence": "0.9000",
                    "x1": 1,
                    "y1": 2,
                    "x2": 3,
                    "y2": 4,
                    "helmet_present": "true",
                    "helmet_present_model": "false",
                    "helmet_present_rule": "true",
                    "vest_present_rule": "true",
                    "status": "ok",
                }
            ],
            ReviewConfig(),
        )
        rejected = [
            {
                "image_name": "sample.jpg",
                "candidate_index": 2,
                "person_confidence": "0.3000",
                "x1": 5,
                "y1": 6,
                "x2": 7,
                "y2": 8,
                "reason": "low_confidence",
            }
        ]

        queue = build_review_queue(events, rejected, ReviewConfig())

        self.assertEqual(2, len(queue))
        self.assertEqual("accepted_event", queue[0]["queue_source"])
        self.assertEqual("rejected_candidate", queue[1]["queue_source"])


if __name__ == "__main__":
    unittest.main()
