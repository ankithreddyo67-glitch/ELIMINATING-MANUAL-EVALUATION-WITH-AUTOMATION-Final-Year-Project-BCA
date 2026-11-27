-- Optional synthetic reference data. Existing subject codes retain their values.
INSERT INTO subjects (code, name, description)
SELECT 'DEMO-CS101', 'Programming Fundamentals', 'Sample subject for AutoExam'
WHERE NOT EXISTS (SELECT 1 FROM subjects WHERE code = 'DEMO-CS101');

INSERT INTO subjects (code, name, description)
SELECT 'DEMO-DB101', 'Database Systems', 'Sample subject for AutoExam'
WHERE NOT EXISTS (SELECT 1 FROM subjects WHERE code = 'DEMO-DB101');
