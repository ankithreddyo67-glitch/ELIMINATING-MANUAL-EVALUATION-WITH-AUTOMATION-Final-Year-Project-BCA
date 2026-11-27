"""Export answer-level errors, largest first."""

import argparse

from autoexam_ml.dataset import read_dataset
from autoexam_ml.scoring import score
from autoexam_ml.storage import load_model, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    model = load_model(args.model)
    report = []
    for index, row in enumerate(read_dataset(args.input), 1):
        result = score(model, row)
        error = 100 * abs(result["marks"] - row["marks"]) / row["max_marks"]
        report.append({"row_number": index, "question_id": row["question_id"],
                       "expected_marks": row["marks"], "predicted_marks": result["marks"],
                       "absolute_error_percentage_points": round(error, 2)})
    write_json(args.output, sorted(report, key=lambda row: -row["absolute_error_percentage_points"]))


if __name__ == "__main__":
    main()

