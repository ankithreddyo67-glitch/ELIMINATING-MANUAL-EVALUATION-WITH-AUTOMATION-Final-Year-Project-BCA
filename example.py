from autoexam_ml.scoring import score
from autoexam_ml.storage import load_model

if __name__ == "__main__":
    print(score(load_model("artifacts/model.json"), {
        "reference": "A loop repeats a block of code.",
        "answer": "It repeats a block of code.",
        "keywords": ["repeats", "code"],
        "max_marks": 5,
    }))
