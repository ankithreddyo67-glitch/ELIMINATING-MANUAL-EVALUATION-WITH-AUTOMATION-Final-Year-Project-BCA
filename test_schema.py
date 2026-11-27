import unittest

from autoexam_ml.schema import validate

class SchemaTests(unittest.TestCase):
    def test_nonfinite_marks_rejected(self):
        with self.assertRaises(ValueError):
            validate({"reference": "Answer", "answer": "", "max_marks": float("nan")})
