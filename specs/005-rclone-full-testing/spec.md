# Feature Specification: Rclone Full Testing

**Feature Branch**: `005-rclone-full-testing`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "1.云盘所有的底层功能全部依赖rclone实现，不需要也不能使用其他方式实现；2.测试全量功能"

## Clarifications

### Session 2026-05-03

- Q: API 认证机制如何选择？ → A: A（依赖 rclone.conf 认证，无额外 API 密钥）
- Q: 离线下载是否需要状态查询？ → A: 云下载触发后立即返回任务创建结果，系统后台跟踪任务完成状态，超过30分钟未完成视为超时失败
- Q: 并发操作冲突如何处理？ → A: A（拒绝操作，返回 FILE_IN_USE 错误）
- Q: 是否需要定义 API 性能目标？ → A: C（暂不定义性能目标，聚焦功能正确性）
- Q: 云下载任务是否需要持久化？ → A: B（持久化到 MySQL cloud_download_jobs 表，与 SyncJob 保持一致）

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify Rclone-Only Implementation (Priority: P1)

As a QA engineer, I want to verify that all cloud drive file operations (list/detail/move/delete) exclusively use rclone as the underlying implementation, so that the system remains consistent and maintainable.

**Why this priority**: Ensures architectural constraint is enforced before functional testing begins.

**Independent Test**: Can be verified by code inspection and contract tests that mock rclone subprocess calls.

**Acceptance Scenarios**:

1. **Given** the codebase, **When** I inspect `src/services/base.py`, **Then** all `CloudDriveService` subclasses MUST use `RcloneAdapter` for file operations (list_remote, list_detail, delete, moveto, copy), **And** no direct HTTP/SDK calls exist for core file operations.

2. **Given** the codebase, **When** I inspect `src/adapters/rclone_adapter.py`, **Then** it MUST be the only module that spawns rclone subprocesses, **And** no other adapter/module calls rclone directly.

---

### User Story 2 - Cloud Drive Operations Across All Drive Types (Priority: P1)

As a user, I want to perform file operations (list/detail/move/delete) on all supported cloud drives, so that I can manage files uniformly regardless of the provider.

**Why this priority**: Core functionality that defines the product value proposition.

**Independent Test**: Each operation can be tested independently with a mocked rclone backend.

**Acceptance Scenarios**:

1. **Given** a configured cloud drive (PikPak/JianGuoYun/BaiduYun), **When** I call `list_files("/")`, **Then** I receive a list of `FileInfoSchema` objects with name, path, size, is_dir, and modified fields.

2. **Given** a configured cloud drive, **When** I call `list_detail("/path/to/file")`, **Then** I receive full metadata including hash and mime_type.

3. **Given** a configured cloud drive with existing files, **When** I call `move(src, dst)`, **Then** the file is moved to the destination, **And** the destination parent directory is auto-created if missing.

4. **Given** a configured cloud drive with existing files, **When** I call `delete(path)`, **Then** the file or directory is removed, **And** root "/" deletion is rejected.

5. **Given** all five drive types, **When** I call the same operation on each, **Then** all produce consistent response schemas regardless of provider.

---

### User Story 3 - Async Sync Job Management (Priority: P2)

As a user, I want to submit, monitor, and cancel file sync jobs, so that I can download cloud files to local storage with progress tracking and cancellation support.

**Why this priority**: Core sync use case with background job lifecycle management.

**Independent Test**: Sync manager can be tested with mocked drive service and in-memory job tracking.

**Acceptance Scenarios**:

1. **Given** the sync queue has capacity (< 5 concurrent jobs), **When** I submit a sync job, **Then** I receive a job_id immediately, **And** the job enters PENDING state.

2. **Given** a running sync job, **When** I query its status via `get_status(job_id)`, **Then** I receive current progress_bytes, total_bytes, and progress_percent.

3. **Given** a pending or running job, **When** I call `cancel(job_id)`, **Then** the job enters CANCELLED state, **And** rclone subprocess is terminated.

4. **Given** the sync queue is full (5 running jobs), **When** I submit a new job, **Then** I receive an `OPERATION_QUEUE_FULL` error.

5. **Given** a completed job, **When** I call `cancel(job_id)`, **Then** I receive an `INVALID_JOB_STATE` error.

---

### User Story 4 - PikPak Cloud Download (Priority: P2)

As a PikPak user, I want to trigger cloud download tasks via HTTP/magnet URLs, so that I can add files to my PikPak cloud drive without waiting for local upload.

**Why this priority**: Differentiating feature for PikPak users.

**Independent Test**: Can be tested with mocked PikPak API client.

**Acceptance Scenarios**:

1. **Given** a valid PikPak account, **When** I call `cloud_download_add(urls=["http://example.com/file.zip"], folder="/My Pack")`, **Then** I immediately receive a task_id string.

2. **Given** a cloud download task was created, **When** the task is still in progress after 30 minutes, **Then** the system MUST mark the task as `FAILED` with an `OfflineDownloadTimeoutError` error.

3. **Given** the PikPak API is rate-limited, **When** I submit a cloud download, **Then** the client retries with exponential backoff (1s, 2s, 4s, ... up to 60s), **And** raises `OfflineDownloadTimeoutError` after max retries.

---

### User Story 5 - MCP Tool Interface (Priority: P3)

As a Claude Code agent, I want to access cloud drive operations via MCP tools, so that I can integrate file management into autonomous workflows.

**Why this priority**: Enables AI agent integration.

**Independent Test**: MCP server can be tested by connecting a mock MCP client.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** I call `pikpak_list_files(path="/")`, **Then** I receive a dict with `path` and `files` keys.

2. **Given** the MCP server, **When** I call `pikpak_offline_download(urls=[...], folder="...")`, **Then** I receive a dict with `task_id`, `urls_count`, and `destination_folder`.

---

### Edge Cases

- **Empty directory listing**: System returns empty list `[]`, not null or error
- **Non-existent path**: `list_detail` raises `FILE_NOT_FOUND` error with appropriate code
- **Move to existing path**: `moveto` overwrites existing file silently (rclone default behavior)
- **Delete root directory**: `delete("/")` raises `VALIDATION_ERROR`, cannot delete root
- **Invalid drive type**: API returns `UNSUPPORTED_DRIVE_TYPE` with supported drive list
- **Rclone binary missing**: `RCLONE_NOT_FOUND` error with clear message
- **Rclone command timeout**: `RCLONE_TIMEOUT` error after configured timeout (default 300s)
- **Sync job not found**: `JOB_NOT_FOUND` error when querying/cancelling unknown job_id
- **Zero-byte progress**: `copy_with_progress` handles `0.000 KiB` progress lines correctly
- **Cloud download timeout**: Cloud download tasks exceeding 30 minutes without completion are automatically marked as FAILED with `OfflineDownloadTimeoutError`
- **Cloud download rate limit**: PikPak API rate limiting triggers exponential backoff retry (1s → 2s → 4s → ... → 60s)
- **File in use**: When attempting to delete or move a file that is currently being synced, system returns `FILE_IN_USE` error; user must cancel the sync job first

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All cloud drive file operations (list/detail/move/delete/copy) MUST use `RcloneAdapter` and its underlying rclone CLI subprocess — no direct HTTP calls to cloud provider APIs for file operations.
- **FR-002**: System MUST support three cloud drive types: PikPak, JianGuoYun, and BaiduYun (via Alist WebDAV), via the same `CloudDriveService` interface.
- **FR-003**: The `list_files` operation MUST return lightweight file listings with name, path, size, is_dir, and modified time.
- **FR-004**: The `list_detail` operation MUST return full metadata including hash and mime_type.
- **FR-005**: The `move` operation MUST automatically create destination parent directories if they do not exist.
- **FR-006**: The `delete` operation MUST reject deletion of the root directory ("/").
- **FR-007**: System MUST support background sync jobs with a maximum of 5 concurrent jobs.
- **FR-008**: Sync jobs MUST support progress tracking (bytes done, total bytes, percent) and cancellation via threading.Event.
- **FR-009**: Sync job status MUST be queryable by job_id and return current phase, progress, and state.
- **FR-010**: System MUST persist sync job state to MySQL `sync_jobs` table for durability.
- **FR-011**: PikPak cloud download (`cloud_download_add`) MUST immediately return a task_id after triggering, then track task completion state in the background; if a task remains incomplete for more than 30 minutes, it MUST be marked as `FAILED` with an `OfflineDownloadTimeoutError` error.
- **FR-012**: All API endpoints MUST return consistent `APIResponse` format with code, message, and data fields.
- **FR-013**: All operations MUST be logged to the `operation_logs` table with operation type, result, drive_type, path, and timestamp.
- **FR-014**: MCP server MUST expose the same cloud drive operations as the HTTP API.
- **FR-015**: When attempting to delete or move a file that is currently being synced, system MUST return a `FILE_IN_USE` error; the file cannot be modified until the sync job completes or is cancelled.
- **FR-016**: Cloud download job state MUST be persisted to MySQL `cloud_download_jobs` table for durability; service restart MUST NOT lose active job tracking.

### Key Entities

- **CloudDriveService**: Abstract service layer defining file operation interface. Implementations: PikPakCloudDrive, JianguoyunCloudDrive, BaiduCloudDrive (Alist WebDAV).
- **RcloneAdapter**: Thread-safe wrapper around rclone CLI subprocess. Commands: lsjson, purge, moveto, mkdir, copyto, copy (with --progress).
- **SyncJob**: In-memory job representation with state machine (PENDING → RUNNING → COMPLETED/FAILED/CANCELLED).
- **CloudDownloadJob**: Background job tracking PikPak cloud download tasks with state (PENDING → DOWNLOADING → COMPLETED/FAILED/TIMEOUT). Includes 30-minute timeout watchdog.
- **PikPakClient**: Async HTTP API client using pikpakapi with rate limiting and retry logic.
- **Database**: MySQL connection pool managing sync_jobs, cloud_download_jobs, and operation_logs tables.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three cloud drive types (PikPak, JianGuoYun, BaiduYun) produce identical response schemas for list/detail/move/delete operations.
- **SC-002**: Code inspection confirms zero direct HTTP/SDK calls to cloud providers in file operation code paths — only `RcloneAdapter` calls rclone subprocess.
- **SC-003**: A full sync job lifecycle (submit → run → complete/cancel) correctly updates in-memory state and MySQL persistence.
- **SC-004**: Rclone progress parsing correctly handles all rclone output formats: zero bytes (0 B, 0.000 KiB), percentages 0-100, and all size units (B, KiB, MiB, GiB, TiB).
- **SC-005**: MCP tool responses match HTTP API response schemas for equivalent operations.
- **SC-006**: All error codes returned match the `CloudDriveError` hierarchy as defined in `src/core/exceptions.py`.
- **SC-007**: Rate limiting on PikPak cloud download triggers exponential backoff (1s → 2s → 4s → ... → 60s max) and raises `OfflineDownloadTimeoutError` after 5 retries.

## Assumptions

- rclone binary is installed and configured in the system PATH, with remotes (pikpak:, jianguoyun:, baiduyun:) pre-configured in `rclone.conf`. BaiduYun is accessed via Alist WebDAV.
- MySQL database `cloud_drive_manager` is created, with `sync_jobs`, `cloud_download_jobs`, and `operation_logs` tables initialized via `python -m src.main init-db`.
- PikPak offline download credentials (username/password) are configured in `config/config_dev.yaml` under `pikpak.username` and `pikpak.password`.
- All tests use mocked rclone subprocesses to avoid real cloud operations during CI.
- Production deployments target Linux servers; Windows is used for local development only.
- **认证机制**：API 访问依赖 rclone.conf 中配置的云盘认证（无额外 API 密钥层）；适用于本地网络部署的内部工具场景。
- **云下载超时**：PikPak 云下载任务在创建后30分钟内未完成，视为超时失败，由系统自动标记为 `FAILED`。
- **并发控制**：正在被同步任务使用的文件无法被删除或移动，必须先取消同步任务。
- **云下载持久化**：云下载任务状态持久化到 `cloud_download_jobs` 表，支持服务重启后恢复。
