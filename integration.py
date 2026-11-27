from autoexam_ml.scoring import score


def evaluate_descriptive(model, student_answer, model_answer, keywords, max_marks):
    """Return score and review metadata in AutoExam's evaluator format."""
    result = score(model, {
        "reference": model_answer,
        "answer": student_answer or "",
        "keywords": keywords or [],
        "max_marks": max_marks,
    })
    return {
        "awarded_marks": result["marks"],
        "max_marks": max_marks,
        "confidence": None,
        "needs_review": result["needs_review"],
        "feedback": "Faculty review recommended." if result["needs_review"] else "Provisional model score.",
        "breakdown": {
            "method": "RUBRIC_LOGISTIC_REGRESSION",
            "features": result["features"],
            "review_reasons": result["reasons"],
        },
    }
