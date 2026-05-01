# Implementation Plan: 云盘通用文件操作

**Branch**: `003-cloud-drive-operations` | **Date**: 2026-05-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/003-cloud-drive-operations/spec.md`

## Summary

为 5 个云盘（PikPak、JianGuoYun、Baidu、Aliyun、Quark）实现统一的文件操作接口（列表/详情/移动/删除/云下载/同步本地），包含异步任务队列、进度追踪、任务取消、操作审计日志。

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastAPI, rclone CLI, MySQL (PyMySQL), cryptography (Fernet), FastMCP, Pydantic v2, uvicorn
**Storage**: MySQL (cloud_drive_configs 表) + in-memory SyncJobManager + structured JSON file logs
**Testing**: pytest
**Target Platform**: Linux/WSL (Ubuntu 24.04)
**Project Type**: HTTP REST API service + MCP interface (FastMCP)
**Performance Goals**: 列表操作 < 5s（100 文件内），5 个并发同步任务稳定运行
**Constraints**: SC-008（API 操作 500ms 内写入操作记录表），JSON 日志 buffered flush ≤ 5s，10 次重试 95% 完成率
**Scale/Scope**: 5 个云盘并发管理，5 个同步任务并发，1 个管理员（无多用户）

## Constitution Check

> Constitution 文件（`.specify/memory/constitution.md`）为模板占位符，无实质约束，无需 gate 检查。

| Gate | Status |
|------|--------|
| Constitution 约束检查 | ✅ N/A（Constitution 为空模板） |

## Project Structure

### Documentation (this feature)

```text
specs/003-cloud-drive-operations/
├── plan.md              # 本文件
├── research.md          # Phase 0 研究结论
├── data-model.md        # Phase 1 数据模型
├── quickstart.md        # Phase 1 快速开始指南
├── contracts/           # Phase 1 接口契约
│   └── sync-job-api.md  # 同步任务 API 端点契约
└── tasks.md             # Phase 2 任务清单（/speckit.tasks 输出）
```

### Source Code

```text
src/
├── adapters/
│   └── rclone_adapter.py     # rclone CLI 封装（已有：list/detail/delete/moveto/copy）
├── services/
│   ├── base.py               # CloudDriveService 抽象类（已有）
│   ├── pikpak.py             # 需修改：cloud_download_add 改为真实 PikPak API
│   ├── jianguoyun.py         # 已有（rclone 代理）
│   ├── baidu.py              # 已有（rclone 代理）
│   ├── aliyun.py             # 已有（rclone 代理）
│   ├── quark.py              # 已有（rclone 代理）
│   └── sync_manager.py       # 新增：SyncJobManager（内存任务队列 + 进度追踪）
├── api/
│   ├── cloud.py              # 已有：cloud drive 路由
│   ├── sync.py               # 需修改：改为异步任务创建 + status 端点 + cancel 端点
│   ├── pikpak_offline.py     # 新增：PikPak 离线下载 API（GET+POST tasks）
│   └── operation_log.py       # 新增：操作记录 CRUD
├── core/
│   ├── exceptions.py          # 已有
│   ├── schemas.py             # 已有 + 新增 SyncJobSchema / OperationLogSchema
│   ├── logger.py              # 已有（需扩展为结构化 JSON）
│   └── config.py              # 已有
└── mcp/
    └── server.py              # 已有（28 个工具）

tests/
├── unit/
│   ├── test_sync_manager.py
│   └── test_rclone_adapter.py
└── integration/
    └── test_cloud_operations.py
```

**Structure Decision**: 单项目 Python 服务（backend/src + tests），MCP server 同进程复用 HTTP API 路由。

## Phase 0: Research Findings

> 结论来自背景调研 + 现有代码分析

### 已有实现（无需修改）

| 组件 | 现状 |
|------|------|
| `CloudDriveService.list_files` | ✅ 已实现（rclone lsjson） |
| `CloudDriveService.list_detail` | ✅ 已实现（rclone lsjson --full） |
| `CloudDriveService.delete` | ✅ 已实现（rclone purge） |
| `CloudDriveService.download` | ✅ 已实现（rclone copyto） |
| `CloudDriveService.move` | ⚠️ 已有，需补充 auto-mkdir 逻辑（FR-003） |
| MCP Server (28 tools) | ✅ 已有（stateless_http=True） |

> ⚠️ 注意：src/ 下目前仅有 __pycache__（编译缓存），源代码未提交至 Git。实现阶段需重新创建这些文件。

### 技术决策

| 决策 | 方案 | 理由 |
|------|------|------|
| 同步任务队列 | 内存 dict + Background thread | 轻量，个人工具够用，无需 Celery/Redis |
| 进度追踪 | 解析 `rclone copy --progress` stdout | rclone 原生支持，格式稳定 |
| 任务取消 | `subprocess.Popen` + `proc.terminate()`/`proc.kill()` | 最可靠的中断方式 |
| 日志格式 | Python logging + custom JSONFormatter | 标准库，无需引入 loguru |
| 操作记录 | MySQL 表（同步写入，≤500ms） | SC-008 要求 |
| PikPak 离线下载 | PikPak 官方 API（POST /v1/download） | rclone 不支持，需 API |
| 移动自动创建目录 | `rclone mkdir` + `rclone moveto` | rclone moveto 不会自动创建父目录 |
| 备份移动冲突 | 跳过 + 告警（logged as warning） | 第二个任务不失败，status 仍 completed |

### rclone moveto 不自动创建目标目录

**问题**：`rclone moveto src dst` 若 `dst` 的父目录不存在，则报错：
```
Failed to moveto: directory not found
```

**解决**：moveto 前先执行 `rclone mkdir -p dst_parent`：
```bash
rclone mkdir pikpak:/backup/documents
rclone moveto pikpak:/docs/a.txt pikpak:/backup/documents/a.txt
```

### rclone copy --progress 输出格式（经验值）

```
Transferred:    1.345 GiB / 10.382 GiB, 13%, 11.161 MiB/s, ETA 13m41s
```

**解析正则**：
```python
import re
PROGRESS_RE = re.compile(
    r"Transferred:\s+([\d.]+ [KMGT]iB) / ([\d.]+ [KMGT]iB),\s+(\d+)%"
)
```

### PikPak API（待调研确认）

> bg_84cd9f08 背景调研进行中，以下为初步方案

**API Base**: `https://api.mypikpak.com`

**认证**：`POST /v1/auth/signin` — username + password → access_token

**离线下载**：`POST /v1/download` — access_token + urls → task_id

**限速处理**（来自 Clarification）：指数退避 1s→2s→4s…，上限 60s 后任务标记 failed

---

## Phase 1: Design Artifacts

> 详见子文件

| 文件 | 内容 |
|------|------|
| `data-model.md` | 6 个实体定义、关系、SQL DDL、SyncJob 状态机 |
| `contracts/sync-job-api.md` | 9 个 HTTP 端点契约（list/detail/move/delete/sync/sync-status/cancel/offline-download/logs）|
| `quickstart.md` | 快速开始指南、操作示例、MCP 调用示例 |
