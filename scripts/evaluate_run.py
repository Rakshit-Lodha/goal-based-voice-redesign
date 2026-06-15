"""Evaluate a saved live-run transcript with binary PASS/FAIL checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.run_eval import evaluate_transcript_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True, help="Path to output/transcripts/*.json")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    result = evaluate_transcript_file(args.transcript)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print("PASS" if result.passed else "FAIL")
        for check in result.checks:
            status = "PASS" if check.passed else "FAIL"
            detail = f" - {check.detail}" if check.detail else ""
            print(f"{status} {check.name}{detail}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
