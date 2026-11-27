import json
from pathlib import Path

from autoexam_ml.schema import validate


def read_dataset(path):
    records = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                validate(row, labeled=True)
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            records.append(row)
    if not records:
        raise ValueError(f"{path}: dataset is empty.")
    return records
