import json
import math
from pathlib import Path

from autoexam_ml.features import NAMES
from autoexam_ml.model import GradeModel


def write_json(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_model(path):
    data = load_json(path)
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("features") != list(NAMES):
        raise ValueError("Unsupported model schema.")
    weights = data.get("weights")
    bias = data.get("bias")
    if not isinstance(weights, list) or len(weights) != len(NAMES):
        raise ValueError("Incorrect model dimensions.")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in [*weights, bias]):
        raise ValueError("Model parameters must be finite.")
    return GradeModel(tuple(weights), bias)
