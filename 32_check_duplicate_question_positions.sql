-- Expected healthy result: zero rows.
SELECT exam_id, order_index, COUNT(*) AS question_count FROM questions GROUP BY exam_id, order_index HAVING COUNT(*) > 1;
