"""Export batch results flagged for faculty review."""

import argparse

from autoexam_ml.storage import load_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    rows = load_json(args.input)
    if not isinstance(rows, list):
        raise SystemExit("The input must be a JSON array produced by batch_score.")
    write_json(args.output, [row for row in rows if row["needs_review"]])


if __name__ == "__main__":
    main()

