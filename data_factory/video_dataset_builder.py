#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build an unlabeled YOLO image dataset from site video files.

This script is intentionally CPU-friendly: it extracts sparse frames, applies
light quality checks, performs conservative perceptual-hash de-duplication, and
creates YOLO-compatible image/label folders for later human QA or pre-labeling.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np


DEFAULT_CLASSES = ["person", "head", "helmet", "vest", "no_helmet", "no_vest"]
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".ts", ".m4v"}


@dataclass(frozen=True)
class VideoInfo:
    path: str
    width: int
    height: int
    fps: float
    frames: int
    duration_seconds: float


@dataclass(frozen=True)
class FrameRecord:
    image_path: str
    label_path: str
    split: str
    video_path: str
    video_name: str
    frame_index: int
    timestamp_seconds: float
    width: int
    height: int
    mean_intensity: float
    blur_score: float
    dhash: str
    label_status: str


@dataclass
class BuildStats:
    videos_seen: int = 0
    videos_opened: int = 0
    frames_attempted: int = 0
    frames_saved: int = 0
    skipped_decode: int = 0
    skipped_dark: int = 0
    skipped_bright: int = 0
    skipped_blurry: int = 0
    skipped_duplicate: int = 0


def frame_step_for_sample_fps(source_fps: float, sample_fps: float) -> int:
    if source_fps <= 0:
        raise ValueError("source_fps must be greater than 0")
    if sample_fps <= 0:
        raise ValueError("sample_fps must be greater than 0")
    return max(1, int(round(source_fps / sample_fps)))


def choose_split(index: int, train_pct: int = 80, val_pct: int = 10) -> str:
    if train_pct <= 0 or val_pct < 0 or train_pct + val_pct >= 100:
        raise ValueError("split percentages must leave at least 1% for test")
    bucket = index % 100
    if bucket < train_pct:
        return "train"
    if bucket < train_pct + val_pct:
        return "val"
    return "test"


def hamming_distance(left: int, right: int) -> int:
    return int(left ^ right).bit_count()


def is_duplicate_hash(candidate: int, existing: Sequence[int], threshold: int) -> bool:
    return any(hamming_distance(candidate, previous) <= threshold for previous in existing)


def safe_video_stem(path: Path) -> str:
    stem = re.sub(r"[^0-9A-Za-z._-]+", "_", path.stem).strip("._-")
    return stem or "video"


def initialize_yolo_dataset(root: Path, class_names: Sequence[str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)

    normalized_root = str(root.resolve()).replace("\\", "/")
    lines = [
        f"path: {normalized_root}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        f"nc: {len(class_names)}",
        "names:",
    ]
    lines.extend(f"  {idx}: {name}" for idx, name in enumerate(class_names))
    (root / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def iter_videos(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in VIDEO_EXTENSIONS else []
    return sorted(
        path
        for path in input_path.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def read_video_info(video_path: Path) -> VideoInfo | None:
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            return None
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = frames / fps if fps > 0 else 0.0
        return VideoInfo(
            path=str(video_path),
            width=width,
            height=height,
            fps=fps,
            frames=frames,
            duration_seconds=duration,
        )
    finally:
        cap.release()


def compute_dhash(frame: np.ndarray, hash_size: int = 8) -> int:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    value = 0
    for bit in diff.flatten():
        value = (value << 1) | int(bit)
    return value


def blur_score(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def write_csv(path: Path, rows: Iterable[dict], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_frame(
    frame: np.ndarray,
    output_root: Path,
    split: str,
    video_stem: str,
    frame_index: int,
    quality: int,
) -> tuple[Path, Path]:
    image_name = f"{video_stem}_f{frame_index:08d}.jpg"
    label_name = f"{video_stem}_f{frame_index:08d}.txt"
    image_path = output_root / "images" / split / image_name
    label_path = output_root / "labels" / split / label_name
    ok = cv2.imwrite(str(image_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError(f"Failed to write image: {image_path}")
    label_path.write_text("", encoding="utf-8")
    return image_path, label_path


def build_ffmpeg_extract_command(
    ffmpeg_exe: Path,
    video_path: Path,
    output_pattern: Path,
    sample_fps: float,
    jpeg_quality: int,
) -> list[str]:
    return [
        str(ffmpeg_exe),
        "-hide_banner",
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"fps={sample_fps:g}",
        "-q:v",
        str(jpeg_quality),
        str(output_pattern),
    ]


def get_ffmpeg_exe() -> Path:
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError(
            "FFmpeg backend requires imageio-ffmpeg. Install it with: python -m pip install imageio-ffmpeg"
        ) from exc
    return Path(imageio_ffmpeg.get_ffmpeg_exe())


def extract_frames_with_ffmpeg(
    video_path: Path,
    raw_dir: Path,
    video_stem: str,
    sample_fps: float,
    ffmpeg_qscale: int,
) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = raw_dir / f"{video_stem}_%08d.jpg"
    command = build_ffmpeg_extract_command(
        ffmpeg_exe=get_ffmpeg_exe(),
        video_path=video_path,
        output_pattern=output_pattern,
        sample_fps=sample_fps,
        jpeg_quality=ffmpeg_qscale,
    )
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for {video_path.name} with exit {completed.returncode}:\n{completed.stderr}"
        )
    return sorted(raw_dir.glob(f"{video_stem}_*.jpg"))


def build_dataset(
    input_path: Path,
    output_root: Path,
    sample_fps: float,
    class_names: Sequence[str],
    dedup_threshold: int = 1,
    dark_threshold: float = 8.0,
    bright_threshold: float = 248.0,
    blur_threshold: float = 0.0,
    jpeg_quality: int = 92,
    max_frames_per_video: int | None = None,
    extract_backend: str = "opencv",
    read_mode: str = "seek",
    ffmpeg_qscale: int = 3,
) -> tuple[BuildStats, list[VideoInfo], list[FrameRecord]]:
    initialize_yolo_dataset(output_root, class_names)
    videos = iter_videos(input_path)
    stats = BuildStats(videos_seen=len(videos))
    video_infos: list[VideoInfo] = []
    records: list[FrameRecord] = []
    hashes: list[int] = []
    saved_index = 0

    for video_path in videos:
        info = read_video_info(video_path)
        if info is None or info.fps <= 0 or info.frames <= 0:
            continue
        stats.videos_opened += 1
        video_infos.append(info)
        print(
            f"Processing {video_path.name}: {info.width}x{info.height}, "
            f"{info.fps:.2f} FPS, {info.duration_seconds / 60:.2f} min",
            flush=True,
        )

        step = frame_step_for_sample_fps(info.fps, sample_fps)
        video_stem = safe_video_stem(video_path)
        saved_for_video = 0

        def handle_frame(actual_frame_index: int, frame: np.ndarray) -> bool:
            nonlocal saved_index, saved_for_video
            mean_intensity = float(frame.mean())
            if mean_intensity < dark_threshold:
                stats.skipped_dark += 1
                return False
            if mean_intensity > bright_threshold:
                stats.skipped_bright += 1
                return False

            blur = 0.0
            if blur_threshold > 0:
                blur = blur_score(frame)
                if blur < blur_threshold:
                    stats.skipped_blurry += 1
                    return False

            frame_hash: int | None = None
            if dedup_threshold >= 0:
                frame_hash = compute_dhash(frame)
                if is_duplicate_hash(frame_hash, hashes, dedup_threshold):
                    stats.skipped_duplicate += 1
                    return False

            split = choose_split(saved_index)
            image_path, label_path = save_frame(
                frame,
                output_root,
                split,
                video_stem,
                actual_frame_index,
                jpeg_quality,
            )
            if frame_hash is not None:
                hashes.append(frame_hash)
            record = FrameRecord(
                image_path=str(image_path),
                label_path=str(label_path),
                split=split,
                video_path=str(video_path),
                video_name=video_path.name,
                frame_index=actual_frame_index,
                timestamp_seconds=actual_frame_index / info.fps,
                width=frame.shape[1],
                height=frame.shape[0],
                mean_intensity=round(mean_intensity, 3),
                blur_score=round(blur, 3),
                dhash=f"{frame_hash:016x}" if frame_hash is not None else "",
                label_status="empty_needs_annotation",
            )
            records.append(record)
            saved_index += 1
            saved_for_video += 1
            stats.frames_saved += 1
            return True

        try:
            if extract_backend == "ffmpeg":
                with tempfile.TemporaryDirectory(prefix=f"{video_stem}_", dir=str(output_root)) as tmp_dir:
                    raw_frames = extract_frames_with_ffmpeg(
                        video_path=video_path,
                        raw_dir=Path(tmp_dir),
                        video_stem=video_stem,
                        sample_fps=sample_fps,
                        ffmpeg_qscale=ffmpeg_qscale,
                    )
                    for sequence_index, raw_frame_path in enumerate(raw_frames):
                        if max_frames_per_video is not None and saved_for_video >= max_frames_per_video:
                            break
                        stats.frames_attempted += 1
                        frame = cv2.imread(str(raw_frame_path))
                        if frame is None:
                            stats.skipped_decode += 1
                            continue
                        timestamp_seconds = sequence_index / sample_fps
                        actual_frame_index = int(round(timestamp_seconds * info.fps))
                        handle_frame(actual_frame_index, frame)
            elif extract_backend == "opencv" and read_mode == "seek":
                cap = cv2.VideoCapture(str(video_path))
                frame_indices = range(0, info.frames, step)
                try:
                    for actual_frame_index in frame_indices:
                        if max_frames_per_video is not None and saved_for_video >= max_frames_per_video:
                            break
                        stats.frames_attempted += 1
                        cap.set(cv2.CAP_PROP_POS_FRAMES, actual_frame_index)
                        ok, frame = cap.read()
                        if not ok or frame is None:
                            stats.skipped_decode += 1
                            continue
                        handle_frame(actual_frame_index, frame)
                finally:
                    cap.release()
            elif extract_backend == "opencv" and read_mode == "sequential":
                cap = cv2.VideoCapture(str(video_path))
                try:
                    frame_index = 0
                    while frame_index < info.frames:
                        if frame_index % step != 0:
                            if not cap.grab():
                                break
                            frame_index += 1
                            continue

                        if max_frames_per_video is not None and saved_for_video >= max_frames_per_video:
                            break
                        stats.frames_attempted += 1
                        ok, frame = cap.read()
                        actual_frame_index = frame_index
                        frame_index += 1
                        if not ok or frame is None:
                            stats.skipped_decode += 1
                            continue
                        handle_frame(actual_frame_index, frame)
                finally:
                    cap.release()
            else:
                raise ValueError("extract_backend must be 'opencv' or 'ffmpeg'")
        finally:
            pass
        print(f"Saved {saved_for_video} frames from {video_path.name}", flush=True)

    write_outputs(output_root, stats, video_infos, records, class_names, sample_fps)
    return stats, video_infos, records


def write_outputs(
    output_root: Path,
    stats: BuildStats,
    video_infos: Sequence[VideoInfo],
    records: Sequence[FrameRecord],
    class_names: Sequence[str],
    sample_fps: float,
) -> None:
    write_csv(
        output_root / "metadata" / "videos.csv",
        (asdict(info) for info in video_infos),
        ["path", "width", "height", "fps", "frames", "duration_seconds"],
    )
    write_csv(
        output_root / "metadata" / "frames.csv",
        (asdict(record) for record in records),
        [
            "image_path",
            "label_path",
            "split",
            "video_path",
            "video_name",
            "frame_index",
            "timestamp_seconds",
            "width",
            "height",
            "mean_intensity",
            "blur_score",
            "dhash",
            "label_status",
        ],
    )
    summary = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sample_fps": sample_fps,
        "classes": list(class_names),
        "stats": asdict(stats),
    }
    (output_root / "metadata" / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    split_counts = {"train": 0, "val": 0, "test": 0}
    for record in records:
        split_counts[record.split] += 1

    total_duration = sum(info.duration_seconds for info in video_infos)
    readme = [
        "# Station PPE Dataset Draft",
        "",
        "This is an extracted image dataset draft. Label files are intentionally empty until human QA or pre-labeling is run.",
        "",
        f"- Source videos: {len(video_infos)}",
        f"- Source duration: {total_duration / 60:.2f} minutes",
        f"- Sample FPS: {sample_fps}",
        f"- Saved frames: {stats.frames_saved}",
        f"- Split counts: train={split_counts['train']}, val={split_counts['val']}, test={split_counts['test']}",
        f"- Classes: {', '.join(class_names)}",
        "",
        "Next steps:",
        "1. Import this YOLO dataset into CVAT, X-AnyLabeling, or another annotation tool.",
        "2. Run a teacher model for pre-labeling if available.",
        "3. Human-review labels before training.",
    ]
    (output_root / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")


def parse_classes(raw: str) -> list[str]:
    classes = [item.strip() for item in raw.split(",") if item.strip()]
    if not classes:
        raise ValueError("at least one class is required")
    return classes


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Video file or directory")
    parser.add_argument("--output", required=True, type=Path, help="Output YOLO dataset directory")
    parser.add_argument("--sample-fps", type=float, default=0.5, help="Frames per second to sample from each video")
    parser.add_argument(
        "--classes",
        default=",".join(DEFAULT_CLASSES),
        help="Comma-separated class names for data.yaml",
    )
    parser.add_argument("--dedup-threshold", type=int, default=1, help="dHash Hamming threshold; -1 disables dedup")
    parser.add_argument("--dark-threshold", type=float, default=8.0)
    parser.add_argument("--bright-threshold", type=float, default=248.0)
    parser.add_argument("--blur-threshold", type=float, default=0.0, help="0 disables blur filtering")
    parser.add_argument("--jpeg-quality", type=int, default=92)
    parser.add_argument("--max-frames-per-video", type=int, default=None)
    parser.add_argument(
        "--extract-backend",
        choices=("opencv", "ffmpeg"),
        default="opencv",
        help="ffmpeg is usually faster for sparse HEVC video extraction",
    )
    parser.add_argument(
        "--read-mode",
        choices=("seek", "sequential"),
        default="seek",
        help="seek is faster for sparse sampling; sequential is safer for problematic codecs",
    )
    parser.add_argument("--ffmpeg-qscale", type=int, default=3, help="FFmpeg JPEG q:v value; lower is better")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    class_names = parse_classes(args.classes)
    stats, video_infos, _records = build_dataset(
        input_path=args.input,
        output_root=args.output,
        sample_fps=args.sample_fps,
        class_names=class_names,
        dedup_threshold=args.dedup_threshold,
        dark_threshold=args.dark_threshold,
        bright_threshold=args.bright_threshold,
        blur_threshold=args.blur_threshold,
        jpeg_quality=args.jpeg_quality,
        max_frames_per_video=args.max_frames_per_video,
        extract_backend=args.extract_backend,
        read_mode=args.read_mode,
        ffmpeg_qscale=args.ffmpeg_qscale,
    )
    print(json.dumps({"videos": len(video_infos), "stats": asdict(stats)}, ensure_ascii=False, indent=2))
    return 0 if stats.frames_saved > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
