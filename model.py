import math
from dataclasses import dataclass

from autoexam_ml.features import NAMES


@dataclass(frozen=True)
class GradeModel:
    weights: tuple[float, ...]
    bias: float

    def predict(self, features):
        if len(features) != len(self.weights):
            raise ValueError("Feature count does not match the model.")
        logit = self.bias + sum(weight * value for weight, value in zip(self.weights, features))
        return 1 / (1 + math.exp(-max(-60, min(60, logit))))

    def payload(self):
        return {"version": 1, "features": list(NAMES), "weights": self.weights, "bias": self.bias}
