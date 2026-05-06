"""Initialize database schema — creates tables from data-model.md."""

from __future__ import annotations

from src.core.logger import get_logger
from src.db.database import Database

logger = get_logger("init_db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sync_jobs (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    job_id          VARCHAR(64) NOT NULL UNIQUE,
    drive_type      VARCHAR(32) NOT NULL,
    source_path     VARCHAR(1024) NOT NULL,
    local_path      VARCHAR(1024) NOT NULL,
    status          VARCHAR(16) NOT NULL DEFAULT 'pending',
    phase           VARCHAR(24) NOT NULL DEFAULT 'downloading',
    progress_bytes  BIGINT NOT NULL DEFAULT 0,
    total_bytes     BIGINT NOT NULL DEFAULT 0,
    progress_percent FLOAT NOT NULL DEFAULT 0.0,
    retry_count     INT NOT NULL DEFAULT 0,
    error_message   TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_drive_type (drive_type)
);

CREATE TABLE IF NOT EXISTS cloud_download_jobs (
    id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id             VARCHAR(128) NOT NULL COMMENT 'Task ID from rclone or PikPak',
    urls                TEXT NOT NULL COMMENT 'JSON array of URLs',
    folder              VARCHAR(512) NOT NULL DEFAULT '/My Pack' COMMENT 'Destination folder',
    status              VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT 'pending/running/completed/failed/timeout',
    error_message       TEXT COMMENT 'Error details if failed',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    finished_at         DATETIME COMMENT 'Completion/failure timestamp',
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
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