# Implementation Plan: 云盘通用文件操作

**Branch**: `003-cloud-drive-operations` | **Date**: 2026-05-01
**Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/003-cloud-drive-operations/spec.md`

## Summary

为 5 个云盘（PikPak、JianGuoYun、Baidu、Aliyun、Quark）实现统一的文件操作接口。

**已有（无需修改）**：列表、详情、删除、基础移动（rclone adapter 已实现）
**需要实现**：
1. 移动操作自动创建目标目录（rclone moveto 不会自动创建父目录）
2. PikPak 云下载（离线下载）— 调用 PikPak API，非 rclone
3. 异步同步任务 + 进度查询（当前为同步阻塞，需改造为后台任务）

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastAPI, PyMySQL, cryptography (Fernet), rclone CLI
**Storage**: MySQL (cloud_drive_configs 表) + in-memory job store (dict)
**Testing**: pytest
**Target Platform**: Linux/WSL
**Project Type**: HTTP REST API service
**Performance Goals**: 列表操作 < 5 秒（100 文件以内）
**Scale/Scope**: 5 个并发同步任务

## Constitution Check

Constitution 文件（`.specify/memory/constitution.md`）目前为模板占位符，无实质约束。

## Project Structure

### Source Code (D:\MyCode\CloudDriveManager)

```text
src/
├── adapters/
│   └── rclone_adapter.py      # 已有：list, detail, delete, moveto, copyto
├── services/
│   ├── base.py               # 已有：CloudDriveService 抽象类
│   ├── pikpak.py             # 需修改：cloud_download_add 改为真实实现
│   ├── jianguoyun.py         # 已有（代理到 rclone_adapter）
│   ├── baidu.py              # 已有（代理到 rclone_adapter）
│   ├── aliyun.py             # 已有（代理到 rclone_adapter）
│   ├── quark.py              # 已有（代理到 rclone_adapter）
│   └── sync_manager.py       # 新增：SyncJobManager（内存任务队列 + 进度追踪）
├── api/
│   ├── cloud.py              # 已有：cloud drive routers
│   ├── sync.py               # 需修改：改为异步任务创建 + 进度查询
│   └── pikpak_offline.py     # 新增：PikPak 离线下载 API endpoints
├── core/
│   ├── exceptions.py          # 已有
│   ├── schemas.py            # 已有 + 新增 SyncJobSchema
│   └── logger.py             # 已有
└── mcp/
    └── server.py             # 已有（FastMCP server）

tests/
├── unit/
│   └── test_rclone_adapter.py
├── integration/
│   └── test_cloud_operations.py
└── contract/
    └── test_api_contracts.py
```

## Complexity Tracking

> 无 Constitution 违规，无需记录。

## Implementation Notes

### 1. 移动自动创建目录（FR-003 补充）

rclone `moveto` 不会自动创建目标目录的父目录。需在执行 moveto 前先用 `rclone mkdir` 创建目标目录。

### 2. PikPak 云下载（FR-005）

PikPak 有官方 API，需通过 HTTP 调用（非 rclone）：
- API Base: `https://api.mypikpak.com`
- 离线下载接口：`POST /v1/download`
- 需 OAuth2 认证（username/password → access_token）
- 认证 token 需通过 PikPak API 获取并存入 DB

### 3. 异步同步任务（FR-006/FR-007）

同步任务改造方案：
- `SyncJobManager`：内存任务队列（`dict[job_id, SyncJob]`）
- `/cloud/sync` → 创建任务，立即返回 `job_id`（202 Accepted）
- `/cloud/sync/{job_id}/status` → 查询进度
- 后台使用 `threading.Thread` 或 `asyncio.create_task` 执行
- rclone copy 支持 `--progress` 可用于进度追踪

### 4. 目录结构（FR-001/FR-002）

已有功能（`list_files` / `list_detail`），验证即可。
