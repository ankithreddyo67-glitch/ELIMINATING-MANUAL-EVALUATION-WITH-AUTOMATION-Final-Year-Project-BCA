import argparse
import json

from autoexam_ml.dataset import read_dataset
from autoexam_ml.metrics import evaluate
from autoexam_ml.scoring import score
from autoexam_ml.split import require_disjoint_questions
from autoexam_ml.storage import load_json, load_model, write_json
from autoexam_ml.train import train


def main():
    parser = argparse.ArgumentParser(description="Train and run the AutoExam answer grader.")
    commands = parser.add_subparsers(dest="command", required=True)
    fit = commands.add_parser("train")
    for name in ("training", "validation", "model", "metrics"):
        fit.add_argument(name)
    for command in ("score", "evaluate"):
        subparser = commands.add_parser(command)
        subparser.add_argument("model")
        subparser.add_argument("input")
    args = parser.parse_args()
    try:
        if args.command == "train":
            training = read_dataset(args.training)
            validation = read_dataset(args.validation)
            require_disjoint_questions(training, validation)
            model = train(training)
            result = evaluate(model, validation)
            write_json(args.model, model.payload())
            write_json(args.metrics, result)
        elif args.command == "evaluate":
            result = evaluate(load_model(args.model), read_dataset(args.input))
        else:
            result = score(load_model(args.model), load_json(args.input))
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2))
