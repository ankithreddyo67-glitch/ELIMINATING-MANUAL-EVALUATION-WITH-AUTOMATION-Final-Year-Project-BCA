CREATE OR REPLACE VIEW assignment_roster AS
SELECT a.exam_id, e.title, a.student_id, u.full_name, a.due_at FROM exam_assignments a JOIN exams e ON e.id = a.exam_id JOIN users u ON u.id = a.student_id;
