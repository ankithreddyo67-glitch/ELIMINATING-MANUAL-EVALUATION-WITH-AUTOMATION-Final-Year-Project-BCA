"""Score a JSON array of descriptive answers."""

import argparse

from autoexam_ml.scoring import score
from autoexam_ml.storage import load_json, load_model, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    rows = load_json(args.input)
    if not isinstance(rows, list):
        raise SystemExit("The input must be a JSON array of answer records.")
    model = load_model(args.model)
    results = [dict(row_number=index, **score(model, row)) for index, row in enumerate(rows, 1)]
    write_json(args.output, results)


if __name__ == "__main__":
    main()

