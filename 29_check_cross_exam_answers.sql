-- Expected healthy result: zero rows.
SELECT a.id AS answer_id, t.exam_id AS attempt_exam_id, q.exam_id AS question_exam_id FROM answers a JOIN questions q ON q.id = a.question_id JOIN exam_attempts t ON t.id = a.attempt_id WHERE t.exam_id <> q.exam_id;
