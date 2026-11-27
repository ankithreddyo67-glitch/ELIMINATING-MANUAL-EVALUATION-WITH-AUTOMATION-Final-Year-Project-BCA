import unittest

from autoexam_ml.features import extract

class FeatureTests(unittest.TestCase):
    def test_aliases_and_negation(self):
        result = extract("A loop repeats code", "A loop does not repeat code", ["repeat code"])
        self.assertEqual(result[2], 1)
        self.assertEqual(result[-1], 1)
