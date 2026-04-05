#!/usr/bin/env python3
"""CLI for rendering lightweight educational summaries from project artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate explanation-oriented summaries.")
    parser.add_argument("--input", type=Path, required=True, help="Path to source artifact.")
    parser.add_argument(
        "--mode",
        choices=["summary", "teaching", "risk-brief"],
        default="summary",
        help="Explanation style to generate.",
    )
    parser.add_argument(
        "--audience",
        default="quant-research",
        help="Audience label used in explanation framing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"[explain] input={args.input} mode={args.mode} audience={args.audience}")


if __name__ == "__main__":
    main()
