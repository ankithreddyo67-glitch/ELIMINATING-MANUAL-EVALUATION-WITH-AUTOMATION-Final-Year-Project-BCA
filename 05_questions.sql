CREATE TABLE IF NOT EXISTS questions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    exam_id BIGINT UNSIGNED NOT NULL,
    order_index INT NOT NULL DEFAULT 1,
    question_type VARCHAR(255) NOT NULL CHECK(question_type IN ('MCQ', 'TRUE_FALSE', 'SHORT', 'SUBJECTIVE', 'PROGRAMMING')),
    prompt TEXT NOT NULL,
    options_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    model_answer TEXT NOT NULL,
    keywords_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
    max_marks DOUBLE NOT NULL DEFAULT 5.0,
    subject VARCHAR(255) NOT NULL DEFAULT '',
    difficulty VARCHAR(255) NOT NULL DEFAULT 'MEDIUM',
    FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
    KEY ix_questions_exam_order (exam_id, order_index)
) ENGINE = InnoDB;
