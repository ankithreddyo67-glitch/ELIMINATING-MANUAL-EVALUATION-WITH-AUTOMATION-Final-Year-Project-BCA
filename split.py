def require_disjoint_questions(*datasets):
    seen = set()
    for rows in datasets:
        current = {row["question_id"] for row in rows}
        overlap = seen & current
        if overlap:
            raise ValueError(f"Question leakage across datasets: {', '.join(sorted(overlap))}")
        seen.update(current)
