#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run supervision-backed visual QA over station PPE YOLO labels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_factory.supervision_ppe import DEFAULT_CLASSES, parse_classes, render_qc_outputs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--classes", default=",".join(DEFAULT_CLASSES))
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--rows", type=int, default=3)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = render_qc_outputs(
        images_dir=args.images,
        labels_dir=args.labels,
        output_dir=args.output,
        class_names=parse_classes(args.classes),
        columns=args.columns,
        rows=args.rows,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
