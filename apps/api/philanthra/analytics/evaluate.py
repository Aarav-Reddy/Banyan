"""Explicit historical evaluation command; absence of real labels is not validation."""

import argparse
import json
from pathlib import Path

from .evaluation import evaluate_historical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="JSON with records, train_end, validation_end, label_definition, horizon_days",
    )
    parser.add_argument("--synthetic-harness-only", action="store_true")
    args = parser.parse_args()
    if args.input is None:
        print(
            json.dumps(
                {
                    "status": "not_validated",
                    "model_enabled": False,
                    "reason": "No permissioned real historical label dataset supplied.",
                }
            )
        )
        return 2
    data = json.loads(args.input.read_text())
    result = evaluate_historical(**data, real_validation=not args.synthetic_harness_only)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["status"] == "not_validated" else 0


if __name__ == "__main__":
    raise SystemExit(main())
