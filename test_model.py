import unittest
from autoexam_ml.model import GradeModel

class ModelTests(unittest.TestCase):
    def test_dimension_mismatch(self):
        with self.assertRaises(ValueError):
            GradeModel((0.0,), 0).predict(())

    def test_extreme_logits_return_bounded_scores(self):
        self.assertGreater(GradeModel((), 1000).predict(()), 0.99)
        self.assertGreaterEqual(GradeModel((), -1000).predict(()), 0)

