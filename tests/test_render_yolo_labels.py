import unittest

from data_factory.render_yolo_labels import parse_yolo_label_line, xywhn_to_xyxy


class RenderYoloLabelsTests(unittest.TestCase):
    def test_parse_yolo_label_line_reads_class_and_box(self):
        class_id, box = parse_yolo_label_line("2 0.500000 0.250000 0.100000 0.200000")

        self.assertEqual(class_id, 2)
        self.assertEqual(box, [0.5, 0.25, 0.1, 0.2])

    def test_xywhn_to_xyxy_converts_to_pixel_coordinates(self):
        self.assertEqual(xywhn_to_xyxy([0.5, 0.5, 0.25, 0.5], width=400, height=200), (150, 50, 250, 150))


if __name__ == "__main__":
    unittest.main()
