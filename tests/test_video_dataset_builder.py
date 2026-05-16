import tempfile
import unittest
from pathlib import Path

from data_factory.video_dataset_builder import (
    build_ffmpeg_extract_command,
    choose_split,
    frame_step_for_sample_fps,
    hamming_distance,
    initialize_yolo_dataset,
    is_duplicate_hash,
    safe_video_stem,
)


class VideoDatasetBuilderTests(unittest.TestCase):
    def test_frame_step_for_sample_fps_uses_nearest_whole_frame_interval(self):
        self.assertEqual(frame_step_for_sample_fps(source_fps=25.0, sample_fps=0.5), 50)
        self.assertEqual(frame_step_for_sample_fps(source_fps=25.0, sample_fps=1.0), 25)
        self.assertEqual(frame_step_for_sample_fps(source_fps=25.0, sample_fps=60.0), 1)

    def test_choose_split_is_deterministic_and_roughly_80_10_10(self):
        counts = {"train": 0, "val": 0, "test": 0}
        for index in range(100):
            counts[choose_split(index)] += 1

        self.assertEqual(counts, {"train": 80, "val": 10, "test": 10})
        self.assertEqual(choose_split(101), choose_split(1))

    def test_duplicate_hash_uses_hamming_distance_threshold(self):
        existing = [0b11110000, 0b00001111]

        self.assertEqual(hamming_distance(0b11110000, 0b11110011), 2)
        self.assertTrue(is_duplicate_hash(0b11110011, existing, threshold=2))
        self.assertFalse(is_duplicate_hash(0b10101010, existing, threshold=2))

    def test_safe_video_stem_keeps_traceable_filename_without_unsafe_chars(self):
        self.assertEqual(
            safe_video_stem(Path(r"F:\yolo\2026-05-15\00000001970000000.mp4")),
            "00000001970000000",
        )
        self.assertEqual(safe_video_stem(Path("camera 01:main.mp4")), "camera_01_main")

    def test_initialize_yolo_dataset_writes_dirs_and_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "station_ppe"
            classes = ["person", "head", "helmet", "vest", "no_helmet", "no_vest"]

            initialize_yolo_dataset(root, classes)

            for split in ("train", "val", "test"):
                self.assertTrue((root / "images" / split).is_dir())
                self.assertTrue((root / "labels" / split).is_dir())

            data_yaml = (root / "data.yaml").read_text(encoding="utf-8")
            self.assertIn("path: " + str(root).replace("\\", "/"), data_yaml)
            self.assertIn("nc: 6", data_yaml)
            self.assertIn("0: person", data_yaml)
            self.assertIn("5: no_vest", data_yaml)

    def test_build_ffmpeg_extract_command_samples_to_numbered_jpegs(self):
        command = build_ffmpeg_extract_command(
            ffmpeg_exe=Path("ffmpeg.exe"),
            video_path=Path("input.mp4"),
            output_pattern=Path("frames") / "camera_%08d.jpg",
            sample_fps=0.5,
            jpeg_quality=3,
        )

        self.assertEqual(command[0], "ffmpeg.exe")
        self.assertIn("fps=0.5", command)
        self.assertIn("-q:v", command)
        self.assertIn("3", command)
        self.assertEqual(command[-1], str(Path("frames") / "camera_%08d.jpg"))


if __name__ == "__main__":
    unittest.main()
