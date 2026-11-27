CREATE OR REPLACE VIEW exam_outcomes AS
SELECT exam_id, COUNT(*) AS result_count, AVG(percentage) AS mean_percentage, SUM(passed) AS pass_count FROM published_results GROUP BY exam_id;
