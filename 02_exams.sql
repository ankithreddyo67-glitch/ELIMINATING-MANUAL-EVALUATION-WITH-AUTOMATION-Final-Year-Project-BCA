CREATE TABLE IF NOT EXISTS exams (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    duration_minutes INT NOT NULL DEFAULT 30,
    passing_percentage DOUBLE NOT NULL DEFAULT 40.0,
    proctoring_enabled TINYINT NOT NULL DEFAULT 1,
    proctoring_strictness VARCHAR(255) NOT NULL DEFAULT 'MEDIUM' CHECK(proctoring_strictness IN ('LOW', 'MEDIUM', 'HIGH')),
    max_warnings INT NOT NULL DEFAULT 5,
    auto_submit_on_warning_limit TINYINT NOT NULL DEFAULT 1,
    status VARCHAR(255) NOT NULL DEFAULT 'PUBLISHED' CHECK(status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    created_by BIGINT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    restricted TINYINT NOT NULL DEFAULT 0,
    opens_at DATETIME,
    closes_at DATETIME,
    FOREIGN KEY (created_by) REFERENCES users (id)
) ENGINE = InnoDB;
