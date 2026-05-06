# Cloud Download API Contract

**Endpoint**: `POST /cloud/pikpak/cloud-download`
**Feature**: FR-011, FR-016
**Date**: 2026-05-03

## Overview

触发 PikPak 云下载任务。调用立即返回 task_id，任务在后台跟踪状态，超时30分钟自动标记为失败。

---

## Request

### Headers

| Header | Value | Required |
|--------|-------|----------|
| Content-Type | application/json | Yes |

### Body

```json
{
  "urls": ["https://example.com/file.zip", "magnet:?xt=urn:btih:..."],
  "folder": "/My Pack"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| urls | string[] | Yes | — | HTTP URL 或 magnet URL 列表，至少1个 |
| folder | string | No | "/My Pack" | PikPak 目标文件夹路径 |

### Validation

- `urls` 数组不能为空
- 每个 URL 必须是合法的 HTTP/HTTPS URL 或以 `magnet:` 开头

---

## Response: Success (200 OK)

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "abc123xyz",
    "urls_count": 2,
    "destination_folder": "/My Pack",
    "created_at": "2026-05-03T12:00:00Z"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| task_id | string | PikPak API 返回的任务 ID |
| urls_count | int | 提交的 URL 总数 |
| destination_folder | string | 目标文件夹路径 |
| created_at | datetime | ISO 8601 格式的任务创建时间 |

---

## Response: Validation Error (500)

```json
{
  "code": "VALIDATION_ERROR",
  "message": "urls cannot be empty",
  "data": null
}
```

---

## Response: Rate Limited (500)

```json
{
  "code": "OFFLINE_DOWNLOAD_TIMEOUT",
  "message": "PikPak offline download timed out.",
  "data": {
    "detail": "Rate limit exceeded after 5 retries"
  }
}
```

---

## Background Behavior

1. **立即返回**: API 调用立即返回 `task_id`，不等待下载完成
2. **后台跟踪**: 系统使用独立线程/定时器定期查询 PikPak API 任务状态
3. **状态持久化**: 任务状态保存到 MySQL `cloud_download_jobs` 表
4. **超时机制**: 任务创建后30分钟若仍为 pending/downloading 状态，自动标记为 `TIMEOUT`
5. **服务重启恢复**: 服务重启时，从 `cloud_download_jobs` 表恢复所有未完成任务并继续跟踪

---

## Related Errors

| Code | Meaning |
|------|---------|
| VALIDATION_ERROR | 请求参数验证失败 |
| OFFLINE_DOWNLOAD_ERROR | PikPak API 调用失败（非限流） |
| OFFLINE_DOWNLOAD_TIMEOUT | 限流重试5次后仍失败，或任务超时30分钟 |
