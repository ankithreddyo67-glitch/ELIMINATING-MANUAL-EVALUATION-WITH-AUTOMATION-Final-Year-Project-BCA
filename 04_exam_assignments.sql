CREATE TABLE IF NOT EXISTS exam_assignments (
    exam_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    assigned_by BIGINT UNSIGNED,
    due_at DATETIME,
    FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users (id) ON DELETE SET NULL,
    PRIMARY KEY (exam_id, student_id)
) ENGINE = InnoDB;
