import unittest
from autoexam_ml.metrics import evaluate
from autoexam_ml.model import GradeModel

class MetricsTests(unittest.TestCase):
    def test_metrics_normalize_by_available_marks(self):
        rows = [
            {"question_id": "a", "reference": "code", "answer": "", "marks": 2, "max_marks": 4},
            {"question_id": "a", "reference": "code", "answer": "", "marks": 4, "max_marks": 8},
        ]
        result = evaluate(GradeModel((), 0), rows)
        self.assertEqual(result["mae_percentage_points"], 50)
        self.assertEqual(result["rmse_percentage_points"], 50)
        self.assertEqual(result["n_questions"], 1)

