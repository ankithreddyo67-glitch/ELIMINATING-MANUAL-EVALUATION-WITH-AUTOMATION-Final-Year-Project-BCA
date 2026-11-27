import unittest
from autoexam_ml.features import NAMES
from autoexam_ml.integration import evaluate_descriptive
from autoexam_ml.model import GradeModel

class IntegrationTests(unittest.TestCase):
    def test_flags_provisional_grade_for_review(self):
        model = GradeModel((0.0,) * len(NAMES), 0)
        result = evaluate_descriptive(model, "repeat code", "repeat code", ["code"], 8)
        self.assertEqual(result["awarded_marks"], 4)
        self.assertTrue(result["needs_review"])
        self.assertIsNone(result["confidence"])

