import unittest

import tempfile
from pathlib import Path
from autoexam_ml.model import GradeModel
from autoexam_ml.storage import load_model, write_json

class StorageTests(unittest.TestCase):
    def test_round_trip(self):
        model = GradeModel((1, 2, 3, 4, 5, 6), -1)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.json"
            write_json(path, model.payload())
            self.assertEqual(load_model(path), model)
