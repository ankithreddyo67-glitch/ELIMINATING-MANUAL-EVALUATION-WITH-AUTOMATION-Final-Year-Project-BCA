CREATE OR REPLACE VIEW faculty_review_queue AS
SELECT a.id AS answer_id, a.attempt_id, t.exam_id, a.question_id, a.ai_marks, a.ai_confidence, a.ai_feedback FROM answers a JOIN exam_attempts t ON t.id = a.attempt_id WHERE a.needs_review = 1 AND a.faculty_override = 0 AND t.status IN ('SUBMITTED', 'EVALUATED');
