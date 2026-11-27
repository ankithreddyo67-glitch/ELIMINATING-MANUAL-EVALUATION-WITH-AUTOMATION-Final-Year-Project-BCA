CREATE TABLE IF NOT EXISTS question_bank (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    created_by BIGINT UNSIGNED NOT NULL,
    question_type VARCHAR(255) NOT NULL,
    prompt TEXT NOT NULL,
    options_json JSON NOT NULL,
    model_answer TEXT NOT NULL,
    keywords_json JSON NOT NULL,
    max_marks DOUBLE NOT NULL,
    subject VARCHAR(255) NOT NULL,
    difficulty VARCHAR(255) NOT NULL,
    FOREIGN KEY (created_by) REFERENCES users (id)
) ENGINE = InnoDB;
