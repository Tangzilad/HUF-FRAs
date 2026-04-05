#!/usr/bin/env python3
"""CLI for concise model and market explainers.

Usage examples:
    python scripts/explain.py
    python scripts/explain.py --topic cip --section calibration
    python scripts/explain.py --topic risk --format text --output docs/risk_brief.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.explainers import render_explanation


TOPICS = ("parametric", "short-rate", "cross-currency", "cip", "risk", "all")
SECTIONS = ("full", "concepts", "inputs", "calibration", "outputs", "trading")
FORMATS = ("md", "text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Explain core concepts, calibration workflow, and trading interpretation "
            "for HUF FRA analytics modules."
        )
    )
    parser.add_argument("--topic", choices=TOPICS, default="all", help="Topic to explain.")
    parser.add_argument("--section", choices=SECTIONS, default="full", help="Section to print.")
    parser.add_argument("--format", choices=FORMATS, default="md", help="Output format.")
    parser.add_argument("--output", type=Path, default=None, help="Optional output file path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    content = render_explanation(topic=args.topic, section=args.section, output_format=args.format)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
        print(f"Saved explanation to {args.output}")
    else:
        print(content)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
