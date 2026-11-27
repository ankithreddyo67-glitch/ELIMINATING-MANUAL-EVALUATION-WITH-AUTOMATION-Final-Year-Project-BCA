import re

NAMES = ("recall", "precision", "concept_coverage", "bigram_recall", "length_match", "negation_mismatch")
STOPWORDS = {"a", "an", "the", "of", "to", "and", "it", "is", "are", "in", "for"}
NEGATIONS = {"not", "no", "never", "cannot", "without", "n't"}
ALIASES = {"saves": "store", "stores": "store", "keeps": "store", "repeats": "repeat",
           "repetition": "repeat", "uses": "use", "protects": "protect", "changed": "change",
           "changing": "change", "converts": "convert", "translates": "convert"}


def tokens(text):
    words = re.findall(r"n't|[a-z0-9]+", text.casefold().replace("’", "'").replace("n't", " n't"))
    return [ALIASES.get(word, word) for word in words if word not in STOPWORDS]


def extract(reference, answer, keywords):
    ref = tokens(reference)
    candidate = tokens(answer)
    ref_set, candidate_set = set(ref), set(candidate)
    shared = len(ref_set & candidate_set)
    concepts = [tokens(keyword) for keyword in keywords if tokens(keyword)]
    phrase_text = " " + " ".join(candidate) + " "
    coverage = sum(" " + " ".join(concept) + " " in phrase_text for concept in concepts)
    ref_pairs = set(zip(ref, ref[1:]))
    candidate_pairs = set(zip(candidate, candidate[1:]))
    return (
        shared / max(1, len(ref_set)),
        shared / max(1, len(candidate_set)),
        coverage / len(concepts) if concepts else shared / max(1, len(ref_set)),
        len(ref_pairs & candidate_pairs) / max(1, len(ref_pairs)),
        min(len(ref), len(candidate)) / max(1, len(ref), len(candidate)),
        float(bool(ref_set & NEGATIONS) != bool(candidate_set & NEGATIONS)),
    )
