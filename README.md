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
