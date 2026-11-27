from autoexam_ml.features import NAMES, extract
from autoexam_ml.model import GradeModel
from autoexam_ml.schema import validate


def train(rows, epochs=800, learning_rate=0.35, penalty=0.01):
    if not rows or epochs < 1 or learning_rate <= 0 or penalty < 0:
        raise ValueError("Supply training data and valid hyperparameters.")
    examples = []
    for row in rows:
        maximum = validate(row, labeled=True)
        features = extract(row["reference"], row["answer"], row.get("keywords", []))
        examples.append((features, row["marks"] / maximum))

    weights = [0.0] * len(NAMES)
    bias = 0.0
    for _ in range(epochs):
        model = GradeModel(tuple(weights), bias)
        gradients = [0.0] * len(weights)
        bias_gradient = 0.0
        for features, target in examples:
            error = model.predict(features) - target
            bias_gradient += error
            for index, value in enumerate(features):
                gradients[index] += error * value
        for index, gradient in enumerate(gradients):
            weights[index] -= learning_rate * (gradient / len(examples) + penalty * weights[index])
        bias -= learning_rate * bias_gradient / len(examples)
    return GradeModel(tuple(weights), bias)
