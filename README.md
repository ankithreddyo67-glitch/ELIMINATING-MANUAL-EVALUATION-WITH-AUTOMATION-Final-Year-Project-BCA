# AutoExam AI Machine Learning

A Python 3.10+ package for rubric-based descriptive-answer grading. It trains a regularized logistic regression model to estimate the fraction of available marks from text and rubric features. The included model and metrics use synthetic examples only.

From the extracted project folder:

```powershell
python -m autoexam_ml train data/train.jsonl data/validation.jsonl artifacts/model.json artifacts/metrics.json
python -m autoexam_ml score artifacts/model.json data/example.json
python -m autoexam_ml evaluate artifacts/model.json data/test.jsonl
python -m unittest discover -s tests -v
```

The module has no third-party runtime dependencies. See docs/integration.md for the optional adapter. Scores are provisional and faculty retain final grading authority.

## Python utilities

Run each utility with `python -m autoexam_ml.<name> --help` to see its inputs.

- audit_data checks train, validation and test data for overlapping question IDs.
- dataset_summary shows sample counts and mean label percentages per question.
- inspect_model shows the trained model's feature weights.
- inspect_features shows the text features for a single answer JSON object.
- batch_score reads a JSON array of answer objects and writes scores in input order.
- review_queue extracts flagged entries from the batch output.
- error_report compares predictions with labeled scores from a JSONL dataset.

The archive contains 34 Python source files plus the datasets, model and documentation.
