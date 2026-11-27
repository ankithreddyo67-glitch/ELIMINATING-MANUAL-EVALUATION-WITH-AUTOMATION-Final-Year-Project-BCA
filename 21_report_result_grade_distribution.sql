SELECT exam_id, grade, COUNT(*) AS result_count FROM published_results GROUP BY exam_id, grade ORDER BY exam_id, grade;
