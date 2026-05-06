# Data Model: 云盘通用文件操作

**Feature**: [spec.md](./spec.md)
**Updated**: 2026-05-01

## Overview

本数据模型覆盖 6 个实体：FileInfo、SyncJob、CloudDriveConfig、OfflineDownloadTask、OperationLog、SyncJobCancelToken。

---

## Entity Definitions

### 1. FileInfo（云盘文件）

表示云盘上的一个文件或目录条目。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | 文件名（不含路径） |
| `path` | string | ✅ | 完整路径（如 `/documents/a.txt`） |
| `size` | integer | ✅ | 文件大小（字节）；目录为 0 |
| `is_dir` | boolean | ✅ | true = 目录，false = 文件 |
| `modified` | string (ISO 8601) | ✅ | 最后修改时间，格式 `2024-01-01T12:00:00Z` |
| `mime_type` | string or null | ✅ | MIME 类型；目录可为空 |

**Validation**:
- `path` 必须以 `/` 开头（绝对路径）
- `name` 不能包含字符 `/`
- `size` >= 0

---

### 2. SyncJob（同步任务）

表示一次异步同步到本地的任务生命周期。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_id` | string (UUID) | ✅ | 全局唯一任务 ID |
| `source_path` | string | ✅ | 云盘源路径（绝对路径） |
| `local_path` | string | ✅ | 本地目标目录（绝对路径） |
| `status` | enum | ✅ | `pending` \| `running` \| `completed` \| `failed` \| `cancelled` |
| `phase` | enum | ✅ | `downloading` \| `moving-to-backup` \| `completed` |
| `progress_bytes` | integer | ✅ | 已下载字节数 |
| `total_bytes` | integer | ✅ | 总字节数 |
| `progress_percent` | float | ✅ | 完成百分比（0.0~100.0） |
| `created_at` | string (ISO 8601) | ✅ | 任务创建时间 |
| `updated_at` | string (ISO 8601) | ✅ | 最后更新时间 |
| `error_message` | string or null | ✅ | 失败原因（失败时填写） |
| `retry_count` | integer | ✅ | 当前重试次数（默认 0） |
| `drive_type` | string | ✅ | 云盘类型：`pikpak` \| `jianguoyun` \| `baidu` \| `aliyun` \| `quark` |

**Status State Machine**:

```
pending → running → completed
                ↘ failed
                ↘ cancelled
```

- `pending`：任务已创建，等待调度
- `running`：下载中（phase=`downloading`）或备份移动中（phase=`moving-to-backup`）
- `completed`：下载完成且备份移动成功（或跳过）
- `failed`：重试 10 次后仍失败
- `cancelled`：管理员主动取消

**Phase State Machine**:

```
downloading → moving-to-backup → completed
```

- `downloading`：正在下载文件到本地
- `moving-to-backup`：下载完成，正在将云盘原文件移动到 `/backup/`
- `completed`：全部完成

**Validation**:
- `job_id` 为 UUID v4 格式
- `source_path` 不能为空
- `local_path` 不能为空
- `retry_count` 上限为 10

---

### 3. CloudDriveConfig（云盘配置）

存储各云盘的 rclone 配置和认证凭证（已在 spec 002 中定义，此处补充完整字段）。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | ✅ | 主键，自增 |
| `drive_type` | string | ✅ | 云盘类型（唯一索引） |
| `remote_name` | string | ✅ | rclone remote 名称（如 `pikpak:`） |
| `rclone_path` | string | ✅ | rclone 可执行文件路径（默认 `rclone`） |
| `username` | string | ✅ | 云盘用户名（用于 API 认证） |
| `password_encrypted` | string | ✅ | Fernet 加密后的密码密文 |
| `is_enabled` | boolean | ✅ | 是否启用（默认 true） |
| `created_at` | string (ISO 8601) | ✅ | 创建时间 |
| `updated_at` | string (ISO 8601) | ✅ | 更新时间 |

**Notes**:
- `password_encrypted` 使用 Fernet 对称加密，key 来自 `config.yaml` 的 `encryption.salt`
- `remote_name` 必须符合 rclone remote 命名规则（字母数字下划线）

---

### 4. OfflineDownloadTask（离线下载任务）

表示一个 PikPak 离线下载任务。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | ✅ | PikPak 返回的任务 ID |
| `drive_type` | string | ✅ | 固定为 `pikpak` |
| `urls` | list[string] | ✅ | 待下载的 URL 列表 |
| `destination_folder` | string | ✅ | 目标云盘目录（默认 `/My Pack`） |
| `status` | enum | ✅ | `pending` \| `running` \| `completed` \| `failed` |
| `created_at` | string (ISO 8601) | ✅ | 创建时间 |
| `updated_at` | string (ISO 8601) | ✅ | 更新时间 |
| `error_message` | string or null | ✅ | 失败原因 |

**Validation**:
- `urls` 至少包含一个有效 URL
- `destination_folder` 必须以 `/` 开头或为空（空时默认 `/My Pack`）

---

### 5. OperationLog（操作记录）

结构化审计日志，写入 MySQL 操作记录表（SC-008 要求：500ms 内写入）。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | ✅ | 主键，自增 |
| `op_user` | string | ✅ | 操作人（固定为 `"admin"`，个人工具无多用户） |
| `drive_type` | string or null | ✅ | 云盘类型（操作指定云盘时填写） |
| `operation` | string | ✅ | 操作类型：`list` \| `detail` \| `move` \| `delete` \| `offline_download` \| `sync_start` \| `sync_cancel` \| `admin_add` \| `admin_update` \| `admin_delete` |
| `path` | string or null | ✅ | 操作的云盘路径（若无路径则为空） |
| `result` | string | ✅ | 结果：`success` \| `failed` |
| `error_code` | string or null | ✅ | 错误码（如 `FILE_NOT_FOUND`，成功时为空） |
| `error_message` | string or null | ✅ | 错误详情（成功时为空） |
| `extra` | JSON string or null | ✅ | 额外信息（JSON 格式，如 `{ "job_id": "xxx" }`） |
| `ip_address` | string | ✅ | 调用方 IP（FastAPI Request，固定为 `"localhost"`） |
| `created_at` | string (ISO 8601) | ✅ | 操作时间 |

**Indexes**:
- `idx_op_user_created` on (`op_user`, `created_at`)
- `idx_drive_type_created` on (`drive_type`, `created_at`)
- `idx_operation_created` on (`operation`, `created_at`)

**Validation**:
- `op_user` 固定为 `"admin"`
- `operation` 必须在允许的枚举值内
- `created_at` 写入延迟 ≤ 500ms（SC-008）

---

## Relationships

```
CloudDriveConfig (1) ─── has many ──── (N) SyncJob
CloudDriveConfig (1) ─── has many ──── (N) OfflineDownloadTask
SyncJob (N) ──── belongs to ──── (1) CloudDriveConfig
OperationLog (N) ──── records ──── (1) SyncJob (via job_id in extra)
```

---

## Database Schema (MySQL)

```sql
CREATE TABLE cloud_drive_configs (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    drive_type  VARCHAR(32) NOT NULL UNIQUE,
    remote_name VARCHAR(128) NOT NULL,
    rclone_path VARCHAR(256) NOT NULL DEFAULT 'rclone',
    username    VARCHAR(256) NOT NULL,
    password_encrypted TEXT NOT NULL,
    is_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE sync_jobs (
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

CREATE TABLE offline_download_tasks (
    id                  INT PRIMARY KEY AUTO_INCREMENT,
    task_id             VARCHAR(128) NOT NULL,
    drive_type          VARCHAR(32) NOT NULL DEFAULT 'pikpak',
    urls                JSON NOT NULL,
    destination_folder  VARCHAR(1024) NOT NULL DEFAULT '/My Pack',
    status              VARCHAR(16) NOT NULL DEFAULT 'pending',
    error_message       TEXT,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_task_id (task_id)
);

CREATE TABLE operation_logs (
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
```

---

## SyncJob Cancel Token

任务取消不依赖独立实体，而是通过内存中的 `threading.Event` 实现：

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | 要取消的 job_id |
| `cancel_event` | `threading.Event` | 信号量；调用 `cancel_event.set()` 触发取消 |

**取消流程**:
1. `POST /cloud/sync/{job_id}/cancel` 收到请求
2. 从 `SyncJobManager._jobs[job_id]` 找到对应的 `cancel_event`
3. 调用 `cancel_event.set()`
4. Background thread 检测到 `cancel_event.is_set()` → 停止下载，清理临时文件，删除 job 记录

---

## Enums Summary

| Entity | Field | Values |
|--------|-------|--------|
| SyncJob | `status` | `pending`, `running`, `completed`, `failed`, `cancelled` |
| SyncJob | `phase` | `downloading`, `moving-to-backup`, `completed` |
| OfflineDownloadTask | `status` | `pending`, `running`, `completed`, `failed` |
| OperationLog | `operation` | `list`, `detail`, `move`, `delete`, `offline_download`, `sync_start`, `sync_cancel`, `admin_add`, `admin_update`, `admin_delete` |
| OperationLog | `result` | `success`, `failed` |
