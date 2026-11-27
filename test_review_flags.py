import unittest
from autoexam_ml.features import NAMES
from autoexam_ml.model import GradeModel
from autoexam_ml.scoring import score

class ReviewFlagTests(unittest.TestCase):
    def test_negation_requires_review_even_with_high_estimate(self):
        model = GradeModel((0.0,) * len(NAMES), 10)
        result = score(model, {"reference": "DNS translates names", "answer": "DNS never translates names"})
        self.assertTrue(result["needs_review"])
        self.assertIn("negation_mismatch", result["reasons"])

