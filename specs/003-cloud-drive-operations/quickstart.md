# Quickstart: 云盘通用文件操作

**Feature**: [spec.md](./spec.md)
**Updated**: 2026-05-01

## 前提条件

- Python 3.10+
- rclone 已安装并加入 PATH（`rclone version` 验证）
- MySQL 数据库已配置（`cloud_drive_configs`、`sync_jobs`、`offline_download_tasks`、`operation_logs` 四张表）
- `config/config_dev.yaml` 或 `config/config_prod.yaml` 已配置数据库连接和加密密钥

## 启动服务

```bash
# 开发模式
python main.py

# 生产模式（使用 config_prod.yaml）
python main.py --prod
```

服务地址：
- **HTTP API**: `http://localhost:29312`
- **MCP Server**: `http://localhost:29313`（FastMCP stateless HTTP）

## 首次配置云盘

通过 API 添加云盘凭证：

```bash
curl -X POST http://localhost:29312/cloud/admin/drives \
  -H "Content-Type: application/json" \
  -d '{
    "drive_type": "pikpak",
    "remote_name": "pikpak:",
    "username": "your@pikpak.email",
    "password": "your_password"
  }'
```

## 操作示例

### 1. 列出目录

```bash
# 列出根目录
curl -X POST http://localhost:29312/cloud/pikpak/list \
  -H "Content-Type: application/json" \
  -d '{"path": "/"}'

# 列出子目录
curl -X POST http://localhost:29312/cloud/pikpak/list \
  -H "Content-Type: application/json" \
  -d '{"path": "/documents"}'
```

### 2. 查看文件详情

```bash
curl -X POST http://localhost:29312/cloud/pikpak/detail \
  -H "Content-Type: application/json" \
  -d '{"path": "/documents/report.pdf"}'
```

### 3. 移动文件（自动创建目标目录）

```bash
curl -X POST http://localhost:29312/cloud/pikpak/move \
  -H "Content-Type: application/json" \
  -d '{"src": "/docs/a.txt", "dst": "/archive/a.txt"}'
```

> 目标目录 `/archive/` 不存在时会自动创建。

### 4. 删除文件

```bash
curl -X POST http://localhost:29312/cloud/pikpak/delete \
  -H "Content-Type: application/json" \
  -d '{"path": "/docs/to_delete.txt"}'
```

> 禁止删除根目录 `/`。

### 5. 同步文件到本地

```bash
# 发起同步任务
curl -X POST http://localhost:29312/cloud/sync \
  -H "Content-Type: application/json" \
  -d '{
    "drive_type": "pikpak",
    "source_path": "/documents/data.zip",
    "local_path": "/home/user/downloads"
  }'

# 响应（202 Accepted）：
# {
#   "code": 0,
#   "data": {
#     "job_id": "a1b2c3d4",
#     "status": "pending",
#     ...
#   }
# }

# 查询进度
curl http://localhost:29312/cloud/sync/a1b2c3d4/status

# 取消任务
curl -X POST http://localhost:29312/cloud/sync/a1b2c3d4/cancel
```

**同步流程**：
1. 下载云盘文件到本地目标路径
2. 下载成功后，将云盘原文件移动到 `/backup/` 相同路径结构
3. 支持 5 并发、10 次重试

### 6. 云下载（仅 PikPak）

```bash
curl -X POST http://localhost:29312/cloud/pikpak/offline-download \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/file.zip",
      "magnet:?xt=urn:btih:abc123"
    ],
    "folder": "/My Pack"
  }'
```

### 7. 查看操作日志

```bash
# 分页查询最近操作
curl "http://localhost:29312/cloud/admin/operation-logs?page=1&page_size=20"

# 按操作类型过滤
curl "http://localhost:29312/cloud/admin/operation-logs?operation=sync_start"

# 按日期范围过滤
curl "http://localhost:29312/cloud/admin/operation-logs?start_date=2024-01-01&end_date=2024-01-31"
```

## MCP 接口调用

MCP Server 监听 29313 端口，通过 HTTP POST 调用：

```bash
# 列表操作
curl -X POST http://localhost:29313 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "pikpak_list_files",
      "arguments": {"path": "/"}
    },
    "id": 1
  }'

# 同步到本地
curl -X POST http://localhost:29313 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "pikpak_sync_to_local",
      "arguments": {
        "source_path": "/documents/data.zip",
        "local_path": "/home/user/downloads"
      }
    },
    "id": 2
  }'
```

## 日志查看

结构化 JSON 日志输出到 `log/app.log`：

```json
{"timestamp": "2024-01-15T10:30:00Z", "level": "INFO", "logger": "sync_api", "message": "Sync job started", "extra": {"job_id": "a1b2c3d4", "drive": "pikpak"}}
{"timestamp": "2024-01-15T10:30:05Z", "level": "INFO", "logger": "sync_api", "message": "Sync job completed", "extra": {"job_id": "a1b2c3d4", "duration_s": 5}}
```

## 错误排查

| 症状 | 可能原因 | 解决方法 |
|------|----------|----------|
| `CLOUD_DRIVE_NOT_FOUND` | 云盘凭证未配置 | 管理员添加云盘凭证 |
| `RCLONE_NOT_FOUND` | rclone 未安装 | `sudo apt install rclone` 或加入 PATH |
| 同步任务一直 `pending` | 超过 5 并发上限 | 等待其他任务完成或取消 |
| 云下载返回 `OFFLINE_DOWNLOAD_ERROR` | PikPak API 认证失败 | 检查 PikPak 用户名密码是否正确 |
| `FILE_NOT_FOUND` | 源路径不存在 | 确认云盘路径正确 |
