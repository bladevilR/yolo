"""Run the prototype concrete surface anomaly-screening demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_factory.concrete_surface_qc import ConcreteQcConfig, run_concrete_surface_qc_demo
from data_factory.field_qc_rules import CONCRETE_SURFACE_CLASSES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="Field QC media manifest CSV.")
    parser.add_argument("--output", required=True, type=Path, help="Concrete-QC output directory.")
    args = parser.parse_args(argv)

    if not args.manifest.exists() or not args.manifest.is_file():
        print(f"Manifest CSV not found: {args.manifest}")
        return 2

    paths = run_concrete_surface_qc_demo(
        args.manifest,
        args.output,
        config=ConcreteQcConfig(defect_classes=CONCRETE_SURFACE_CLASSES),
    )
    print(f"Report CSV: {paths.report_csv}")
    print(f"Report JSON: {paths.report_json}")
    print(f"Summary: {paths.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
