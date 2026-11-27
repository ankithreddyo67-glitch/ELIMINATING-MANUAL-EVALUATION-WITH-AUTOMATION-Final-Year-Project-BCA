"""Inspect the text features for a single answer."""

import argparse
import json

from autoexam_ml.features import NAMES, extract
from autoexam_ml.schema import validate
from autoexam_ml.storage import load_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    args = parser.parse_args()
    row = load_json(args.input)
    validate(row)
    values = extract(row["reference"], row["answer"], row.get("keywords", []))
    print(json.dumps(dict(zip(NAMES, values)), indent=2))


if __name__ == "__main__":
    main()

