# Tasks: Cloud Drive Manager

**Input**: Design documents from `/specs/001-cloud-drive-manager/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: NOT explicitly requested in spec — no automated test tasks generated. Manual API testing will be used per independent test criteria.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure `src/`, `config/`, `tests/unit/`, `tests/integration/` per implementation plan
- [ ] T002 Create `pyproject.toml` with dependencies: fastapi, uvicorn, pyyaml, cryptography, pytest
- [ ] T003 [P] Create `src/__init__.py`, `src/config/__init__.py`, `src/core/__init__.py`, `src/adapters/__init__.py`, `src/services/__init__.py`, `src/api/__init__.py`
- [ ] T004 [P] Create `config/config_dev.yaml` with all cloud drive config sections and placeholder values per data-model.md
- [ ] T005 [P] Create `config/config_prod.yaml` as production template
- [ ] T006 [P] Create `src/__init__.py` exposing public API exports

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 [P] Implement `src/core/exceptions.py` — CloudDriveError base class and full exception hierarchy per data-model.md (ConfigError, EncryptionError, RCloneError, CloudDriveError with all subclasses)
- [ ] T008 [P] Implement `src/core/logger.py` — Python logging with RotatingFileHandler, 10MB maxBytes, 10 backupCount, 7-day retention cleanup per FR-001
- [ ] T009 [P] Implement `src/core/encryption.py` — Fernet encryption/decryption service, startup decryption of all passwords to memory per FR-002
- [ ] T010 [P] Implement `src/config/config.py` — Config singleton, YAML loading, `config_{mode}.yaml` per FR-004/FR-005/FR-006, point-dot key access, env override, throws on missing key
- [ ] T011 [P] Implement `src/api/schemas.py` — Pydantic models: APIResponse, FileInfo, FileListResponseData, SyncRequest, all cloud drive request/response schemas per data-model.md
- [ ] T012 [P] Implement `src/api/health.py` — GET /health endpoint returning `{"code":0,"message":"success","data":{"status":"healthy","version":"1.0.0"}}` per api-contract.md
- [ ] T013 Implement `src/main.py` — FastAPI app instantiation, startup event (load config + decrypt passwords), register routers, return app object per research.md Decision 5

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - 配置与日志基础设施 (Priority: P1) 🎯 MVP

**Goal**: 公共基础设施完成 — Config, Logger, Encryption, Exceptions 可通过单元测试验证；服务可启动并响应健康检查

**Independent Test**: `pytest tests/unit/` 全部通过；`uvicorn src.main:app` 可在 5 秒内启动并响应 `/health`

### Implementation for User Story 1

- [ ] T014 [P] [US1] Write unit tests in `tests/unit/test_config.py` verifying Config.get() behavior: key found returns value, key missing raises ConfigKeyNotFoundError, dot-notation access works
- [ ] T015 [P] [US1] Write unit tests in `tests/unit/test_logger.py` verifying log rotation: file >10MB creates new file, old logs within 7 days retained, logs >7 days cleaned up on write
- [ ] T016 [P] [US1] Write unit tests in `tests/unit/test_encryption.py` verifying encrypt/decrypt roundtrip, invalid salt raises EncryptionSaltInvalidError, decryption failure raises DecryptionFailedError
- [ ] T017 [P] [US1] Write unit tests in `tests/unit/test_exceptions.py` verifying all exception classes have error_code and message attributes
- [ ] T018 [US1] Run all unit tests, fix any failures before proceeding
- [ ] T019 [US1] Start service with `uvicorn src.main:app --port 8000`, verify `/health` returns 200 within 5 seconds

**Checkpoint**: US1 complete — Config, Logger, Encryption, Exceptions all verified, service starts and health-check passes

---

## Phase 4: User Story 2 - Rclone 云盘操作封装 (Priority: P2)

**Goal**: RcloneAdapter 实现，支持多云盘类型；CloudDriveService 基类实现；所有云盘通用 API 端点完成

**Independent Test**: 调用 `/cloud/pikpak/list?path=/` 返回正确文件列表；调用 `/cloud/pikpak/detail?path=X` 返回正确文件详情；下载、删除、同步操作正确

### Implementation for User Story 2

- [ ] T020 [P] [US2] Implement `src/adapters/rclone_adapter.py` — RcloneAdapter class with list_directory, get_file_details, download_file, delete_item, move_item, create_directory, cloud_download_add methods; subprocess.run() calls rclone with --fast-list --transfers=8 --timeout=300s --retries=3; retry on network error per FR-007/FR-008/FR-009/FR-010/FR-011/FR-012/FR-013
- [ ] T021 [P] [US2] Implement `src/services/base.py` — CloudDriveService abstract base class defining interface (list_directory, get_file_details, download_file, delete_item, move_item, sync_to_local); receives RcloneAdapter instance per plan.md structure
- [ ] T022 [US2] Implement `src/api/cloud.py` — FastAPI router with GET /cloud/{drive_type}/list, GET /cloud/{drive_type}/detail, POST /cloud/{drive_type}/download, POST /cloud/{drive_type}/delete, POST /cloud/{drive_type}/move, POST /cloud/sync per api-contract.md
- [ ] T023 [US2] Register cloud router in `src/main.py`
- [ ] T024 [US2] Manually test: start service, call `/cloud/pikpak/list?path=/`, verify returns file list in APIResponse format

**Checkpoint**: US2 complete — RcloneAdapter working, cloud API endpoints functional, list/detail/download/delete/move/sync all return correct responses

---

## Phase 5: User Story 3 - 多云盘管理接口 (Priority: P3)

**Goal**: 五种云盘（PikPak、坚果云、百度云、阿里云、夸克云）全部接入；各自独立实现类；PikPak 离线下载扩展 API 完成

**Independent Test**: 调用各云盘 `/cloud/{type}/list` 均返回正确响应；调用 `/cloud/pikpak/offline-download` 添加离线任务成功

### Implementation for User Story 3

- [ ] T025 [P] [US3] Implement `src/services/pikpak.py` — PikPakCloudDrive extending CloudDriveService; inherits base operations; adds cloud_download_add for offline-download per api-contract.md
- [ ] T026 [P] [US3] Implement `src/services/jianguoyun.py` — JianguoyunCloudDrive extending CloudDriveService
- [ ] T027 [P] [US3] Implement `src/services/baidu.py` — BaiduCloudDrive extending CloudDriveService
- [ ] T028 [P] [US3] Implement `src/services/aliyun.py` — AliyunCloudDrive extending CloudDriveService
- [ ] T029 [P] [US3] Implement `src/services/quark.py` — QuarkCloudDrive extending CloudDriveService
- [ ] T030 [US3] Wire cloud drive service factory/registry in `src/api/cloud.py` — routes `{drive_type}` path param to correct service class (pikpak→PikPakCloudDrive, etc.); raises CLOUD_DRIVE_NOT_CONFIGURED if drive_type not configured
- [ ] T031 [US3] Implement POST `/cloud/pikpak/offline-download` in `src/api/cloud.py` per api-contract.md
- [ ] T032 [US3] Manually test all five cloud drive endpoints with a configured rclone remote

**Checkpoint**: US3 complete — all five cloud drives functional with consistent interface, PikPak offline-download available

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T033 [P] Add global exception handler in `src/main.py` using FastAPI's exception_handler to convert all CloudDriveError subclasses to proper JSON error responses per api-contract.md
- [ ] T034 [P] Verify API response format consistency: all endpoints return `{code, message, data}` structure
- [ ] T035 Verify all edge cases from spec.md are handled: root delete forbidden, rclone not found fast-fail, log dir unwritable fallback, encryption salt invalid errors
- [ ] T036 Create `tests/integration/test_api.py` with basic smoke tests: health check, list returns 200, missing key returns error response
- [ ] T037 Run through quickstart.md validation: can start service, call health, call list, verify logs appear in log/ directory with correct rotation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 → US2 → US3 can proceed sequentially (recommended for single developer)
  - Or US2 and US3 can proceed in parallel after US1 completes (if two developers)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **US2 (P2)**: Can start after Foundational (Phase 2) — No dependencies on US1, but US2's API endpoints will be empty until US1 schemas/exceptions are ready
- **US3 (P3)**: Can start after Foundational (Phase 2) — Depends on US2's base CloudDriveService and RcloneAdapter existing

### Within Each User Story

- Models/schemas before services
- Services before API endpoints
- Core implementation before edge case handling

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T001-T006)
- All Foundational tasks marked [P] can run in parallel (T007-T012)
- Five cloud drive implementations (T025-T029) can all run in parallel

---

## Parallel Example: After Foundational Complete

```bash
# One developer does US1:
T014 → T015 → T016 → T017 → T018 → T019

# Another developer does US2 in parallel:
T020 → T021 → T022 → T023 → T024

# After US2, third developer does US3:
T025 → T026 → T027 → T028 → T029 → T030 → T031 → T032

# Finally, polish:
T033 → T034 → T035 → T036 → T037
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `pytest tests/unit/` and start service to verify `/health`
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Complete US1 → Test independently → Deploy/Demo (MVP!)
3. Complete US2 → Test independently → Deploy/Demo
4. Complete US3 → Test independently → Deploy/Demo
5. Polish phase → Final validation

---

## Notes

- Tests are NOT generated (not explicitly requested in spec)
- Manual API testing per independent test criteria for each user story
- All cloud drive service implementations (pikpak/jianguoyun/baidu/aliyun/quark) follow same base interface — only differ in config remote_name
- RcloneAdapter is the key shared component — implement carefully with retry logic
- Encryption service startup decryption is a critical startup-time concern — verify all passwords decrypt successfully before server starts accepting requests