"""ML & NLP Subjective and Objective Answer Evaluation Engine.

Implements an explainable multi-signal evaluation pipeline:
1. Text preprocessing, stopword removal, lightweight stemming, and synonym canonicalization
2. TF-IDF Vectorization + Cosine Similarity
3. BM25-inspired term-saturation similarity
4. Bigram phrase overlap F1
5. Faculty rubric / key-concept coverage (with auto-extracted concepts fallback)
6. Negation polarity mismatch detection
7. Length/completeness calibration + confidence scoring & human-readable feedback
"""

from __future__ import annotations

import math
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from backend.config import NLP_CONFIDENCE_LOW_THRESHOLD

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "can",
    "could", "did", "do", "does", "doing", "done", "for", "from", "had", "has",
    "have", "having", "he", "her", "here", "hers", "him", "his", "how", "i",
    "if", "in", "into", "is", "it", "its", "itself", "just", "may", "me",
    "might", "more", "most", "must", "my", "no", "nor", "not", "of", "on",
    "once", "only", "or", "other", "our", "ours", "out", "over", "own", "same",
    "shall", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "will", "with", "would", "you", "your", "yours", "also", "used",
    "using", "use", "make", "makes", "made", "way", "etc", "e.g", "i.e",
}

NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "none", "nothing", "nowhere",
    "hardly", "barely", "scarcely", "cannot", "cant", "dont",
    "doesnt", "didnt", "isnt", "arent", "wasnt", "werent", "wont", "wouldnt",
    "shouldnt", "couldnt",
}

# Canonicalize common academic/technical synonyms & variants
SYNONYM_MAP = {
    "labelled": "label",
    "labeled": "label",
    "labels": "label",
    "labelling": "label",
    "labeling": "label",
    "unlabelled": "unlabel",
    "unlabeled": "unlabel",
    "generalize": "general",
    "generalise": "general",
    "generalization": "general",
    "generalisation": "general",
    "optimize": "optim",
    "optimise": "optim",
    "optimization": "optim",
    "optimisation": "optim",
    "minimize": "minim",
    "minimise": "minim",
    "maximize": "maxim",
    "maximise": "maxim",
    "accuracy": "accur",
    "accurate": "accur",
    "prediction": "predict",
    "predictions": "predict",
    "predicting": "predict",
    "predicted": "predict",
    "classification": "classif",
    "classify": "classif",
    "classifier": "classif",
    "regression": "regress",
    "clustering": "cluster",
    "clusters": "cluster",
    "training": "train",
    "trained": "train",
    "testing": "test",
    "validation": "valid",
    "validate": "valid",
    "evaluation": "evalu",
    "evaluate": "evalu",
    "evaluating": "evalu",
    "features": "featur",
    "feature": "featur",
    "attributes": "featur",
    "attribute": "featur",
    "parameters": "param",
    "parameter": "param",
    "weights": "weight",
    "regularization": "regular",
    "regularisation": "regular",
    "overfitting": "overfit",
    "overfit": "overfit",
    "underfitting": "underfit",
    "underfit": "underfit",
    "algorithm": "algorithm",
    "algorithms": "algorithm",
    "method": "algorithm",
    "technique": "algorithm",
    "neural": "neural",
    "networks": "network",
    "network": "network",
    "gradient": "gradient",
    "descent": "descent",
    "supervised": "supervis",
    "unsupervised": "unsupervis",
    "reinforcement": "reinforc",
    "automated": "automat",
    "automatic": "automat",
    "automation": "automat",
    "database": "databas",
    "databases": "databas",
    "encapsulation": "encapsul",
    "inheritance": "inherit",
    "polymorphism": "polymorph",
    "abstraction": "abstract",
    "asynchronous": "async",
    "synchronous": "sync",
    "scalability": "scalabl",
    "scalable": "scalabl",
    "latency": "latenc",
    "throughput": "throughput",
    "security": "secur",
    "authentication": "authent",
    "authorization": "authoriz",
    "integrity": "integr",
    "consistency": "consist",
    "consistent": "consist",
    "manual": "manual",
    "human": "human",
    "error": "error",
    "errors": "error",
    "mistake": "error",
    "mistakes": "error",
    "reduce": "reduc",
    "reduces": "reduc",
    "reducing": "reduc",
    "decrease": "reduc",
    "decreases": "reduc",
    "improve": "improv",
    "improves": "improv",
    "improving": "improv",
    "enhance": "improv",
    "enhances": "improv",
    "dataset": "data",
    "datasets": "data",
    "examples": "data",
    "example": "data",
    "samples": "data",
    "sample": "data",
    "output": "target",
    "outputs": "target",
    "targets": "target",
    "target": "target",
    "outcome": "target",
    "outcomes": "target",
    "finds": "discover",
    "find": "discover",
    "discovers": "discover",
    "discover": "discover",
    "detects": "discover",
    "hidden": "latent",
    "natural": "latent",
    "patterns": "pattern",
    "pattern": "pattern",
    "structure": "pattern",
    "adjust": "updat",
    "adjusting": "updat",
    "updates": "updat",
    "updating": "updat",
    "weights": "param",
    "answer": "respons",
    "answers": "respons",
    "response": "respons",
    "responses": "respons",
    "fast": "quick",
    "instant": "quick",
    "rapid": "quick",
    "generate": "produc",
    "generates": "produc",
    "generating": "produc",
    "provide": "produc",
    "provides": "produc",
    "providing": "produc",
}


def light_stem(word: str) -> str:
    """Normalize and apply lightweight suffix stemming + synonym mapping."""
    w = word.lower().strip()
    if not w:
        return ""
    if w in SYNONYM_MAP:
        return SYNONYM_MAP[w]

    # Simple contraction normalization
    w = w.replace("'", "")
    if w in SYNONYM_MAP:
        return SYNONYM_MAP[w]

    # Lightweight Porter-inspired suffix stripping (guarding short roots)
    for suffix in ("ational", "ization", "isation", "fulness", "iveness", "ousness"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            w = w[: -len(suffix)] + "ate"
            break
    else:
        for suffix in ("ments", "ment", "ness", "able", "ible", "tion", "sion", "ally", "ing", "ies", "ied", "ed", "es", "ly", "s"):
            if len(w) > len(suffix) + 3 and w.endswith(suffix):
                if suffix == "ies":
                    w = w[:-3] + "y"
                elif suffix == "ied":
                    w = w[:-3] + "y"
                else:
                    w = w[: -len(suffix)]
                break

    return SYNONYM_MAP.get(w, w)


def tokenize_raw(text: str) -> list[str]:
    """Extract lowercase alphanumeric tokens preserving contractions."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s'-]", " ", text.lower())
    cleaned = cleaned.replace("'", "")
    return [tok for tok in cleaned.split() if tok and len(tok) > 1 or tok.isdigit()]


def preprocess_tokens(text: str, remove_stopwords: bool = True) -> list[str]:
    """Tokenize, optionally filter stopwords, and stem tokens."""
    tokens = tokenize_raw(text)
    result: list[str] = []
    for tok in tokens:
        if remove_stopwords and tok in STOPWORDS:
            continue
        stemmed = light_stem(tok)
        if stemmed and (not remove_stopwords or stemmed not in STOPWORDS):
            result.append(stemmed)
    return result


def build_ngrams(tokens: list[str], n: int = 2) -> list[tuple[str, ...]]:
    """Construct n-grams from a token list."""
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def compute_tfidf_cosine(doc_a: str, doc_b: str, extra_corpus: list[str] | None = None) -> float:
    """Compute TF-IDF cosine similarity between two documents."""
    tokens_a = preprocess_tokens(doc_a)
    tokens_b = preprocess_tokens(doc_b)
    if not tokens_a or not tokens_b:
        return 0.0

    docs = [tokens_a, tokens_b]
    if extra_corpus:
        for text in extra_corpus:
            toks = preprocess_tokens(text)
            if toks:
                docs.append(toks)

    n_docs = len(docs)
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))

    def vectorize(tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        total = len(tokens)
        vec: dict[str, float] = {}
        for term, count in tf.items():
            # Sublinear TF + smoothed IDF
            tf_weight = 1.0 + math.log(count)
            idf = math.log((1.0 + n_docs) / (1.0 + df[term])) + 1.0
            vec[term] = (tf_weight / math.sqrt(total)) * idf
        return vec

    vec_a = vectorize(tokens_a)
    vec_b = vectorize(tokens_b)

    dot = sum(val * vec_b.get(term, 0.0) for term, val in vec_a.items())
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def compute_bm25_similarity(query_doc: str, target_doc: str) -> float:
    """Compute normalized BM25 overlap score of target_doc against query_doc (model answer)."""
    q_tokens = preprocess_tokens(query_doc)
    t_tokens = preprocess_tokens(target_doc)
    if not q_tokens or not t_tokens:
        return 0.0

    k1 = 1.5
    b = 0.75
    avgdl = max(1.0, len(q_tokens))
    dl = len(t_tokens)
    t_tf = Counter(t_tokens)
    q_unique = list(dict.fromkeys(q_tokens))

    score = 0.0
    max_possible = 0.0
    for term in q_unique:
        idf = 1.2  # balanced term salience when comparing pair
        max_possible += idf * ((k1 + 1.0) / (k1 * (1.0 - b + b * (len(q_tokens) / avgdl)) + 1.0))
        tf = t_tf.get(term, 0)
        if tf > 0:
            denom = tf + k1 * (1.0 - b + b * (dl / avgdl))
            score += idf * ((tf * (k1 + 1.0)) / denom)

    if max_possible <= 0.0:
        return 0.0
    return max(0.0, min(1.0, score / max_possible))


def compute_bigram_f1(text_a: str, text_b: str) -> float:
    """Compute bigram phrase F1 overlap."""
    tok_a = preprocess_tokens(text_a)
    tok_b = preprocess_tokens(text_b)
    bg_a = set(build_ngrams(tok_a, 2))
    bg_b = set(build_ngrams(tok_b, 2))
    if not bg_a or not bg_b:
        return 0.0
    overlap = len(bg_a & bg_b)
    if overlap == 0:
        return 0.0
    precision = overlap / len(bg_b)
    recall = overlap / len(bg_a)
    return 2.0 * precision * recall / (precision + recall)


def extract_auto_concepts(model_answer: str, max_concepts: int = 8) -> list[str]:
    """Fallback concept extraction from model answer when explicit keywords aren't provided."""
    raw_tokens = tokenize_raw(model_answer)
    content = [t for t in raw_tokens if t not in STOPWORDS and len(t) > 2]
    # Prefer informative bigrams plus top frequent unigrams
    freq = Counter(content)
    concepts: list[str] = []
    seen_stems: set[str] = set()
    for word, _ in freq.most_common(max_concepts * 2):
        stem = light_stem(word)
        if stem not in seen_stems:
            seen_stems.add(stem)
            concepts.append(word)
        if len(concepts) >= max_concepts:
            break
    return concepts


def _concept_matches(concept: str, student_text: str, student_stems: set[str]) -> bool:
    """Check whether a rubric concept (single word or multi-word phrase) is covered."""
    c_clean = concept.strip().lower()
    if not c_clean:
        return False

    # Direct substring match for exact phrase
    if c_clean in student_text.lower():
        return True

    c_stems = preprocess_tokens(c_clean, remove_stopwords=True)
    if not c_stems:
        c_stems = [light_stem(t) for t in tokenize_raw(c_clean)]
    if not c_stems:
        return False

    # Exact stem coverage for all tokens in concept
    matched_count = 0
    for stem in c_stems:
        if stem in student_stems:
            matched_count += 1
        else:
            # Fuzzy fallback for minor spelling mistakes (e.g., "algoritm" -> "algorithm")
            if any(SequenceMatcher(None, stem, s_tok).ratio() >= 0.84 for s_tok in student_stems):
                matched_count += 1

    return matched_count >= len(c_stems)


def detect_negation_conflicts(model_answer: str, student_answer: str, concepts: list[str]) -> list[str]:
    """Detect concepts whose negation polarity flips between model answer and student answer."""
    def polarity_map(text: str) -> dict[str, bool]:
        tokens = tokenize_raw(text)
        res: dict[str, bool] = {}
        for concept in concepts:
            c_stems = preprocess_tokens(concept)
            if not c_stems:
                continue
            target = c_stems[0]
            for idx, tok in enumerate(tokens):
                if light_stem(tok) == target:
                    window = tokens[max(0, idx - 3) : idx]
                    has_neg = any(w in NEGATION_WORDS for w in window)
                    res[concept] = has_neg
                    break
        return res

    model_pol = polarity_map(model_answer)
    student_pol = polarity_map(student_answer)
    conflicts: list[str] = []
    for concept, m_neg in model_pol.items():
        if concept in student_pol and student_pol[concept] != m_neg:
            conflicts.append(concept)
    return conflicts


def round_marks(raw_marks: float, max_marks: float) -> float:
    """Round awarded marks cleanly to the nearest 0.25 within [0, max_marks]."""
    clamped = max(0.0, min(max_marks, raw_marks))
    return round(clamped * 4.0) / 4.0


def evaluate_mcq(student_answer: str, correct_answer: str, max_marks: float) -> dict[str, Any]:
    """Evaluate a Multiple-Choice Question."""
    s_clean = (student_answer or "").strip().upper()
    c_clean = (correct_answer or "").strip().upper()
    is_correct = bool(s_clean) and s_clean == c_clean
    awarded = float(max_marks) if is_correct else 0.0
    feedback = (
        f"Correct option selected ({c_clean})."
        if is_correct
        else f"Incorrect. Selected '{s_clean or 'None'}', expected '{c_clean}'."
    )
    return {
        "awarded_marks": awarded,
        "max_marks": float(max_marks),
        "confidence": 1.0,
        "needs_review": False,
        "feedback": feedback,
        "breakdown": {
            "method": "EXACT_MCQ_MATCH",
            "is_correct": is_correct,
            "selected": s_clean,
            "expected": c_clean,
        },
    }


def evaluate_short_answer(
    student_answer: str,
    model_answer: str,
    keywords: list[str],
    max_marks: float,
) -> dict[str, Any]:
    """Evaluate a short factual answer using normalization, fuzzy ratio, and rubric concepts."""
    s_raw = (student_answer or "").strip()
    m_raw = (model_answer or "").strip()
    if not s_raw:
        return {
            "awarded_marks": 0.0,
            "max_marks": float(max_marks),
            "confidence": 1.0,
            "needs_review": False,
            "feedback": "No answer submitted.",
            "breakdown": {"method": "SHORT_ANSWER_NLP", "similarity": 0.0, "concept_coverage": 0.0},
        }

    s_norm = " ".join(preprocess_tokens(s_raw, remove_stopwords=False))
    m_norm = " ".join(preprocess_tokens(m_raw, remove_stopwords=False))
    seq_ratio = SequenceMatcher(None, s_norm, m_norm).ratio() if (s_norm and m_norm) else 0.0
    tfidf_sim = compute_tfidf_cosine(m_raw, s_raw)

    concepts = [k.strip() for k in keywords if k.strip()] or extract_auto_concepts(m_raw, max_concepts=4)
    student_stems = set(preprocess_tokens(s_raw, remove_stopwords=False))
    matched = [c for c in concepts if _concept_matches(c, s_raw, student_stems)]
    missing = [c for c in concepts if c not in matched]
    concept_cov = len(matched) / len(concepts) if concepts else tfidf_sim

    conflicts = detect_negation_conflicts(m_raw, s_raw, concepts)
    neg_penalty = min(0.35, 0.2 * len(conflicts))

    combined = max(0.0, min(1.0, (0.45 * concept_cov + 0.35 * tfidf_sim + 0.20 * seq_ratio) - neg_penalty))
    if seq_ratio >= 0.90 or (concept_cov >= 0.99 and tfidf_sim >= 0.75):
        combined = max(combined, 0.95)

    awarded = round_marks(combined * max_marks, max_marks)
    confidence = round(min(0.98, 0.70 + 0.28 * abs(combined - 0.5) * 2.0 - (0.15 * len(conflicts))), 3)
    needs_review = confidence < NLP_CONFIDENCE_LOW_THRESHOLD

    feedback_parts = []
    if matched:
        feedback_parts.append(f"Matched concepts: {', '.join(matched)}.")
    if missing:
        feedback_parts.append(f"Missing key points: {', '.join(missing)}.")
    if conflicts:
        feedback_parts.append(f"Polarity/negation mismatch near: {', '.join(conflicts)}.")

    return {
        "awarded_marks": awarded,
        "max_marks": float(max_marks),
        "confidence": confidence,
        "needs_review": needs_review,
        "feedback": " ".join(feedback_parts) or "Evaluated against reference answer.",
        "breakdown": {
            "method": "SHORT_ANSWER_NLP",
            "tfidf_cosine": round(tfidf_sim, 3),
            "sequence_similarity": round(seq_ratio, 3),
            "concept_coverage": round(concept_cov, 3),
            "matched_concepts": matched,
            "missing_concepts": missing,
            "negation_conflicts": conflicts,
            "composite_score": round(combined, 3),
        },
    }


def evaluate_subjective_answer(
    student_answer: str,
    model_answer: str,
    keywords: list[str],
    max_marks: float,
    corpus_answers: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate a descriptive/subjective answer with multi-feature ML/NLP ensemble."""
    s_raw = (student_answer or "").strip()
    m_raw = (model_answer or "").strip()

    if not s_raw:
        return {
            "awarded_marks": 0.0,
            "max_marks": float(max_marks),
            "confidence": 1.0,
            "needs_review": False,
            "feedback": "No subjective answer provided.",
            "breakdown": {
                "method": "SUBJECTIVE_ML_NLP_ENSEMBLE",
                "tfidf_cosine": 0.0,
                "bm25_similarity": 0.0,
                "bigram_f1": 0.0,
                "concept_coverage": 0.0,
                "length_adequacy": 0.0,
                "matched_concepts": [],
                "missing_concepts": keywords,
                "negation_conflicts": [],
                "composite_score": 0.0,
            },
        }

    # 1. Core similarity signals
    tfidf_sim = compute_tfidf_cosine(m_raw, s_raw, extra_corpus=corpus_answers)
    bm25_sim = compute_bm25_similarity(m_raw, s_raw)
    bigram_f1 = compute_bigram_f1(m_raw, s_raw)

    # 2. Rubric concept coverage
    concepts = [k.strip() for k in keywords if k.strip()]
    if not concepts:
        concepts = extract_auto_concepts(m_raw, max_concepts=8)
    student_stems = set(preprocess_tokens(s_raw, remove_stopwords=False))
    matched = [c for c in concepts if _concept_matches(c, s_raw, student_stems)]
    missing = [c for c in concepts if c not in matched]
    concept_cov = len(matched) / len(concepts) if concepts else tfidf_sim

    # 3. Completeness / length calibration
    s_words = tokenize_raw(s_raw)
    m_words = tokenize_raw(m_raw)
    target_len = max(12, int(len(m_words) * 0.65))
    length_ratio = min(1.0, len(s_words) / target_len)
    # Smooth penalty for ultra-short answers trying to game keywords
    length_adequacy = math.sqrt(length_ratio)

    # 4. Negation polarity check
    conflicts = detect_negation_conflicts(m_raw, s_raw, concepts)
    neg_penalty = min(0.30, 0.14 * len(conflicts))

    # 5. Weighted ensemble fusion
    composite = (
        0.42 * concept_cov
        + 0.26 * tfidf_sim
        + 0.16 * bm25_sim
        + 0.08 * bigram_f1
        + 0.08 * length_adequacy
    ) - neg_penalty

    # Calibrate valid paraphrased answers that hit rubric concepts with adequate depth
    if concept_cov >= 0.85 and max(tfidf_sim, bm25_sim) >= 0.35 and length_adequacy >= 0.80 and not conflicts:
        paraphrase_floor = min(0.92, 0.70 * concept_cov + 0.16 * max(tfidf_sim, bm25_sim) + 0.08 * length_adequacy)
        composite = max(composite, paraphrase_floor)

    # Reward near-identical complete answers without artificial deflation
    if concept_cov >= 0.90 and tfidf_sim >= 0.80 and length_adequacy >= 0.85 and not conflicts:
        composite = max(composite, 0.94)
    elif len(s_words) < 4 and max_marks >= 3:
        composite = min(composite, 0.25)

    composite = max(0.0, min(1.0, composite))
    awarded = round_marks(composite * max_marks, max_marks)

    # Confidence estimation: lower confidence on borderline scores, very short answers, or conflicts
    margin_from_mid = abs(composite - 0.5)
    signal_agreement = 1.0 - min(1.0, abs(concept_cov - tfidf_sim))
    confidence = 0.52 + 0.26 * signal_agreement + 0.18 * margin_from_mid - 0.15 * len(conflicts)
    if len(s_words) < 6:
        confidence -= 0.10
    confidence = round(max(0.25, min(0.98, confidence)), 3)
    needs_review = confidence < NLP_CONFIDENCE_LOW_THRESHOLD

    feedback_parts: list[str] = []
    if composite >= 0.80:
        feedback_parts.append("Strong, comprehensive response covering core concepts accurately.")
    elif composite >= 0.55:
        feedback_parts.append("Good foundational understanding, though some rubric depth is missing.")
    elif composite >= 0.30:
        feedback_parts.append("Partial understanding shown; key technical details need elaboration.")
    else:
        feedback_parts.append("Insufficient conceptual coverage compared to the reference answer.")

    if matched:
        feedback_parts.append(f"Covered: {', '.join(matched)}.")
    if missing:
        feedback_parts.append(f"Missing/underdeveloped: {', '.join(missing)}.")
    if conflicts:
        feedback_parts.append(f"Potential negation contradiction detected for: {', '.join(conflicts)}.")
    if len(s_words) < max(8, int(len(m_words) * 0.35)):
        feedback_parts.append("Response is brief relative to expected rubric depth.")

    return {
        "awarded_marks": awarded,
        "max_marks": float(max_marks),
        "confidence": confidence,
        "needs_review": needs_review,
        "feedback": " ".join(feedback_parts),
        "breakdown": {
            "method": "SUBJECTIVE_ML_NLP_ENSEMBLE",
            "tfidf_cosine": round(tfidf_sim, 3),
            "bm25_similarity": round(bm25_sim, 3),
            "bigram_f1": round(bigram_f1, 3),
            "concept_coverage": round(concept_cov, 3),
            "length_adequacy": round(length_adequacy, 3),
            "matched_concepts": matched,
            "missing_concepts": missing,
            "negation_conflicts": conflicts,
            "word_count": len(s_words),
            "composite_score": round(composite, 3),
        },
    }


def evaluate_answer(
    question_type: str,
    student_answer: str,
    model_answer: str,
    keywords: list[str] | None,
    max_marks: float,
    corpus_answers: list[str] | None = None,
) -> dict[str, Any]:
    """Dispatch evaluation based on question type (MCQ, SHORT, SUBJECTIVE)."""
    qtype = (question_type or "SUBJECTIVE").upper()
    kw_list = keywords or []
    if qtype == "TRUE_FALSE":
        return evaluate_mcq(student_answer, model_answer, max_marks)
    if qtype == "PROGRAMMING":
        def normalize(code: str) -> str:
            return "\n".join(line.rstrip() for line in code.splitlines()).strip("\n")

        answer = normalize(student_answer or "")
        equivalent = bool(answer) and answer == normalize(model_answer or "")
        return {
            "awarded_marks": max_marks if equivalent else 0.0,
            "max_marks": max_marks,
            "confidence": 1.0 if equivalent or not answer else 0.0,
            "needs_review": bool(answer) and not equivalent,
            "feedback": (
                "Matches the reference code." if equivalent else
                "Faculty review required for this code submission." if answer else "No code submitted."
            ),
            "breakdown": {"method": "REFERENCE_CODE_MATCH", "exact_match": equivalent},
        }
    if qtype == "MCQ":
        return evaluate_mcq(student_answer, model_answer, max_marks)
    if qtype == "SHORT":
        return evaluate_short_answer(student_answer, model_answer, kw_list, max_marks)
    return evaluate_subjective_answer(
        student_answer,
        model_answer,
        kw_list,
        max_marks,
        corpus_answers=corpus_answers,
    )


def compute_grade_letter(percentage: float) -> str:
    """Map percentage score to academic letter grade."""
    if percentage >= 90:
        return "A+"
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B+"
    if percentage >= 60:
        return "B"
    if percentage >= 50:
        return "C"
    if percentage >= 40:
        return "D"
    return "F"
