import unittest
import json
from pathlib import Path
import subprocess
import sys

class CliTests(unittest.TestCase):
    def test_scores_supplied_example(self):
        root = Path(__file__).resolve().parents[1]
        process = subprocess.run(
            [sys.executable, "-m", "autoexam_ml", "score", "artifacts/model.json", "data/example.json"],
            cwd=root, check=True, capture_output=True, text=True,
        )
        self.assertIn("marks", json.loads(process.stdout))

