"""Validate datasets and check for question leakage."""

import argparse
import json

from autoexam_ml.dataset import read_dataset
from autoexam_ml.split import require_disjoint_questions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    inputs = [read_dataset(path) for path in args.paths]
    require_disjoint_questions(*inputs)
    print(json.dumps({path: {"answers": len(rows), "questions": len({row["question_id"] for row in rows})}
          for path, rows in zip(args.paths, inputs)}, indent=2))


if __name__ == "__main__":
    main()

