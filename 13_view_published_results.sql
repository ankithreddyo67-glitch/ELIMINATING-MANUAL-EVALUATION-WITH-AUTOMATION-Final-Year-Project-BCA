CREATE OR REPLACE VIEW published_results AS
SELECT a.id AS attempt_id, a.exam_id, a.student_id, a.total_score, a.max_score, a.percentage, a.grade, a.passed FROM exam_attempts a WHERE a.status = 'PUBLISHED';
