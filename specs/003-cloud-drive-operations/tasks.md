---

description: "Task list for cloud drive file operations feature implementation"
---

# Tasks: 云盘通用文件操作

**Input**: Design documents from `specs/003-cloud-drive-operations/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/sync-job-api.md
**Tests**: 不要求（spec.md 中各 story 有 Independent Test 描述，但未要求 TDD 流程）

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 归属的用户故事，如 [US1]、[US2]（Phase 3+ 必须标注）
- 描述中包含具体文件路径

## Phase 1: Setup（项目初始化）

**Purpose**: 项目基础结构和依赖管理

- [X] T001 [P] 创建 `src/adapters/`、`src/services/`、`src/api/`、`src/core/`、`src/db/` 目录结构
- [X] T002 [P] 创建 `tests/unit/`、`tests/integration/`、`tests/contract/` 目录结构
- [X] T003 [P] 创建 `src/__init__.py` 及各子包 `__init__.py`
- [X] T004 [P] 创建/更新 `pyproject.toml`（FastAPI, uvicorn, pydantic>=2.0, pymysql, cryptography, pytest, httpx, python-multipart）
- [X] T005 [P] 创建 `.gitignore`（Python: __pycache__/, *.pyc, .venv/, *.egg-info/, .env, build/, dist/, *.spec）
- [X] T006 创建 `log/` 目录（用于 JSON 结构化日志输出）

---

## Phase 2: Foundational（核心基础设施）

**Purpose**: 所有用户故事的前置依赖，必须先完成

**⚠️ CRITICAL**: Phase 2 完成前不得开始任何用户故事实现

- [X] T007 [P] 实现 `src/core/logger.py` — 结构化 JSON 日志Formatter（timestamp/level/logger/message/extra），使用 Python logging 标准库
- [X] T008 [P] 实现 `src/core/config.py` — 加载 `config/config_*.yaml`，解析 encryption.salt 为 Fernet key
- [X] T009 [P] 创建 `src/db/database.py` — MySQL 连接管理（PyMySQL），配置来自 config
- [X] T010 [P] 实现 `src/core/schemas.py` — 补充 `SyncJobSchema`、`OperationLogSchema`、`CloudDriveListRequest`、`CloudDriveDetailRequest` 等 Pydantic 模型（参照 data-model.md）
- [X] T011 [P] 创建 `src/core/exceptions.py` — 补充 `SyncError`、`JobNotFoundError`、`InvalidJobStateError`、`OperationQueueFullError`（参照 contracts/sync-job-api.md 错误码）
- [X] T012 实现 `src/db/init_db.py` — 执行 data-model.md 中的 CREATE TABLE SQL（cloud_drive_configs、sync_jobs、offline_download_tasks、operation_logs）
- [X] T013 [P] 实现 `src/core/operation_logger.py` — OperationLog 写入逻辑（同步写入，≤500ms，参照 SC-008）
- [X] T014 实现 `src/adapters/rclone_adapter.py` — 补充 `mkdir` 方法（自动创建目标目录）和 `moveto` 前先 `mkdir` 的调用逻辑（FR-003）

**Checkpoint**: 基础就绪，可以开始用户故事实现

---

## Phase 3: User Story 1 — 查看云盘目录内容 (Priority: P1) 🎯 MVP

**Goal**: 用户能列出云盘指定目录的文件列表，路径为空时列出根目录

**Independent Test**: POST `/cloud/{drive_type}/list` 返回文件数组，验证根目录和子目录列表正确

### Implementation

- [ ] T015 [P] [US1] 实现 `CloudDriveListRequest` schema（`path: str = "/"`）in `src/core/schemas.py`
- [ ] T016 [P] [US1] 在 `src/services/base.py` 的 `CloudDriveService.list_files` 中补充空路径默认根目录逻辑
- [ ] T017 [US1] 在 `src/api/cloud.py` 添加 `POST /cloud/{drive_type}/list` 端点实现，调用 `CloudDriveService.list_files`
- [ ] T018 [US1] 添加操作日志记录（operation=`list`）到 `src/core/operation_logger.py`
- [ ] T019 [US1] 补充 rclone `lsjson` 命令解析（`RcloneAdapter.list_remote` 返回 `List[FileInfoSchema]`）
- [ ] T020 [US1] 添加输入校验：路径格式校验（不能包含非法字符）

**Checkpoint**: US1 完成 — 可独立测试

---

## Phase 4: User Story 2 — 查看文件/文件夹详情 (Priority: P1)

**Goal**: 用户能获取文件/文件夹的详细元数据

**Independent Test**: POST `/cloud/{drive_type}/detail` 返回完整 FileInfo 元数据，空路径返回错误

### Implementation

- [ ] T021 [P] [US2] 实现 `CloudDriveDetailRequest` schema（`path: str`，不能为空）in `src/core/schemas.py`
- [ ] T022 [US2] 在 `src/api/cloud.py` 添加 `POST /cloud/{drive_type}/detail` 端点，调用 `CloudDriveService.list_detail`
- [ ] T023 [US2] 添加操作日志记录（operation=`detail`）
- [ ] T024 [US2] 添加空路径校验：path 为空返回 `VALIDATION_ERROR`

**Checkpoint**: US2 完成

---

## Phase 5: User Story 3 — 移动文件或文件夹 (Priority: P1)

**Goal**: 移动文件到目标地址，目标目录不存在时自动创建

**Independent Test**: POST `/cloud/{drive_type}/move` 将文件从 A 移动到 B，验证 B 出现且 A 消失；目标目录不存在时自动创建

### Implementation

- [ ] T025 [P] [US3] 实现 `CloudDriveMoveRequest` schema（`src: str, dst: str`）in `src/core/schemas.py`
- [ ] T026 [US3] 在 `src/adapters/rclone_adapter.py` 实现 `move_with_mkdir(src, dst)` 方法：
  1. 解析 `dst` 的父目录
  2. `rclone mkdir remote:parent_dir`
  3. `rclone moveto remote:src remote:d st`
- [ ] T027 [US3] 在 `src/services/base.py` 实现 `CloudDriveService.move`，调用 `move_with_mkdir`
- [ ] T028 [US3] 在 `src/api/cloud.py` 添加 `POST /cloud/{drive_type}/move` 端点
- [ ] T029 [US3] 添加操作日志记录（operation=`move`）
- [ ] T030 [US3] 添加输入校验：src 为空返回 `VALIDATION_ERROR`

**Checkpoint**: US3 完成

---

## Phase 6: User Story 4 — 删除文件或文件夹 (Priority: P2)

**Goal**: 删除指定路径文件/目录，根目录和空路径禁止删除

**Independent Test**: POST `/cloud/{drive_type}/delete` 删除文件，验证文件不再出现在目录列表

### Implementation

- [ ] T031 [P] [US4] 实现 `CloudDriveDeleteRequest` schema（`path: str`）in `src/core/schemas.py`
- [ ] T032 [US4] 在 `src/api/cloud.py` 添加 `POST /cloud/{drive_type}/delete` 端点
- [ ] T033 [US4] 添加输入校验：path 为空或为 `/` 返回 `VALIDATION_ERROR`
- [ ] T034 [US4] 添加操作日志记录（operation=`delete`）

**Checkpoint**: US4 完成

---

## Phase 7: User Story 5 — 云下载（仅 PikPak）(Priority: P2)

**Goal**: 提交离线下载任务，调用 PikPak API，目录为空时默认 `/My Pack`

**Independent Test**: POST `/cloud/pikpak/offline-download` 返回 task_id，任务在 PikPak 可见

### Implementation

- [ ] T035 [P] [US5] 实现 `OfflineDownloadRequest` schema（`urls: List[str], folder: str = "/My Pack"`）in `src/core/schemas.py`
- [ ] T036 [US5] 调研 PikPak API 认证和下载接口（使用 `/context7-mcp` 查询 PikPak API 文档）
- [ ] T037 [US5] 实现 `src/services/pikpak_api.py` — PikPak HTTP API 封装：
  - `signin(username, password)` → access_token
  - `create_download_task(access_token, urls, folder)` → task_id
  - 限速处理：指数退避 1s→2s→4s…，上限 60s
- [ ] T038 [US5] 在 `src/services/pikpak.py` 实现 `cloud_download_add`（调用 `pikpak_api.py`）
- [ ] T039 [US5] 在 `src/api/pikpak_offline.py` 添加 `POST /cloud/pikpak/offline-download` 端点
- [ ] T040 [US5] 非 PikPak 云盘调用时返回 `UNSUPPORTED_DRIVE_TYPE`
- [ ] T041 [US5] 添加操作日志记录（operation=`offline_download`）

**Checkpoint**: US5 完成（PikPak 离线下载可用）

---

## Phase 8: User Story 6 — 同步文件到本地 (Priority: P2)

**Goal**: 异步下载云盘文件到本地，下载成功后移动原文件到云盘 `/backup/`，支持进度查询和取消

**Independent Test**: POST `/cloud/sync` 返回 job_id → GET `/cloud/sync/{job_id}/status` 查询进度 → 文件出现在本地 + 云盘原文件移动到 `/backup/`

### Implementation

- [ ] T042 [P] [US6] 实现 `src/services/sync_manager.py` — `SyncJobManager` 类：
  - `dict[job_id, SyncJob]` 内存存储
  - `submit(drive_type, source_path, local_path)` → job_id（202 Accepted）
  - `get_status(job_id)` → SyncJob
  - `cancel(job_id)` → 设置 cancel_event
  - `MAX_CONCURRENT = 5`，超出返回 `OPERATION_QUEUE_FULL`
- [ ] T043 [P] [US6] 实现 `SyncJob` dataclass（status/phase/progress_bytes/total_bytes/retry_count/cancel_event）
- [ ] T044 [US6] 实现下载线程 `src/services/sync_downloader.py`：
  - `rclone copy --progress remote:source local_dir`
  - 解析 `Transferred: X / Y, Z%` 进度行
  - `threading.Event` 检测取消信号
  - 下载完成后 phase=`moving-to-backup`，执行 `rclone moveto` 移动到 `/backup/`
  - 重试逻辑：最多 10 次，retry_count++
- [ ] T045 [P] [US6] 实现 backup 移动冲突处理：moveto 目标已存在时跳过并记录 warning log（不失败）
- [ ] T046 [US6] 在 `src/api/sync.py` 添加：
  - `POST /cloud/sync` — 创建同步任务，返回 job_id
  - `GET /cloud/sync/{job_id}/status` — 查询进度
  - `POST /cloud/sync/{job_id}/cancel` — 取消任务
- [ ] T047 [US6] 添加操作日志记录（operation=`sync_start`/`sync_cancel`）

**Checkpoint**: US6 完成（异步同步 + 进度 + 取消 + backup 移动）

---

## Phase 9: User Story 6 补充 — 操作记录查询 (Priority: P2)

**Goal**: 管理员查询所有 API 操作记录（分页、过滤）

**Independent Test**: GET `/cloud/admin/operation-logs` 返回分页列表

### Implementation

- [ ] T048 [P] [US6-log] 实现 `src/api/operation_log.py`：
  - `GET /cloud/admin/operation-logs` — 分页查询（page/page_size/operation/drive_type/start_date/end_date）
  - operation 字段：`list`/`detail`/`move`/`delete`/`offline_download`/`sync_start`/`sync_cancel`/`admin_add`/`admin_update`/`admin_delete`

**Checkpoint**: 操作日志查询可用

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: 跨用户故事的完善工作

- [ ] T049 [P] 更新 `src/mcp/server.py` — 添加 `pikpak_sync_to_local`、`pikpak_get_sync_status`、`pikpak_cancel_sync` MCP 工具（参照 contracts/sync-job-api.md 端点）
- [ ] T050 [P] 更新 `src/mcp/server.py` — 添加 `pikpak_offline_download` MCP 工具
- [ ] T051 [P] 验证所有 `src/core/exceptions.py` 错误码与 contracts/sync-job-api.md 错误表一致
- [ ] T052 运行 `quickstart.md` 中的所有 curl 示例，验证端到端流程
- [ ] T053 [P] 更新 `config/config_dev.yaml` 和 `config/config_prod.yaml`（如有新增配置项）
- [ ] T054 清理 `__pycache__`、`*.pyc`，确保 `.gitignore` 生效

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | 依赖 | 说明 |
|-------|------|------|
| Phase 1 (Setup) | 无 | 可立即开始 |
| Phase 2 (Foundational) | Phase 1 完成 | 阻塞所有用户故事 |
| Phase 3-9 (User Stories) | Phase 2 完成 | 可按优先级顺序或并行 |
| Phase 10 (Polish) | Phase 3-9 完成 | 最后执行 |

### User Story Dependencies

| Story | 依赖 | 说明 |
|-------|------|------|
| US1 (list) | Phase 2 | 目录列表是基础操作 |
| US2 (detail) | Phase 2 | 详情是独立操作 |
| US3 (move) | Phase 2, T014（rclone mkdir）| 依赖基础移动能力 |
| US4 (delete) | Phase 2 | 删除是独立操作 |
| US5 (云下载) | Phase 2 | 独立于其他 story |
| US6 (同步) | Phase 2, T042-T047 | 最复杂，依赖 Phase 2 全部 |

### 并行执行机会

- Phase 1 所有 6 个任务 [P] 可并行
- Phase 2 中 T007/T008/T009/T010/T011/T013/T014 可并行
- Phase 3-9 中不同 Story 可由不同 agent 并行实现

---

## Suggested MVP Scope

**MVP = Phase 3 (US1 list) + Phase 4 (US2 detail) + Phase 5 (US3 move)**

优先实现目录浏览 + 移动（自动创建目录）这两个最高频场景，形成可演示的 MVP。

---

## Notes

- 不要求 TDD，测试仅为独立验证手段
- PikPak API 调研（T036）若失败，US5 标记为部分可用（NotImplementedError fallback）
- Phase 2 的 T014（rclone mkdir）是 FR-003 的关键前置
- 并发上限 5 个任务在 T042 SyncJobManager 中强制校验