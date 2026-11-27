"""Unit tests for the ML & NLP subjective and objective answer evaluator."""

import unittest

from backend.nlp_evaluator import (
    compute_grade_letter,
    compute_tfidf_cosine,
    evaluate_answer,
)


class TestNLPEvaluator(unittest.TestCase):
    def test_mcq_exact_match(self):
        correct = evaluate_answer("MCQ", "b", "B", [], 5.0)
        self.assertEqual(correct["awarded_marks"], 5.0)
        self.assertEqual(correct["confidence"], 1.0)

        wrong = evaluate_answer("MCQ", "A", "B", [], 5.0)
        self.assertEqual(wrong["awarded_marks"], 0.0)

    def test_subjective_high_quality_paraphrase(self):
        model = (
            "Supervised learning trains models on labeled datasets to predict outputs such as spam detection, "
            "whereas unsupervised learning finds hidden clusters in unlabeled data."
        )
        keywords = ["labeled", "unlabeled", "clusters", "predict"]
        good_student = (
            "In supervised learning, algorithms learn from labeled input-output examples to predict targets like spam. "
            "In contrast, unsupervised learning discovers natural clusters inside unlabeled datasets."
        )
        res = evaluate_answer("SUBJECTIVE", good_student, model, keywords, 10.0)
        self.assertGreaterEqual(res["awarded_marks"], 7.5)
        self.assertGreaterEqual(res["breakdown"]["concept_coverage"], 0.75)
        self.assertEqual(len(res["breakdown"]["missing_concepts"]), 0)

    def test_subjective_blank_and_unrelated(self):
        model = "Gradient descent minimizes the loss function iteratively using the learning rate."
        blank = evaluate_answer("SUBJECTIVE", "   ", model, ["gradient descent", "loss function"], 10.0)
        self.assertEqual(blank["awarded_marks"], 0.0)

        unrelated = evaluate_answer(
            "SUBJECTIVE",
            "Photosynthesis converts sunlight into chemical energy inside plant leaves.",
            model,
            ["gradient descent", "loss function", "learning rate"],
            10.0,
        )
        self.assertLessEqual(unrelated["awarded_marks"], 1.5)

    def test_negation_conflict_penalized(self):
        model = "Regularization reduces overfitting and improves generalization on unseen data."
        keywords = ["regularization", "overfitting", "generalization"]
        positive = evaluate_answer(
            "SUBJECTIVE",
            "Regularization reduces overfitting and improves generalization on new test data.",
            model,
            keywords,
            10.0,
        )
        contradictory = evaluate_answer(
            "SUBJECTIVE",
            "Regularization does not reduce overfitting and never improves generalization on new test data.",
            model,
            keywords,
            10.0,
        )
        self.assertGreater(positive["awarded_marks"], contradictory["awarded_marks"])
        self.assertTrue(len(contradictory["breakdown"]["negation_conflicts"]) >= 1)

    def test_short_answer_evaluation(self):
        res = evaluate_answer(
            "SHORT",
            "Overfitting occurs when a model learns training noise and fails to generalize to unseen data.",
            "Overfitting is when a model memorizes noise in training data and generalizes poorly on unseen data.",
            ["training", "noise", "generalize", "unseen"],
            5.0,
        )
        self.assertGreaterEqual(res["awarded_marks"], 3.75)

    def test_tfidf_cosine_bounds(self):
        sim = compute_tfidf_cosine("neural networks optimize weights", "neural network weight optimization")
        self.assertGreater(sim, 0.5)
        self.assertLessEqual(sim, 1.0)

    def test_grade_letters(self):
        self.assertEqual(compute_grade_letter(92), "A+")
        self.assertEqual(compute_grade_letter(74), "B+")
        self.assertEqual(compute_grade_letter(30), "F")


if __name__ == "__main__":
    unittest.main()
