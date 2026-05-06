# API Contracts: 云盘文件操作

**Feature**: [spec.md](../spec.md)
**Updated**: 2026-05-01

## Overview

所有端点统一使用 `APIResponse<T>` 包装：
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```
错误时：
```json
{
  "code": 1,
  "message": "error description",
  "detail": "optional detail"
}
```

---

## 1. 目录列表

### `POST /cloud/{drive_type}/list`

列出云盘指定目录下的文件列表。

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `drive_type` | string | ✅ | `pikpak` \| `jianguoyun` \| `baidu` \| `aliyun` \| `quark` |

**Request Body**:
```json
{
  "path": "/documents"
}
```
- `path` 为空或不提供时，默认列出根目录 `/`

**Response** (`200 OK`):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "path": "/documents",
    "files": [
      {
        "name": "report.pdf",
        "path": "/documents/report.pdf",
        "size": 1048576,
        "is_dir": false,
        "modified": "2024-01-15T10:30:00Z",
        "mime_type": "application/pdf"
      },
      {
        "name": "archive",
        "path": "/documents/archive",
        "size": 0,
        "is_dir": true,
        "modified": "2024-01-10T08:00:00Z",
        "mime_type": null
      }
    ]
  }
}
```

**Errors**:
| code | message | condition |
|------|---------|-----------|
| 1 | `CLOUD_DRIVE_NOT_FOUND` | 云盘凭证未配置 |
| 1 | `RCLONE_NOT_FOUND` | rclone 未安装 |
| 1 | `DIRECTORY_NOT_FOUND` | 指定目录不存在 |

---

## 2. 文件详情

### `POST /cloud/{drive_type}/detail`

获取文件/文件夹的详细元数据。

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `drive_type` | string | ✅ | 同上 |

**Request Body**:
```json
{
  "path": "/documents/report.pdf"
}
```
- `path` 不能为空

**Response** (`200 OK`):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "name": "report.pdf",
    "path": "/documents/report.pdf",
    "size": 1048576,
    "is_dir": false,
    "modified": "2024-01-15T10:30:00Z",
    "mime_type": "application/pdf"
  }
}
```

**Errors**:
| code | message | condition |
|------|---------|-----------|
| 1 | `VALIDATION_ERROR` | path 为空 |
| 1 | `FILE_NOT_FOUND` | 文件不存在 |

---

## 3. 移动文件/文件夹

### `POST /cloud/{drive_type}/move`

移动文件或文件夹到目标地址。

**Path Parameters**: 同上

**Request Body**:
```json
{
  "src": "/docs/a.txt",
  "dst": "/archive/a.txt"
}
```
- `src` 不能为空
- `dst` 为目标完整路径（而非目标目录）

**Response** (`200 OK`):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "src": "/docs/a.txt",
    "dst": "/archive/a.txt",
    "moved": true
  }
}
```

**Behavior**:
- 目标目录不存在时，自动创建后再移动（FR-003）
- 若 `src` 不存在，返回 `FILE_NOT_FOUND`
- 移动后 `dst` 立即可见，原位置 `src` 立即消失

**Errors**:
| code | message | condition |
|------|---------|-----------|
| 1 | `VALIDATION_ERROR` | src 为空 |
| 1 | `FILE_NOT_FOUND` | src 不存在 |
| 1 | `PATH_ALREADY_EXISTS` | dst 已存在 |

---

## 4. 删除文件/文件夹

### `POST /cloud/{drive_type}/delete`

删除指定路径的文件或目录。

**Path Parameters**: 同上

**Request Body**:
```json
{
  "path": "/docs/to_delete.txt"
}
```
- `path` 不能为空，不能为根目录 `/`

**Response** (`200 OK`):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "deleted": true,
    "path": "/docs/to_delete.txt"
  }
}
```

**Errors**:
| code | message | condition |
|------|---------|-----------|
| 1 | `VALIDATION_ERROR` | path 为空或为 `/` |
| 1 | `FILE_NOT_FOUND` | 文件不存在 |

---

## 5. 同步文件到本地

### `POST /cloud/sync`

创建异步同步任务，立即返回 job_id。

**Request Body**:
```json
{
  "drive_type": "pikpak",
  "source_path": "/documents/data.zip",
  "local_path": "/home/user/downloads"
}
```
- `source_path` 不能为空，不存在时返回错误
- `local_path` 不能为空，不存在时自动创建
- `drive_type` 必须为有效云盘类型

**Response** (`202 Accepted` — 异步任务创建):
```json
{
  "code": 0,
  "message": "accepted",
  "data": {
    "job_id": "a1b2c3d4",
    "status": "pending",
    "source_path": "/documents/data.zip",
    "local_path": "/home/user/downloads",
    "phase": "downloading",
    "progress_bytes": 0,
    "total_bytes": 0,
    "progress_percent": 0.0,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

> SC-005：5 秒内返回 job_id

---

### `GET /cloud/sync/{job_id}/status`

查询同步任务进度。

**Response** (`200 OK`):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "job_id": "a1b2c3d4",
    "status": "running",
    "phase": "downloading",
    "progress_bytes": 52428800,
    "total_bytes": 104857600,
    "progress_percent": 50.0,
    "retry_count": 0,
    "error_message": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:31:00Z"
  }
}
```

**Status Transitions**:
- `pending` → `running` → `completed` | `failed` | `cancelled`
- `phase`: `downloading` → `moving-to-backup` → `completed`

**Errors**:
| code | message | condition |
|------|---------|-----------|
| 1 | `JOB_NOT_FOUND` | job_id 不存在 |

---

### `POST /cloud/sync/{job_id}/cancel`

取消正在运行的同步任务。

**Response** (`200 OK`):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "job_id": "a1b2c3d4",
    "status": "cancelled",
    "phase": "completed"
  }
}
```

**Behavior**:
- 仅 `running` 状态可取消
- 取消后：中断下载进程，清理临时文件，不执行 backup 移动
- `cancelled` 状态任务不移动云盘原文件

**Errors**:
| code | message | condition |
|------|---------|-----------|
| 1 | `JOB_NOT_FOUND` | job_id 不存在 |
| 1 | `INVALID_JOB_STATE` | 任务非 running 状态，无法取消 |

---

## 6. 云下载（仅 PikPak）

### `POST /cloud/pikpak/offline-download`

提交离线下载任务。

**Request Body**:
```json
{
  "urls": [
    "https://example.com/file1.zip",
    "magnet:?xt=urn:btih:abc123"
  ],
  "folder": "/My Pack"
}
```
- `urls` 至少一个 URL，为空时返回错误
- `folder` 为空时默认为 `/My Pack`

**Response** (`200 OK`):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "pikpak-task-001",
    "drive_type": "pikpak",
    "urls_count": 2,
    "destination_folder": "/My Pack",
    "status": "pending",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Errors**:
| code | message | condition |
|------|---------|-----------|
| 1 | `UNSUPPORTED_DRIVE_TYPE` | 非 PikPak 云盘 |
| 1 | `VALIDATION_ERROR` | urls 为空 |

---

## 7. 操作记录查询（审计）

### `GET /cloud/admin/operation-logs`

查询操作记录（分页）。

**Query Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `page` | integer | 1 | 页码（从 1 开始） |
| `page_size` | integer | 20 | 每页记录数（上限 100） |
| `operation` | string | null | 按操作类型过滤 |
| `drive_type` | string | null | 按云盘类型过滤 |
| `start_date` | string (ISO date) | null | 开始日期 |
| `end_date` | string (ISO date) | null | 结束日期 |

**Response** (`200 OK`):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 1523,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "id": 1001,
        "op_user": "admin",
        "drive_type": "pikpak",
        "operation": "sync_start",
        "path": "/documents/data.zip",
        "result": "success",
        "error_code": null,
        "error_message": null,
        "extra": "{\"job_id\": \"a1b2c3d4\"}",
        "ip_address": "localhost",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

---

## Error Response Format

所有错误统一返回：

| Field | Type | Description |
|-------|------|-------------|
| `code` | integer | 0 = success，1 = error |
| `message` | string | 简短错误信息（用户可见） |
| `detail` | string or null | 详细技术信息（可选） |

**常见错误码**:
| code | message | 说明 |
|------|---------|------|
| `CLOUD_DRIVE_NOT_FOUND` | 云盘未配置 | 管理员未配置该云盘凭证 |
| `RCLONE_NOT_FOUND` | rclone 未找到 | rclone 未安装或不在 PATH |
| `FILE_NOT_FOUND` | 文件不存在 | 指定路径的文件/目录不存在 |
| `DIRECTORY_NOT_FOUND` | 目录不存在 | 列表/详情时目录不存在 |
| `INVALID_PATH` | 路径无效 | 路径格式不符合要求 |
| `PATH_ALREADY_EXISTS` | 目标已存在 | 移动时目标路径已存在 |
| `VALIDATION_ERROR` | 参数错误 | 请求参数校验失败 |
| `SYNC_ERROR` | 同步失败 | 同步任务执行失败 |
| `OFFLINE_DOWNLOAD_ERROR` | 云下载失败 | 离线下载任务创建失败 |
| `UNSUPPORTED_DRIVE_TYPE` | 云盘不支持 | 该云盘不支持此操作 |
| `JOB_NOT_FOUND` | 任务不存在 | 同步 job_id 不存在 |
| `INVALID_JOB_STATE` | 任务状态错误 | 当前状态不支持该操作 |
| `OPERATION_QUEUE_FULL` | 队列已满 | 并发同步任务超过上限（5个） |
