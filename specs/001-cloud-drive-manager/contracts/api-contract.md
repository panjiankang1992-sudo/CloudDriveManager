# API Contract: Cloud Drive Manager

**Feature**: Cloud Drive Manager
**Date**: 2026-04-26
**Base URL**: `http://{host}:{port}`
**默认端口**: `8000`

---

## 统一响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误响应

```json
{
  "code": 1,
  "message": "文件不存在: /nonexistent.txt",
  "error_code": "PIKPAK_FILE_NOT_FOUND"
}
```

**HTTP 状态码**:
| HTTP Status | 含义 |
|-------------|------|
| 200 | 业务成功 |
| 400 | 参数错误 |
| 403 | 禁止操作（如删除根目录） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 健康检查

### GET /health

检查服务是否就绪。

**响应 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "healthy",
    "version": "1.0.0"
  }
}
```

---

## 云盘通用操作

所有云盘操作均遵循 `/cloud/{drive_type}/{operation}` 路由格式。

### 支持的云盘类型 (drive_type)

| drive_type | 云盘名称 |
|------------|---------|
| `pikpak` | PikPak |
| `jianguoyun` | 坚果云 |
| `baidu` | 百度云 |
| `aliyun` | 阿里云盘 |
| `quark` | 夸克云 |

---

### GET /cloud/{drive_type}/list

列出云盘目录内容。

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `drive_type` | string | 是 | 云盘类型 |

**查询参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `path` | string | 否 | `/` | 云盘路径（绝对路径） |

**响应 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "path": "/",
    "items": [
      {
        "name": "downloads",
        "path": "/downloads",
        "size": 0,
        "type": "folder",
        "modified_time": "2026-04-01T10:30:00Z",
        "mime_type": null
      },
      {
        "name": "readme.txt",
        "path": "/readme.txt",
        "size": 1024,
        "type": "file",
        "modified_time": "2026-04-01T10:30:00Z",
        "mime_type": "text/plain"
      }
    ],
    "total": 2
  }
}
```

**错误码**:
| error_code | HTTP Status | 说明 |
|------------|-------------|------|
| `CLOUD_DRIVE_NOT_CONFIGURED` | 500 | 云盘未配置 |
| `RCLONE_NETWORK_ERROR` | 500 | rclone 网络错误 |

---

### GET /cloud/{drive_type}/detail

获取文件/文件夹详细信息。

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `drive_type` | string | 是 | 云盘类型 |

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | 是 | 云盘路径（绝对路径） |

**响应 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "name": "readme.txt",
    "path": "/readme.txt",
    "size": 1024,
    "type": "file",
    "modified_time": "2026-04-01T10:30:00Z",
    "mime_type": "text/plain"
  }
}
```

**错误码**:
| error_code | HTTP Status | 说明 |
|------------|-------------|------|
| `CLOUD_DRIVE_NOT_CONFIGURED` | 500 | 云盘未配置 |
| `CLOUD_DRIVE_FILE_NOT_FOUND` | 404 | 文件/文件夹不存在 |

---

### POST /cloud/{drive_type}/download

下载云盘文件到本地（请求体指定本地路径）。

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `drive_type` | string | 是 | 云盘类型 |

**请求体**:
```json
{
  "cloud_path": "/readme.txt",
  "local_path": "D:/Downloads/readme.txt"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cloud_path` | string | 是 | 云盘文件路径 |
| `local_path` | string | 是 | 本地目标路径 |

**响应 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "cloud_path": "/readme.txt",
    "local_path": "D:/Downloads/readme.txt",
    "size": 1024
  }
}
```

**错误码**:
| error_code | HTTP Status | 说明 |
|------------|-------------|------|
| `CLOUD_DRIVE_NOT_CONFIGURED` | 500 | 云盘未配置 |
| `CLOUD_DRIVE_FILE_NOT_FOUND` | 404 | 云盘文件不存在 |
| `CLOUD_DRIVE_LOCAL_PATH_INVALID` | 400 | 本地路径无效或无法写入 |

---

### POST /cloud/{drive_type}/delete

删除云盘文件或文件夹。

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `drive_type` | string | 是 | 云盘类型 |

**请求体**:
```json
{
  "path": "/downloads/old_file.txt"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | 是 | 要删除的云盘路径 |

**响应 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "path": "/downloads/old_file.txt",
    "deleted": true
  }
}
```

**错误码**:
| error_code | HTTP Status | 说明 |
|------------|-------------|------|
| `CLOUD_DRIVE_NOT_CONFIGURED` | 500 | 云盘未配置 |
| `CLOUD_DRIVE_FILE_NOT_FOUND` | 404 | 文件不存在 |
| `CLOUD_DRIVE_ROOT_DELETE_FORBIDDEN` | 403 | 禁止删除根目录 |
| `RCLONE_DELETE_ERROR` | 500 | rclone 删除失败 |

---

### POST /cloud/{drive_type}/move

移动或重命名云盘文件/文件夹。

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `drive_type` | string | 是 | 云盘类型 |

**请求体**:
```json
{
  "source_path": "/downloads/old_name.txt",
  "dest_path": "/downloads/new_name.txt"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source_path` | string | 是 | 源路径 |
| `dest_path` | string | 是 | 目标路径 |

**响应 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "source_path": "/downloads/old_name.txt",
    "dest_path": "/downloads/new_name.txt",
    "moved": true
  }
}
```

---

## 同步操作

### POST /cloud/sync

在两个云盘之间同步文件。

**请求体**:
```json
{
  "source_drive": "pikpak",
  "source_path": "/downloads",
  "dest_drive": "jianguoyun",
  "dest_path": "/backup/downloads",
  "delete_excluded": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source_drive` | string | 是 | 源云盘类型 |
| `source_path` | string | 是 | 源路径 |
| `dest_drive` | string | 是 | 目标云盘类型 |
| `dest_path` | string | 是 | 目标路径 |
| `delete_excluded` | boolean | 否 | 是否删除目标有而源没有的文件（默认 false） |

**响应 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "source": "pikpak:/downloads",
    "dest": "jianguoyun:/backup/downloads",
    "delete_excluded": false,
    "synced": true
  }
}
```

---

## PikPak 特有接口

### POST /cloud/pikpak/offline-download

添加离线下载任务（PikPak 特有）。

**请求体**:
```json
{
  "urls": ["https://example.com/file.zip"],
  "destination_folder": "/downloads"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `urls` | `list[string]` | 是 | 下载链接列表 |
| `destination_folder` | string | 否 | 目标文件夹（默认 `/downloads`） |

**响应 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total_urls": 1,
    "added_tasks": [
      {
        "url": "https://example.com/file.zip",
        "task_id": "pikpak_task_1745689200000",
        "status": "pending"
      }
    ],
    "failed_urls": [],
    "target_folder": "/downloads"
  }
}
```

---

## 全局错误码

以下错误码可在任何 API 响应中出现：

| error_code | 说明 |
|------------|------|
| `CONFIG_KEY_NOT_FOUND` | 配置文件缺少必需键 |
| `CONFIG_FILE_NOT_FOUND` | 配置文件未找到 |
| `ENCRYPTION_SALT_INVALID` | 加密盐值无效 |
| `DECRYPTION_FAILED` | 密码解密失败 |
| `RCLONE_NOT_FOUND` | rclone 可执行文件不存在 |
| `RCLONE_NETWORK_ERROR` | rclone 网络连接错误 |
| `RCLONE_TIMEOUT` | rclone 命令超时 |
| `CLOUD_DRIVE_NOT_CONFIGURED` | 云盘类型未配置 |
| `CLOUD_DRIVE_FILE_NOT_FOUND` | 云盘文件/文件夹不存在 |
| `CLOUD_DRIVE_ROOT_DELETE_FORBIDDEN` | 禁止删除根目录 |