# Data Model: Cloud Drive Manager

**Feature**: Cloud Drive Manager
**Date**: 2026-04-26

---

## 实体定义

### 1. FileInfo（云盘文件/文件夹信息）

跨所有云盘统一的文件元数据结构，由 RcloneAdapter 从 rclone lsjson 输出转换而来。

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 文件或文件夹名称 |
| `path` | `str` | 云盘绝对路径（如 `/downloads/file.txt`） |
| `size` | `int` | 文件大小（字节）；文件夹为 0 或 -1 |
| `type` | `str` | `"file"` 或 `"folder"` |
| `modified_time` | `str` | ISO 8601 格式修改时间 |
| `mime_type` | `str \| None` | MIME 类型（可选，rclone 可能不返回） |

**Source**: 由 `rclone lsjson <remote:path>` 输出转换而来（见 rclone_adapter.py）

---

### 2. CloudDriveConfig（云盘配置）

每种云盘在配置文件中对应的配置项。

| 字段 | 类型 | 说明 |
|------|------|------|
| `remote_name` | `str` | rclone remote 名称（如 `mypikpak`） |
| `rclone_path` | `str` | rclone 可执行文件路径 |
| `max_retries` | `int` | 最大重试次数（默认 3） |
| `timeout` | `int` | 单次操作超时（秒） |
| `encrypted_password` | `str \| None` | 加密后的密码（Fernet 密文） |
| `username` | `str \| None` | 用户名（如云盘需要） |

**示例配置**（config_dev.yaml）:
```yaml
pikpak:
  remote_name: mypikpak
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 3
  timeout: 300

jianguoyun:
  remote_name: myjianguoyun
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 3
  timeout: 300
```

---

### 3. ServiceConfig（服务全局配置）

服务级别的配置，与具体云盘无关。

| 字段 | 类型 | 说明 |
|------|------|------|
| `mode` | `"dev" \| "prod"` | 运行环境模式（决定加载哪个配置文件） |
| `host` | `str` | 服务监听地址（默认 `0.0.0.0`） |
| `port` | `int` | 服务监听端口（默认 `8000`） |
| `log_level` | `str` | 日志级别（`DEBUG`/`INFO`/`WARNING`/`ERROR`） |
| `log_max_bytes` | `int` | 日志文件最大大小（默认 `10485760` = 10MB） |
| `log_backup_count` | `int` | 日志保留文件数（默认 `10`） |
| `log_retention_days` | `int` | 日志保留天数（默认 `7`） |

---

### 4. EncryptionConfig（加密配置）

| 字段 | 类型 | 说明 |
|------|------|------|
| `salt` | `str` | Fernet 密钥（44字符 URL-safe base64） |

---

### 5. CloudDriveError（统一异常）

所有云盘相关异常的基类。

| 字段 | 类型 | 说明 |
|------|------|------|
| `error_code` | `str` | 字符串错误码（如 `CONFIG_KEY_NOT_FOUND`） |
| `message` | `str` | 人类可读的错误描述 |
| `http_status` | `int` | 对应 HTTP 状态码 |

**异常类层次**:
```
CloudDriveError (基类)
├── ConfigError (配置相关)
│   ├── ConfigKeyNotFoundError
│   └── ConfigFileNotFoundError
├── EncryptionError (加密相关)
│   ├── EncryptionSaltInvalidError
│   └── DecryptionFailedError
├── RCloneError (rclone 执行相关)
│   ├── RCloneNotFoundError
│   ├── RCloneNetworkError
│   └── RCloneTimeoutError
├── CloudDriveError (云盘操作相关)
│   ├── CloudDriveFileNotFoundError
│   ├── CloudDrivePermissionError
│   └── CloudDriveNotConfiguredError
```

**错误码命名规范**: `{MODULE}_{SHORT_NAME}`，如 `RCLONE_NETWORK_ERROR`、`PIKPAK_FILE_NOT_FOUND`

---

### 6. APIResponse（统一 API 响应）

所有 HTTP API 响应的统一结构。

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | `int` | 业务状态码（0=成功，非0=失败） |
| `message` | `str` | 状态描述 |
| `data` | `Any \| None` | 成功时的返回数据 |
| `error_code` | `str \| None` | 失败时的字符串错误码 |

**HTTP 状态码映射**:
- `200`: 业务成功
- `400`: 参数错误（如路径格式错误）
- `401`: 认证错误
- `403`: 权限不足（如禁止删除根目录）
- `404`: 资源不存在（如文件未找到）
- `500`: 服务器内部错误

---

### 7. FileListResponseData（文件列表响应数据）

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | `str` | 查询的云盘路径 |
| `items` | `list[FileInfo]` | 文件/文件夹列表 |
| `total` | `int` | 列表中项目数量 |

---

### 8. SyncRequest（同步请求）

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_drive` | `str` | 源云盘类型（如 `pikpak`） |
| `source_path` | `str` | 源路径 |
| `dest_drive` | `str` | 目标云盘类型（如 `jianguoyun`） |
| `dest_path` | `str` | 目标路径 |
| `delete_excluded` | `bool` | 同步时是否删除目标有而源没有的文件（默认 False） |

---

## 关系图

```
Config (单例，读取 config_dev.yaml / config_prod.yaml)
  ├── ServiceConfig (服务全局配置)
  ├── EncryptionConfig (盐值)
  └── CloudDriveConfig (每个云盘一个)
        ├── RcloneAdapter (调用 rclone 命令)
        └── CloudDriveService (业务逻辑)
              └── CloudDriveAPI (HTTP 路由层)
                    └── APIResponse (统一响应格式)
```

---

## 验证规则

| 实体 | 验证规则 |
|------|----------|
| `CloudDriveConfig.remote_name` | 非空字符串 |
| `CloudDriveConfig.rclone_path` | 文件存在且可执行 |
| `EncryptionConfig.salt` | 非空，Fernet 密钥格式（44字符 base64） |
| `CloudDriveError.error_code` | 非空，符合 `{MODULE}_{NAME}` 格式 |
| `FileInfo.path` | 以 `/` 开头的绝对路径 |
| `SyncRequest.source_drive` | 必须为支持的云盘类型之一 |