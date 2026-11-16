#!/usr/bin/env python3
"""Orchestrator: run pipeline stages via CLI flags."""

import argparse
import subprocess
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    subprocess.run([sys.executable] + cmd, cwd=BASE, check=True)


def main():
    ap = argparse.ArgumentParser(description="Islamic History Timeline Pipeline")
    ap.add_argument("--parse", action="store_true", help="Stage 2: parse mARkdown")
    ap.add_argument("--extract", action="store_true", help="Stage 3: call Gemini")
    ap.add_argument("--dedup", action="store_true", help="Stage 4: deduplicate")
    ap.add_argument("--all", action="store_true", help="Run all stages")
    ap.add_argument("--max-sections", type=int, default=None)
    ap.add_argument("--from-hijra", action="store_true",
                    help="Start parser from first Hijri year section")
    ap.add_argument("--input", default=None, help="Override mARkdown file path (for --parse)")
    args = ap.parse_args()

    if args.all:
        args.parse = args.extract = args.dedup = True

    if args.parse:
        cmd = ["parser.py"]
        if args.max_sections:
            cmd += ["--max-sections", str(args.max_sections)]
        if args.from_hijra:
            cmd += ["--from-hijra"]
        if args.input:
            cmd += ["--input", args.input]
        run(cmd)

    if args.extract:
        run(["extractor.py"])

    if args.dedup:
        run(["dedup.py"])

    if not any([args.parse, args.extract, args.dedup]):
        ap.print_help()


if __name__ == "__main__":
    main()
