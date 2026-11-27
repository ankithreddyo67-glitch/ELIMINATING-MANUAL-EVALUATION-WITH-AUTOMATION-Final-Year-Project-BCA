-- Expected healthy result: zero rows.
SELECT a.id AS answer_id, a.final_marks, q.max_marks FROM answers a JOIN questions q ON q.id = a.question_id WHERE a.final_marks < 0 OR a.final_marks > q.max_marks;
