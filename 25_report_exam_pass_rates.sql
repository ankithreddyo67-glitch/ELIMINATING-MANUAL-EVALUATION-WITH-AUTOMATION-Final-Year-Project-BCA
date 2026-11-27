SELECT exam_id, result_count, ROUND(mean_percentage, 2) AS mean_percentage, ROUND(100.0 * pass_count / NULLIF(result_count, 0), 2) AS pass_rate FROM exam_outcomes ORDER BY exam_id;
