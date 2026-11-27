import math

from autoexam_ml.scoring import score


def evaluate(model, rows):
    if not rows:
        raise ValueError("Evaluation requires labeled answers.")
    errors = []
    reviews = 0
    for row in rows:
        result = score(model, row)
        errors.append((result["marks"] - row["marks"]) / row["max_marks"])
        reviews += result["needs_review"]
    count = len(errors)
    return {
        "n_answers": count,
        "n_questions": len({row["question_id"] for row in rows}),
        "mae_percentage_points": round(100 * sum(abs(e) for e in errors) / count, 2),
        "rmse_percentage_points": round(100 * math.sqrt(sum(e * e for e in errors) / count), 2),
        "faculty_review_percent": round(100 * reviews / count, 2),
    }
