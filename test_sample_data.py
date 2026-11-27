import unittest
from pathlib import Path
from autoexam_ml.dataset import read_dataset
from autoexam_ml.split import require_disjoint_questions

class SampleDataTests(unittest.TestCase):
    def test_question_groups_are_disjoint(self):
        data = Path(__file__).resolve().parents[1] / "data"
        require_disjoint_questions(*(read_dataset(data / filename)
                                     for filename in ("train.jsonl", "validation.jsonl", "test.jsonl")))

