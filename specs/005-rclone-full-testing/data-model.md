# Data Model: Rclone Full Testing

**Feature**: 005-rclone-full-testing | **Date**: 2026-05-03

## Overview

本功能新增 `cloud_download_jobs` MySQL 表用于持久化 PikPak 云下载任务状态，同时新增 `CloudDriveFileInUseError` 错误码用于 FR-015 占用检查。

---

## New Table: `cloud_download_jobs`

```sql
CREATE TABLE cloud_download_jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(128) NOT NULL COMMENT 'PikPak API returned task ID',
    urls TEXT NOT NULL COMMENT 'JSON array of URLs to download',
    folder VARCHAR(512) NOT NULL DEFAULT '/My Pack' COMMENT 'Destination folder on PikPak',
    status ENUM('pending', 'downloading', 'completed', 'failed', 'timeout') NOT NULL DEFAULT 'pending',
    error_message TEXT COMMENT 'Error details if failed or timeout',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    finished_at DATETIME COMMENT 'Completion/failure timestamp (NULL if still running)',
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='PikPak cloud download job tracking';
```

### Field Descriptions

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 内部主键 |
| task_id | VARCHAR(128) | NOT NULL | PikPak API 返回的任务 ID，用于查询任务状态 |
| urls | TEXT | NOT NULL | HTTP 或 magnet URL 列表，JSON 数组格式 |
| folder | VARCHAR(512) | NOT NULL, DEFAULT '/My Pack' | 下载目标文件夹路径 |
| status | ENUM | NOT NULL, DEFAULT 'pending' | 任务状态机：pending → downloading → completed/failed/timeout |
| error_message | TEXT | NULLABLE | 失败或超时时的错误详情 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 任务创建时间 |
| updated_at | DATETIME | NOT NULL, AUTO UPDATE | 最后更新时间 |
| finished_at | DATETIME | NULLABLE | 任务完成/失败时间，running 状态下为 NULL |

### State Machine

```
pending → downloading → completed
                    └→ failed
                    └→ timeout (30 min watchdog)
```

---

## New Error Code: `FILE_IN_USE`

| Field | Value |
|-------|-------|
| CODE | `FILE_IN_USE` |
| HTTP Status | 500 (application-level error) |
| MESSAGE | `The file is currently being used by another operation` |
| Used in | `CloudDriveService.delete()`, `CloudDriveService.move()` |

### When Raised

当尝试删除或移动一个文件，且该文件正被一个活跃的同步任务（sync_jobs 表中状态为 PENDING 或 RUNNING）使用时，抛出此错误。

### Exception Class

```python
class CloudDriveFileInUseError(CloudDriveError2):
    CODE = "FILE_IN_USE"
    MESSAGE = "The file is currently being used by another operation."
```

---

## Existing Table: `sync_jobs` (Reference)

```sql
CREATE TABLE sync_jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL COMMENT 'UUID of the sync job',
    drive_type ENUM('pikpak', 'jianguoyun', 'baiduyun') NOT NULL,
    source_path VARCHAR(1024) NOT NULL,
    local_path VARCHAR(1024) NOT NULL,
    status ENUM('pending', 'running', 'completed', 'failed', 'cancelled') NOT NULL DEFAULT 'pending',
    phase ENUM('downloading', 'moving-to-backup', 'completed') NOT NULL DEFAULT 'downloading',
    progress_bytes BIGINT NOT NULL DEFAULT 0,
    total_bytes BIGINT NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    finished_at DATETIME,
    UNIQUE KEY uk_job_id (job_id),
    INDEX idx_status (status),
    INDEX idx_drive_type (drive_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Existing Table: `operation_logs` (Reference)

```sql
CREATE TABLE operation_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    op_user VARCHAR(64) NOT NULL DEFAULT 'admin',
    drive_type VARCHAR(32),
    operation VARCHAR(32) NOT NULL COMMENT 'list, detail, move, delete, cloud_download, sync_start, sync_cancel',
    path VARCHAR(1024),
    result ENUM('success', 'failed') NOT NULL,
    error_code VARCHAR(64),
    error_message TEXT,
    extra JSON,
    ip_address VARCHAR(64) NOT NULL DEFAULT 'localhost',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operation (operation),
    INDEX idx_drive_type (drive_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Pydantic Schema Changes

### New: `CloudDownloadJobSchema`

```python
class CloudDownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class CloudDownloadJobSchema(BaseModel):
    id: int
    task_id: str
    urls: list[str]
    folder: str
    status: CloudDownloadStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
```

### Updated: `APIResponse.error()` — supports `CloudDriveFileInUseError`
