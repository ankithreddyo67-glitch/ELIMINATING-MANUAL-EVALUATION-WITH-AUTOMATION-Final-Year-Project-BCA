CREATE OR REPLACE VIEW question_bank_inventory AS
SELECT created_by, subject, difficulty, question_type, COUNT(*) AS question_count FROM question_bank GROUP BY created_by, subject, difficulty, question_type;
