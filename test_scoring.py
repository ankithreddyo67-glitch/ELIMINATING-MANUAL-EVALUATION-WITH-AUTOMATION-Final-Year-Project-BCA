import unittest

from autoexam_ml.integration import evaluate_descriptive
from autoexam_ml.model import GradeModel

class ScoringTests(unittest.TestCase):
    def test_blank_answer_scores_zero(self):
        result = evaluate_descriptive(GradeModel((0,) * 6, 0), "", "A reference", [], 10)
        self.assertEqual(result["awarded_marks"], 0)
        self.assertFalse(result["needs_review"])
