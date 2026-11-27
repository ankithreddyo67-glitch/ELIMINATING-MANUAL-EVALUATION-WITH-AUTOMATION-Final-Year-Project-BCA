CREATE OR REPLACE VIEW exam_catalog AS
SELECT e.id AS exam_id, e.title, e.subject, e.status, e.duration_minutes, COUNT(q.id) AS question_count, COALESCE(SUM(q.max_marks), 0) AS available_marks FROM exams e LEFT JOIN questions q ON q.exam_id = e.id GROUP BY e.id, e.title, e.subject, e.status, e.duration_minutes;
