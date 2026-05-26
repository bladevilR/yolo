"""Build a field-QC media inventory from local site-survey materials."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_factory.field_qc_inventory import (
    build_current_survey_overrides,
    build_media_manifest,
    write_inventory_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Directory containing field photos/videos.")
    parser.add_argument("--output", required=True, type=Path, help="Output field-QC dataset directory.")
    parser.add_argument(
        "--current-survey-presets",
        action="store_true",
        help="Apply the manual scenario grouping used for the 2026-05-22 site-survey folder.",
    )
    args = parser.parse_args(argv)

    if not args.source.exists() or not args.source.is_dir():
        print(f"Source directory not found: {args.source}")
        return 2

    file_names = [path.name for path in args.source.iterdir() if path.is_file()]
    overrides = build_current_survey_overrides(file_names) if args.current_survey_presets else {}
    manifest = build_media_manifest(args.source, overrides=overrides)
    paths = write_inventory_outputs(args.output, manifest)

    print(f"Media items: {len(manifest)}")
    print(f"Manifest CSV: {paths.manifest_csv}")
    print(f"Manifest JSON: {paths.manifest_json}")
    print(f"Review CSV: {paths.review_csv}")
    print(f"Summary: {paths.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
