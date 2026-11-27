CREATE OR REPLACE VIEW attempt_progress AS
SELECT t.id AS attempt_id, t.exam_id, t.student_id, t.status, COUNT(a.id) AS answered_count FROM exam_attempts t LEFT JOIN answers a ON a.attempt_id = t.id AND TRIM(a.student_answer) <> '' GROUP BY t.id, t.exam_id, t.student_id, t.status;
