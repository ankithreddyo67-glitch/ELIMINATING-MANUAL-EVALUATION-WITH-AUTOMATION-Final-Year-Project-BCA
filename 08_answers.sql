CREATE TABLE IF NOT EXISTS answers (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    attempt_id BIGINT UNSIGNED NOT NULL,
    question_id BIGINT UNSIGNED NOT NULL,
    student_answer TEXT NOT NULL DEFAULT (''),
    ai_marks DOUBLE NOT NULL DEFAULT 0.0,
    final_marks DOUBLE NOT NULL DEFAULT 0.0,
    ai_confidence DOUBLE NOT NULL DEFAULT 1.0,
    needs_review TINYINT NOT NULL DEFAULT 0,
    ai_feedback TEXT NOT NULL DEFAULT (''),
    ai_breakdown_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
    faculty_override TINYINT NOT NULL DEFAULT 0,
    faculty_comment TEXT NOT NULL DEFAULT (''),
    FOREIGN KEY (attempt_id) REFERENCES exam_attempts (id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
    UNIQUE(attempt_id, question_id),
    KEY ix_answers_review (needs_review, faculty_override)
) ENGINE = InnoDB;
