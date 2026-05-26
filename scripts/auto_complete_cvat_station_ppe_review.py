from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import cv2
import numpy as np
from cvat_sdk import make_client

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_ROOT = Path(r"E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1")
DEFAULT_TASK_ID = 1
CLASS_NAMES = ["person", "helmet", "vest"]


@dataclass(frozen=True)
class BoxLabel:
    class_id: int
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    def to_yolo_line(self, image_width: int, image_height: int) -> str:
        cx = ((self.x1 + self.x2) / 2) / image_width
        cy = ((self.y1 + self.y2) / 2) / image_height
        w = self.width / image_width
        h = self.height / image_height
        return f"{self.class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"

    @classmethod
    def from_yolo(cls, class_id: int, cx: float, cy: float, w: float, h: float, image_width: int, image_height: int) -> "BoxLabel":
        x1 = (cx - w / 2) * image_width
        y1 = (cy - h / 2) * image_height
        x2 = (cx + w / 2) * image_width
        y2 = (cy + h / 2) * image_height
        return cls(class_id, x1, y1, x2, y2)


@dataclass
class RemovalTemplate:
    members: list[BoxLabel]

    @property
    def mean(self) -> tuple[float, float, float, float]:
        count = len(self.members)
        return (
            sum(((box.x1 + box.x2) / 2) / 2560 for box in self.members) / count,
            sum(((box.y1 + box.y2) / 2) / 1440 for box in self.members) / count,
            sum(box.width / 2560 for box in self.members) / count,
            sum(box.height / 1440 for box in self.members) / count,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-complete the local CVAT station PPE review task.")
    parser.add_argument("--host", default="http://localhost:8080")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="StationPPE@2026")
    parser.add_argument("--task-id", type=int, default=DEFAULT_TASK_ID)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--apply", action="store_true", help="Import the generated annotations back into CVAT.")
    parser.add_argument("--changed-tolerance", type=float, default=1.5)
    parser.add_argument("--manual-match-iou", type=float, default=0.5)
    parser.add_argument("--duplicate-iou", type=float, default=0.9)
    parser.add_argument("--template-min-members", type=int, default=3)
    return parser.parse_args()


def box_iou(a: BoxLabel, b: BoxLabel) -> float:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    union = a.width * a.height + b.width * b.height - inter
    return inter / union if union > 0 else 0.0


def same_labels(a: list[BoxLabel], b: list[BoxLabel], tolerance: float) -> bool:
    if len(a) != len(b):
        return False
    key = lambda box: (box.class_id, round(box.x1, 1), round(box.y1, 1), round(box.x2, 1), round(box.y2, 1))
    for left, right in zip(sorted(a, key=key), sorted(b, key=key)):
        if left.class_id != right.class_id:
            return False
        if max(abs(left.x1 - right.x1), abs(left.y1 - right.y1), abs(left.x2 - right.x2), abs(left.y2 - right.y2)) > tolerance:
            return False
    return True


def dedupe(labels: list[BoxLabel], threshold: float) -> tuple[list[BoxLabel], int]:
    kept: list[BoxLabel] = []
    removed = 0
    for label in labels:
        if any(label.class_id == existing.class_id and box_iou(label, existing) >= threshold for existing in kept):
            removed += 1
            continue
        kept.append(label)
    return kept, removed


def load_original_labels(zip_path: Path, frame_names: list[str], width: int, height: int) -> dict[int, list[BoxLabel]]:
    by_frame: dict[int, list[BoxLabel]] = defaultdict(list)
    with ZipFile(zip_path) as zf:
        members = set(zf.namelist())
        for frame, name in enumerate(frame_names):
            label_member = f"obj_train_data/{Path(name).stem}.txt"
            if label_member not in members:
                continue
            text = zf.read(label_member).decode("utf-8", errors="ignore")
            for line in text.splitlines():
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                class_id = int(parts[0])
                cx, cy, w, h = (float(value) for value in parts[1:])
                by_frame[frame].append(BoxLabel.from_yolo(class_id, cx, cy, w, h, width, height))
    return by_frame


def labels_from_cvat(task_id: int, host: str, username: str, password: str) -> tuple[list[str], dict[int, list[BoxLabel]], dict[str, int]]:
    with make_client(host, credentials=(username, password)) as client:
        task = client.tasks.retrieve(task_id)
        frame_names = [frame.name for frame in task.get_meta().frames]
        labels = {label.id: label.name for label in task.get_labels()}
        class_by_label_id = {label_id: CLASS_NAMES.index(name) for label_id, name in labels.items() if name in CLASS_NAMES}
        by_frame: dict[int, list[BoxLabel]] = defaultdict(list)
        for shape in task.get_annotations().shapes:
            if str(shape.type) != "rectangle" or bool(shape.outside):
                continue
            if shape.label_id not in class_by_label_id:
                continue
            x1, y1, x2, y2 = (float(value) for value in shape.points)
            by_frame[int(shape.frame)].append(BoxLabel(class_by_label_id[shape.label_id], x1, y1, x2, y2))
    return frame_names, by_frame, class_by_label_id


def best_match(box: BoxLabel, candidates: list[BoxLabel], used: set[int], min_iou: float) -> int | None:
    best_iou = 0.0
    best_index: int | None = None
    for index, candidate in enumerate(candidates):
        if index in used or candidate.class_id != box.class_id:
            continue
        current_iou = box_iou(box, candidate)
        if current_iou > best_iou:
            best_iou = current_iou
            best_index = index
    return best_index if best_iou >= min_iou else None


def changed_frames_and_removed_people(
    original: dict[int, list[BoxLabel]],
    current: dict[int, list[BoxLabel]],
    frame_count: int,
    tolerance: float,
    match_iou: float,
) -> tuple[set[int], list[BoxLabel]]:
    changed: set[int] = set()
    removed_people: list[BoxLabel] = []
    for frame in range(frame_count):
        original_labels = original.get(frame, [])
        current_labels = current.get(frame, [])
        if same_labels(original_labels, current_labels, tolerance):
            continue
        changed.add(frame)

        used_current: set[int] = set()
        for original_box in original_labels:
            match_index = best_match(original_box, current_labels, used_current, match_iou)
            if match_index is None:
                if original_box.class_id == 0:
                    removed_people.append(original_box)
            else:
                used_current.add(match_index)
    return changed, removed_people


def normalized_tuple(box: BoxLabel) -> tuple[float, float, float, float]:
    return ((box.x1 + box.x2) / 2 / 2560, (box.y1 + box.y2) / 2 / 1440, box.width / 2560, box.height / 1440)


def template_matches(box: BoxLabel, template: RemovalTemplate) -> bool:
    cx, cy, w, h = normalized_tuple(box)
    tcx, tcy, tw, th = template.mean
    return (
        abs(cx - tcx) <= 0.035
        and abs(cy - tcy) <= 0.035
        and abs(w - tw) <= 0.035
        and abs(h - th) <= 0.035
    )


def build_removal_templates(removed_people: list[BoxLabel], min_members: int) -> list[RemovalTemplate]:
    templates: list[RemovalTemplate] = []
    for box in removed_people:
        matched = None
        for template in templates:
            if template_matches(box, template):
                matched = template
                break
        if matched is None:
            templates.append(RemovalTemplate([box]))
        else:
            matched.members.append(box)
    return [template for template in templates if len(template.members) >= min_members]


def is_associated_helmet(helmet: BoxLabel, person: BoxLabel) -> bool:
    person_w = max(1.0, person.width)
    person_h = max(1.0, person.height)
    cx = (helmet.x1 + helmet.x2) / 2
    cy = (helmet.y1 + helmet.y2) / 2
    return (
        person.x1 - person_w * 0.15 <= cx <= person.x2 + person_w * 0.15
        and person.y1 - person_h * 0.20 <= cy <= person.y1 + person_h * 0.42
    )


def person_has_vest(person: BoxLabel, labels: list[BoxLabel]) -> bool:
    return any(label.class_id == 2 and box_iou(person, label) > 0.05 for label in labels)


def person_has_helmet(person: BoxLabel, labels: list[BoxLabel]) -> bool:
    return any(label.class_id == 1 and is_associated_helmet(label, person) for label in labels)


def detect_helmet_candidate(image_bgr: np.ndarray, person: BoxLabel) -> BoxLabel | None:
    height, width = image_bgr.shape[:2]
    person_w = max(1, int(round(person.width)))
    person_h = max(1, int(round(person.height)))
    if person_w < 18 or person_h < 35:
        return None

    hx1 = max(0, round(person.x1 - person_w * 0.12))
    hx2 = min(width, round(person.x2 + person_w * 0.12))
    hy1 = max(0, round(person.y1 - person_h * 0.16))
    hy2 = min(height, round(person.y1 + person_h * 0.28))
    if hx2 <= hx1 or hy2 <= hy1:
        return None

    head = image_bgr[hy1:hy2, hx1:hx2]
    if head.size == 0:
        return None

    hsv = cv2.cvtColor(head, cv2.COLOR_BGR2HSV)
    yellow_orange = (hsv[:, :, 0] >= 12) & (hsv[:, :, 0] <= 42) & (hsv[:, :, 1] >= 95) & (hsv[:, :, 2] >= 100)
    blue = (hsv[:, :, 0] >= 88) & (hsv[:, :, 0] <= 132) & (hsv[:, :, 1] >= 60) & (hsv[:, :, 2] >= 75)
    red = ((hsv[:, :, 0] <= 8) | (hsv[:, :, 0] >= 170)) & (hsv[:, :, 1] >= 100) & (hsv[:, :, 2] >= 95)
    mask = (yellow_orange | blue | red).astype("uint8") * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    head_area = max(1, head.shape[0] * head.shape[1])
    if int(np.count_nonzero(mask)) < max(12, head_area * 0.012):
        return None

    count, _components, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates: list[tuple[int, BoxLabel]] = []
    for component_id in range(1, count):
        x, y, w, h, area = stats[component_id]
        if area < max(12, head_area * 0.018):
            continue
        if w < 5 or h < 5:
            continue
        x1, y1, x2, y2 = hx1 + x, hy1 + y, hx1 + x + w, hy1 + y + h
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        if not (person.x1 + person_w * 0.05 <= center_x <= person.x2 - person_w * 0.05):
            continue
        if center_y > person.y1 + person_h * 0.24:
            continue
        candidates.append((int(area), BoxLabel(1, x1, y1, x2, y2)))

    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def detect_visible_vest_candidate(image_bgr: np.ndarray, person: BoxLabel) -> BoxLabel | None:
    height, width = image_bgr.shape[:2]
    person_w = max(1, int(round(person.width)))
    person_h = max(1, int(round(person.height)))
    if person_w < 18 or person_h < 35:
        return None

    # Keep the search below the head/helmet. The previous broad torso rule
    # sometimes picked up yellow helmets and then labeled the whole body as vest.
    tx1 = max(0, round(person.x1 + person_w * 0.12))
    tx2 = min(width, round(person.x2 - person_w * 0.08))
    ty1 = max(0, round(person.y1 + person_h * 0.30))
    ty2 = min(height, round(person.y1 + person_h * 0.78))
    if tx2 <= tx1 or ty2 <= ty1:
        return None

    torso = image_bgr[ty1:ty2, tx1:tx2]
    if torso.size == 0:
        return None

    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
    orange_red = ((hsv[:, :, 0] <= 24) | (hsv[:, :, 0] >= 168)) & (hsv[:, :, 1] >= 120) & (hsv[:, :, 2] >= 120)
    yellow_green = (hsv[:, :, 0] >= 25) & (hsv[:, :, 0] <= 72) & (hsv[:, :, 1] >= 95) & (hsv[:, :, 2] >= 125)
    mask = (orange_red | yellow_green).astype("uint8") * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    torso_area = max(1, torso.shape[0] * torso.shape[1])
    mask_area = int(np.count_nonzero(mask))
    if mask_area < max(20, torso_area * 0.025):
        return None

    count, _components, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    components: list[tuple[int, int, int, int, int]] = []
    for component_id in range(1, count):
        x, y, w, h, area = stats[component_id]
        if area < max(18, torso_area * 0.020):
            continue
        if w < max(6, person_w * 0.18) or h < max(8, person_h * 0.10):
            continue
        components.append((tx1 + x, ty1 + y, tx1 + x + w, ty1 + y + h, int(area)))

    if not components:
        return None

    x1 = min(item[0] for item in components)
    y1 = min(item[1] for item in components)
    x2 = max(item[2] for item in components)
    y2 = max(item[3] for item in components)
    pad_x = max(2, round(person_w * 0.04))
    pad_y = max(2, round(person_h * 0.04))
    return BoxLabel(
        2,
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(width, x2 + pad_x),
        min(height, y2 + pad_y),
    )


def add_if_not_duplicate(labels: list[BoxLabel], candidate: BoxLabel, duplicate_iou: float) -> bool:
    if any(label.class_id == candidate.class_id and box_iou(label, candidate) >= duplicate_iou for label in labels):
        return False
    labels.append(candidate)
    return True


def auto_complete_frame(
    image_path: Path,
    labels: list[BoxLabel],
    removal_templates: list[RemovalTemplate],
    duplicate_iou: float,
) -> tuple[list[BoxLabel], Counter[str]]:
    stats: Counter[str] = Counter()
    labels, removed_duplicates = dedupe(labels, duplicate_iou)
    stats["duplicates_removed"] += removed_duplicates

    filtered: list[BoxLabel] = []
    for label in labels:
        if label.class_id == 0 and any(template_matches(label, template) for template in removal_templates):
            stats["person_removed_by_learned_template"] += 1
            continue
        filtered.append(label)
    labels = filtered
    labels = remove_unassociated_ppe(labels, stats)

    image = cv2.imread(str(image_path))
    if image is None:
        stats["invalid_image"] += 1
        return labels, stats
    height, width = image.shape[:2]

    for person in [label for label in list(labels) if label.class_id == 0]:
        if not person_has_helmet(person, labels):
            helmet = detect_helmet_candidate(image, person)
            if helmet is not None and add_if_not_duplicate(labels, helmet, 0.50):
                stats["helmet_added"] += 1

        if not person_has_vest(person, labels):
            vest_box = detect_visible_vest_candidate(image, person)
            if vest_box is not None and add_if_not_duplicate(labels, vest_box, 0.50):
                stats["vest_added"] += 1

    labels, removed_duplicates = dedupe(labels, duplicate_iou)
    stats["duplicates_removed"] += removed_duplicates
    labels = remove_unassociated_ppe(labels, stats)
    return labels, stats


def remove_unassociated_ppe(labels: list[BoxLabel], stats: Counter[str]) -> list[BoxLabel]:
    persons = [label for label in labels if label.class_id == 0]
    if not persons:
        removed = sum(1 for label in labels if label.class_id in {1, 2})
        stats["unassociated_ppe_removed"] += removed
        return [label for label in labels if label.class_id == 0]

    kept: list[BoxLabel] = []
    for label in labels:
        if label.class_id == 0:
            kept.append(label)
            continue
        if label.class_id == 1 and any(is_associated_helmet(label, person) for person in persons):
            kept.append(label)
            continue
        if label.class_id == 2 and any(box_iou(label, person) > 0.03 for person in persons):
            kept.append(label)
            continue
        stats["unassociated_ppe_removed"] += 1
    return kept


def write_yolo_zip(zip_path: Path, frame_names: list[str], labels_by_frame: dict[int, list[BoxLabel]], width: int, height: int) -> None:
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("obj.names", "\n".join(CLASS_NAMES) + "\n")
        zf.writestr("obj.data", "classes = 3\nnames = obj.names\ntrain = train.txt\nbackup = backup/\n")
        zf.writestr("train.txt", "".join(f"obj_train_data/{name}\n" for name in frame_names))
        for frame, name in enumerate(frame_names):
            lines = [
                label.to_yolo_line(width, height)
                for label in sorted(labels_by_frame.get(frame, []), key=lambda item: (item.class_id, item.y1, item.x1))
                if label.width > 0 and label.height > 0
            ]
            zf.writestr(f"obj_train_data/{Path(name).stem}.txt", "\n".join(lines) + ("\n" if lines else ""))


def main() -> int:
    args = parse_args()
    root = args.root
    images_dir = root / "images"
    import_dir = root / "cvat_import"
    original_zip = import_dir / "station_ppe_200_yolo11_preannotations.zip"

    frame_names, current, _class_by_label_id = labels_from_cvat(args.task_id, args.host, args.username, args.password)
    width, height = 2560, 1440
    original = load_original_labels(original_zip, frame_names, width, height)
    changed_frames, removed_people = changed_frames_and_removed_people(
        original,
        current,
        len(frame_names),
        args.changed_tolerance,
        args.manual_match_iou,
    )
    removal_templates = build_removal_templates(removed_people, args.template_min_members)

    completed: dict[int, list[BoxLabel]] = {}
    totals: Counter[str] = Counter()
    for frame, name in enumerate(frame_names):
        frame_labels = list(current.get(frame, []))
        if frame in changed_frames:
            completed[frame] = frame_labels
            totals["manual_preserved_frames"] += 1
            continue
        reviewed, stats = auto_complete_frame(images_dir / name, frame_labels, removal_templates, args.duplicate_iou)
        completed[frame] = reviewed
        totals.update(stats)
        totals["auto_completed_frames"] += 1

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_zip = import_dir / f"station_ppe_task{args.task_id}_auto_completed_{timestamp}.zip"
    summary_path = import_dir / f"station_ppe_task{args.task_id}_auto_completed_{timestamp}.json"
    write_yolo_zip(out_zip, frame_names, completed, width, height)

    class_counts = Counter()
    for labels in completed.values():
        class_counts.update(label.class_id for label in labels)

    summary = {
        "task_id": args.task_id,
        "generated_zip": str(out_zip),
        "applied_to_cvat": bool(args.apply),
        "frame_count": len(frame_names),
        "changed_frames_preserved": sorted(changed_frames),
        "removed_person_template_count": len(removal_templates),
        "removed_person_templates": [
            {
                "members": len(template.members),
                "mean_cx_cy_w_h": [round(value, 6) for value in template.mean],
            }
            for template in removal_templates
        ],
        "stats": dict(totals),
        "class_counts": {CLASS_NAMES[class_id]: class_counts[class_id] for class_id in range(len(CLASS_NAMES))},
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.apply:
        with make_client(args.host, credentials=(args.username, args.password)) as client:
            task = client.tasks.retrieve(args.task_id)
            task.import_annotations("YOLO 1.1", out_zip)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
