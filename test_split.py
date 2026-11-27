import unittest

from autoexam_ml.split import require_disjoint_questions

class SplitTests(unittest.TestCase):
    def test_question_leakage(self):
        rows = [{"question_id": "q1"}]
        with self.assertRaises(ValueError):
            require_disjoint_questions(rows, rows)
