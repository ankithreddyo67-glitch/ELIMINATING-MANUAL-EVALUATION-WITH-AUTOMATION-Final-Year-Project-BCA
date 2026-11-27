CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    actor_id BIGINT UNSIGNED,
    action VARCHAR(255) NOT NULL,
    target_type VARCHAR(255) NOT NULL DEFAULT '',
    target_id BIGINT UNSIGNED,
    details TEXT NOT NULL DEFAULT (''),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actor_id) REFERENCES users (id) ON DELETE SET NULL,
    KEY ix_audit_created_at (created_at)
) ENGINE = InnoDB;
