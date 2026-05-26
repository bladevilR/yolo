from __future__ import annotations

import argparse
from pathlib import Path

from cvat_sdk import make_client, models
from cvat_sdk.core.proxies.tasks import ResourceType


DEFAULT_REVIEW_ROOT = Path(
    r"E:\yolo\datasets\station_ppe_20260521_codex_multimodal_review_v1"
)
DEFAULT_TASK_NAME = "station_ppe_20260521_multimodal_v2_conservative_review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the local CVAT review task for station PPE labels."
    )
    parser.add_argument("--host", default="http://localhost:8080")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="StationPPE@2026")
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    parser.add_argument(
        "--images-zip",
        type=Path,
        default=DEFAULT_REVIEW_ROOT / "cvat_import" / "station_ppe_200_images.zip",
    )
    parser.add_argument(
        "--annotations-zip",
        type=Path,
        default=DEFAULT_REVIEW_ROOT
        / "cvat_import"
        / "station_ppe_200_yolo11_preannotations.zip",
    )
    parser.add_argument("--image-quality", type=int, default=100)
    parser.add_argument(
        "--reimport-annotations",
        action="store_true",
        help="If the task already exists, replace its annotations with the local YOLO draft.",
    )
    return parser.parse_args()


def require_file(path: Path) -> Path:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def main() -> None:
    args = parse_args()
    images_zip = require_file(args.images_zip)
    annotations_zip = require_file(args.annotations_zip)

    labels = [
        {"name": "person"},
        {"name": "helmet"},
        {"name": "vest"},
    ]

    with make_client(args.host, credentials=(args.username, args.password)) as client:
        existing = [task for task in client.tasks.list() if task.name == args.task_name]
        if existing:
            task = existing[0]
            print(f"task exists id={task.id} name={task.name}")
            if args.reimport_annotations:
                task.import_annotations("YOLO 1.1", annotations_zip)
                print(f"annotations reimported task_id={task.id}")
            print(f"url={args.host}/tasks/{task.id}")
            return

        task = client.tasks.create_from_data(
            spec=models.TaskWriteRequest(name=args.task_name, labels=labels),
            resource_type=ResourceType.LOCAL,
            resources=[images_zip],
            data_params={
                "image_quality": args.image_quality,
                "sorting_method": "lexicographical",
            },
            annotation_path=str(annotations_zip),
            annotation_format="YOLO 1.1",
            status_check_period=2,
        )
        print(f"created task id={task.id} name={task.name}")
        print(f"url={args.host}/tasks/{task.id}")


if __name__ == "__main__":
    main()
