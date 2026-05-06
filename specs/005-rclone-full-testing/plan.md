# Implementation Plan: Rclone Full Testing

**Branch**: `005-rclone-full-testing` | **Date**: 2026-05-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-rclone-full-testing/spec.md`

## Summary

对 CloudDriveManager 的所有云盘文件操作（list/detail/move/delete/sync/cloud-download）进行全面的测试覆盖验证，同时实现两个遗漏功能：FR-015（`FILE_IN_USE` 占用检查）和 FR-016（CloudDownloadJob 实体 + 30分钟超时 + MySQL 持久化）。

主要技术路径：使用 pytest + unittest.mock 模拟 rclone 子进程，对所有 5 种云盘类型和所有 API 端点进行契约测试；新增 `CloudDownloadJob` 后台任务机制。

## Technical Context

**Language/Version**: Python 3.10
**Primary Dependencies**: FastAPI 0.109+, uvicorn, pydantic v2, pymysql, pytest, httpx, pikpakapi 0.4.0
**Storage**: MySQL (cloud_drive_manager) — tables: sync_jobs, cloud_download_jobs, operation_logs
**Testing**: pytest + unittest.mock (mock rclone subprocess); integration tests require real rclone/config
**Target Platform**: Linux server (development on Windows with WSL)
**Project Type**: REST API + MCP tools web service
**Performance Goals**: 无明确 SLA 目标（聚焦功能正确性）
**Constraints**:
- 所有云盘文件操作必须通过 RcloneAdapter 调用 rclone CLI（FR-001 架构约束）
- rclone binary 必须在 PATH 中且 remotes 已配置
- PikPak API 需要 pikpak.username / pikpak.password 配置
**Scale/Scope**: 单用户本地工具，并发同步任务上限 5 个；测试范围：3 种云盘（PikPak、JianGuoYun、BaiduYun via Alist WebDAV）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 文件 (`.specify/memory/constitution.md`) 为空模板，无实质性约束条款。本计划直接通过 Constitution Check。

## Project Structure

### Documentation (this feature)

```
specs/005-rclone-full-testing/
├── plan.md              # This file
├── research.md           # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/          # Phase 1 output
```

### Source Code (repository root)

```
src/
├── adapters/
│   └── rclone_adapter.py       # 已有：rclone CLI 封装
├── services/
│   ├── base.py                 # 已有：CloudDriveService 抽象层
│   ├── sync_manager.py         # 已有：SyncJobManager
│   └── pikpak.py               # 已有：PikPak 离线下载桥接
├── api/
│   ├── cloud.py                # 已有：FastAPI 路由工厂
│   ├── sync.py                 # 已有：同步任务 API
│   └── pikpak_offline.py       # 已有：PikPak 离线下载 API
├── core/
│   ├── config.py               # 已有：YAML 配置单例
│   ├── schemas.py               # 已有：Pydantic 模型
│   └── exceptions.py            # 已有：错误代码层级
├── db/
│   ├── database.py              # 已有：MySQL 连接池
│   └── init_db.py               # 已有：建表脚本
└── mcp/
    └── server.py                # 已有：FastMCP 服务器

tests/
├── unit/
│   ├── test_rclone_adapter.py   # 已有：rclone 适配器单元测试
│   ├── test_schemas.py          # 已有：schema 测试
│   └── test_exceptions.py       # 已有：异常测试
└── integration/
    └── test_api.py              # 已有：API 路由集成测试
```

**Structure Decision**: 现有项目结构保持不变。本功能主要工作为：(a) 新增单元测试覆盖 FILE_IN_USE 逻辑和 CloudDownloadJob；(b) 扩展集成测试覆盖全部 5 种云盘类型；(c) 新增 `cloud_download_jobs` MySQL 表。

---

## Phase 0: Research

### Research Tasks

**R1: 如何验证 rclone-only 架构约束（FR-001 / FR-002）**

- 目标：建立代码审查级别的架构验证测试，确保 `RcloneAdapter` 是唯一调用 rclone 子进程的模块
- 方法：使用 `ast` 模块或 grep 扫描所有 Python 源文件，验证无其他模块直接调用 `subprocess.run`、`subprocess.Popen` 或云服务商 SDK
- 验收标准：测试运行时报错如果存在非 RcloneAdapter 的 rclone 调用

**R2: 如何全面测试 RcloneAdapter 子进程交互**

- 目标：设计测试策略，覆盖 rclone lsjson / moveto / purge / copy 命令的各种输出格式
- 方法：使用 `unittest.mock.patch("subprocess.run")` 和 `unittest.mock.patch("subprocess.Popen")` 模拟子进程返回，验证参数构造正确性和输出解析逻辑
- 重点：`PROGRESS_RE` 正则表达式覆盖（0 B, 0.000 KiB, 100%, GiB/TiB 单位）

**R3: 如何测试异步任务的 30 分钟超时看门狗机制**

- 目标：验证 CloudDownloadJob 后台任务在超时后正确标记为 FAILED
- 方法：使用快速超时模拟（patch 时间）或直接测试超时判断逻辑
- 关键：服务重启后能从 MySQL `cloud_download_jobs` 表恢复未完成的任务

**R4: 如何测试 FILE_IN_USE 占用检查（FR-015）**

- 目标：验证删除/移动正在被同步任务使用的文件时返回 `FILE_IN_USE` 错误
- 方法：模拟同步任务占用文件状态，检查删除/移动操作是否正确拒绝

**R5: 如何对 5 种云盘类型进行统一的契约测试**

- 目标：确保 PikPak / JianGuoYun / BaiduYun 返回一致的响应 schema
- 方法：参数化测试（pytest parametrize），对每种 drive_type 执行相同操作序列，比较响应结构

---

## Phase 1: Design & Contracts

### Data Model (data-model.md)

**新增 `cloud_download_jobs` 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT AUTO_INCREMENT | 主键 |
| task_id | VARCHAR(128) | PikPak API 返回的任务 ID |
| urls | TEXT | URL 列表（JSON 数组） |
| folder | VARCHAR(512) | 目标文件夹路径 |
| status | ENUM('pending','downloading','completed','failed','timeout') | 任务状态 |
| error_message | TEXT | 错误详情 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| finished_at | DATETIME | 完成/失败时间（可为 NULL） |

**新增错误码**

- `FILE_IN_USE`: 尝试删除/移动正在被同步任务占用的文件（FR-015）

**更新 `sync_jobs` 表**（如有需要确认字段完整性）

---

### Contracts (contracts/)

**API 契约覆盖**：

- `cloud-drive-list-api.md` — POST /cloud/{drive_type}/list 契约（已有）
- `cloud-drive-detail-api.md` — POST /cloud/{drive_type}/detail 契约（已有）
- `cloud-drive-move-api.md` — POST /cloud/{drive_type}/move 契约（已有）
- `cloud-drive-delete-api.md` — POST /cloud/{drive_type}/delete 契约（已有）
- `sync-job-api.md` — 同步任务管理契约（已有）
- `cloud-download-api.md` — **新增**：POST /cloud/pikpak/cloud-download 契约（FR-011, FR-016）
- 测试范围更新：PikPak、JianGuoYun、BaiduYun（Alist WebDAV）三种云盘

---

### Quickstart (quickstart.md)

- 如何运行全套测试：`pytest tests/ -v`
- 如何运行单元测试：`pytest tests/unit/ -v`
- 如何运行集成测试：`pytest tests/integration/ -v`（需要真实 rclone 配置）
- 如何 mock rclone 进行测试：设置 `RCLONE_PATH=echo` 环境变量
- 如何初始化数据库：`python -m src.main init-db`
- 如何运行 API 服务：`python -m src.main`
- 如何运行 MCP 服务：`python -m src.mcp`
