import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from autoexam_ml.dataset import read_dataset

class DatasetTests(unittest.TestCase):
    def test_reports_malformed_line_number(self):
        with TemporaryDirectory() as directory:
            dataset = Path(directory) / "bad.jsonl"
            dataset.write_text("\ninvalid json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"bad\.jsonl:2:"):
                read_dataset(dataset)

