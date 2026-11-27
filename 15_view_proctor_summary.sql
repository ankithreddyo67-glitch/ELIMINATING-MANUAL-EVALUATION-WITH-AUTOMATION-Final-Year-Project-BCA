CREATE OR REPLACE VIEW proctor_summary AS
SELECT attempt_id, COUNT(*) AS event_count, SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) AS high_severity_count, MAX(created_at) AS latest_event_at FROM proctor_logs GROUP BY attempt_id;
