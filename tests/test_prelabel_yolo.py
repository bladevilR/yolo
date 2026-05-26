import unittest

from pathlib import Path

from data_factory.prelabel_yolo import (
    map_model_class_to_target,
    parse_optional_classes,
    target_label_path,
    yolo_line,
)


class PrelabelYoloTests(unittest.TestCase):
    def test_map_model_class_to_target_handles_ppe_synonyms(self):
        target = ["person", "head", "helmet", "vest", "no_helmet", "no_vest"]

        self.assertEqual(map_model_class_to_target("Person", target), 0)
        self.assertEqual(map_model_class_to_target("Hardhat", target), 2)
        self.assertEqual(map_model_class_to_target("Hard Hat", target), 2)
        self.assertEqual(map_model_class_to_target("Helmet", target), 2)
        self.assertEqual(map_model_class_to_target("Safety Helmet", target), 2)
        self.assertEqual(map_model_class_to_target("Safety Vest", target), 3)
        self.assertEqual(map_model_class_to_target("Reflective Vest", target), 3)
        self.assertEqual(map_model_class_to_target("NO-Hardhat", target), 4)
        self.assertEqual(map_model_class_to_target("NO-Safety Vest", target), 5)

    def test_map_model_class_to_target_ignores_unwanted_classes(self):
        target = ["person", "head", "helmet", "vest", "no_helmet", "no_vest"]

        self.assertIsNone(map_model_class_to_target("Mask", target))
        self.assertIsNone(map_model_class_to_target("Safety Boot", target))

    def test_yolo_line_formats_normalized_box(self):
        self.assertEqual(yolo_line(2, [0.5, 0.25, 0.1, 0.2]), "2 0.500000 0.250000 0.100000 0.200000")

    def test_target_label_path_preserves_image_subdirectories(self):
        self.assertEqual(
            target_label_path(
                image_path=Path("dataset/images/train/a.jpg"),
                images_root=Path("dataset/images"),
                output_labels=Path("dataset/pseudo_labels"),
            ),
            Path("dataset/pseudo_labels/train/a.txt"),
        )

    def test_parse_optional_classes_accepts_empty_and_comma_list(self):
        self.assertIsNone(parse_optional_classes(None))
        self.assertIsNone(parse_optional_classes("  "))
        self.assertEqual(parse_optional_classes("person, hard hat, safety vest"), ["person", "hard hat", "safety vest"])


if __name__ == "__main__":
    unittest.main()
