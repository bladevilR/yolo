"""Write the default rulebook for the field AI QC pilot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_factory.field_qc_rules import build_default_rulebook, find_pending_confirmations, write_rulebook_outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Directory for rulebook JSON and Markdown outputs.")
    args = parser.parse_args(argv)

    rulebook = build_default_rulebook()
    paths = write_rulebook_outputs(args.output, rulebook)
    print(f"Rulebook JSON: {paths['json']}")
    print(f"Rulebook Markdown: {paths['markdown']}")
    pending = find_pending_confirmations(rulebook)
    if pending:
        print("Pending confirmations:")
        for item in pending:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
