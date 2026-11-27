"""Inspect the trained model coefficients."""

import argparse
import json

from autoexam_ml.features import NAMES
from autoexam_ml.storage import load_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    args = parser.parse_args()
    model = load_model(args.model)
    print(json.dumps({"bias": model.bias, "weights": dict(zip(NAMES, model.weights))}, indent=2))


if __name__ == "__main__":
    main()

