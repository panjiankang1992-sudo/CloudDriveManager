"""Initialize database schema — creates tables from data-model.md."""

from __future__ import annotations

from src.core.logger import get_logger
from src.db.database import Database

logger = get_logger("init_db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_id          VARCHAR(64) NOT NULL UNIQUE,
    type            VARCHAR(32) NOT NULL COMMENT 'sync or cloud_download',
    drive_type      VARCHAR(32) NOT NULL COMMENT 'pikpak/jianguoyun/baiduyun',
    source          TEXT COMMENT 'JSON: source_path for sync, urls array for cloud_download',
    destination     VARCHAR(1024) NOT NULL COMMENT 'local_path for sync, folder for cloud_download',
    status          VARCHAR(16) NOT NULL DEFAULT 'pending',
    phase           VARCHAR(24) NOT NULL DEFAULT 'downloading',
    progress_bytes  BIGINT NOT NULL DEFAULT 0,
    total_bytes     BIGINT NOT NULL DEFAULT 0,
    progress_percent FLOAT NOT NULL DEFAULT 0.0,
    retry_count     INT NOT NULL DEFAULT 0,
    error_message   TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    finished_at     DATETIME COMMENT 'Completion/failure timestamp',
    INDEX idx_job_id (job_id),
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_drive_type (drive_type),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    op_user       VARCHAR(64) NOT NULL DEFAULT 'admin',
    drive_type    VARCHAR(32),
    operation     VARCHAR(32) NOT NULL,
    path          VARCHAR(1024),
    result        VARCHAR(16) NOT NULL,
    error_code    VARCHAR(64),
    error_message TEXT,
    extra         JSON,
    ip_address    VARCHAR(64) NOT NULL DEFAULT 'localhost',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_op_user_created (op_user, created_at),
    INDEX idx_drive_type_created (drive_type, created_at),
    INDEX idx_operation_created (operation, created_at)
);
"""


def init_db() -> None:
    """Create all tables if they don't exist."""
    db = Database.get()
    logger.info("Initializing database schema...")

    # Execute each CREATE TABLE statement separately
    for statement in SCHEMA_SQL.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            db.execute(stmt + ";")
            logger.info(f"  Executed: {stmt[:60]}...")

    logger.info("Database schema initialized successfully.")


if __name__ == "__main__":
    init_db()