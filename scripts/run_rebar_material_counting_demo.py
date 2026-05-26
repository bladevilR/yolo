"""Run the prototype rebar endpoint material-counting demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_factory.rebar_material_counter import run_material_counting_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="Field QC media manifest CSV.")
    parser.add_argument("--output", required=True, type=Path, help="Material-counting output directory.")
    args = parser.parse_args(argv)

    if not args.manifest.exists() or not args.manifest.is_file():
        print(f"Manifest CSV not found: {args.manifest}")
        return 2

    paths = run_material_counting_demo(args.manifest, args.output)
    print(f"Report CSV: {paths.report_csv}")
    print(f"Report JSON: {paths.report_json}")
    print(f"Summary: {paths.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
