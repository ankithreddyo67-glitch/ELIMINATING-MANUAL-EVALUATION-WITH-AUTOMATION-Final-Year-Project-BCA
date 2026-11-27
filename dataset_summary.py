"""Summarize labeled marks by question."""

import argparse
import json

from autoexam_ml.dataset import read_dataset
from collections import defaultdict
from statistics import mean


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    args = parser.parse_args()
    groups = defaultdict(list)
    for row in read_dataset(args.input):
        groups[row["question_id"]].append(row["marks"] / row["max_marks"])
    print(json.dumps({key: {"answers": len(marks), "mean_percent": round(100 * mean(marks), 2)}
          for key, marks in sorted(groups.items())}, indent=2))


if __name__ == "__main__":
    main()

