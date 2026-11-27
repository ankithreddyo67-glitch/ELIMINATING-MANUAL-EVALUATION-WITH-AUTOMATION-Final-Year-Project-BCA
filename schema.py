import math


def validate(record, labeled=False):
    if not isinstance(record, dict):
        raise ValueError("Expected an answer record.")
    if not isinstance(record.get("reference"), str) or not record["reference"].strip():
        raise ValueError("A reference answer is required.")
    if not isinstance(record.get("answer"), str):
        raise ValueError("The answer must be text.")
    keywords = record.get("keywords", [])
    if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
        raise ValueError("Keywords must be a list of strings.")
    maximum = record.get("max_marks", 5)
    if type(maximum) not in (int, float) or not math.isfinite(maximum) or maximum <= 0:
        raise ValueError("Maximum marks must be positive and finite.")
    if labeled:
        marks = record.get("marks")
        if type(marks) not in (int, float) or not math.isfinite(marks) or not 0 <= marks <= maximum:
            raise ValueError("Training marks must be between zero and maximum marks.")
        if not isinstance(record.get("question_id"), str) or not record["question_id"].strip():
            raise ValueError("A question ID is required for labeled data.")
    return maximum
