import unittest

from autoexam_ml.dataset import read_dataset
from autoexam_ml.scoring import score
from autoexam_ml.train import train

class TrainingTests(unittest.TestCase):
    def test_model_learns_from_labels(self):
        model = train(read_dataset("data/train.jsonl"))
        base = {"reference": "Variables store values", "keywords": ["store values"]}
        full = score(model, {**base, "answer": "Variables store values"})["marks"]
        low = score(model, {**base, "answer": "The weather is rainy"})["marks"]
        self.assertGreater(full, low)
