from autoexam_ml.features import NAMES, extract
from autoexam_ml.schema import validate


def score(model, row):
    maximum = validate(row)
    values = extract(row["reference"], row["answer"], row.get("keywords", []))
    features = dict(zip(NAMES, values))
    if not row["answer"].strip():
        return {"marks": 0.0, "needs_review": False, "reasons": ["blank_answer"], "features": features}

    estimate = model.predict(values)
    reasons = []
    if features["negation_mismatch"]:
        reasons.append("negation_mismatch")
    if 0.3 <= estimate <= 0.75:
        reasons.append("intermediate_prediction")
    if features["recall"] < 0.2:
        reasons.append("low_reference_overlap")
    return {
        "marks": min(maximum, round(estimate * maximum, 2)),
        "needs_review": bool(reasons),
        "reasons": reasons,
        "features": {name: round(value, 3) for name, value in features.items()},
    }
