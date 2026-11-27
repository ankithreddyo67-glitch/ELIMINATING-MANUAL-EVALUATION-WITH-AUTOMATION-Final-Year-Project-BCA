-- Expected healthy result: zero rows.
SELECT a.exam_id, a.student_id, u.role FROM exam_assignments a JOIN users u ON u.id = a.student_id WHERE u.role <> 'STUDENT';
