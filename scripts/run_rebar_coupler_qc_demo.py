"""Run the prototype rebar coupler exposed-thread QC demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_factory.rebar_coupler_qc import CouplerThresholdConfig, run_coupler_qc_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="Field QC media manifest CSV.")
    parser.add_argument("--output", required=True, type=Path, help="Coupler-QC output directory.")
    parser.add_argument("--max-visible-threads-per-side", type=int, default=None)
    args = parser.parse_args(argv)

    if not args.manifest.exists() or not args.manifest.is_file():
        print(f"Manifest CSV not found: {args.manifest}")
        return 2

    paths = run_coupler_qc_demo(
        args.manifest,
        args.output,
        threshold_config=CouplerThresholdConfig(max_visible_threads_per_side=args.max_visible_threads_per_side),
    )
    print(f"Report CSV: {paths.report_csv}")
    print(f"Report JSON: {paths.report_json}")
    print(f"Summary: {paths.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
