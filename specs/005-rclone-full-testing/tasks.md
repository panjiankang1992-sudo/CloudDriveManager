# Tasks: Rclone Full Testing

**Input**: Design documents from `/specs/005-rclone-full-testing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Existing Project — No Setup Tasks)

The project already has a complete source tree. This phase validates existing test infrastructure and is effectively a no-op checkpoint.

- [x] T001 Verify existing test infrastructure in tests/ runs correctly with `pytest tests/ -v` ✅

---

## Phase 2: Foundational — rclone Architecture Guard (FR-001)

**Purpose**: Establish architectural enforcement that ALL file operations go through RcloneAdapter. This blocks every user story and must complete first.

- [x] T002 [P] Add `CloudDriveFileInUseError` exception class to `src/core/exceptions.py` (FR-015) ✅
- [x] T003 [P] Add `CloudDownloadJobSchema` and `CloudDownloadStatus` enum to `src/core/schemas.py` (FR-016) ✅
- [x] T004 Update `src/db/init_db.py` to include `cloud_download_jobs` table creation SQL ✅
- [x] T005 Write architecture guard test in `tests/unit/test_rclone_only_enforcement.py` that uses `ast` module to verify only `src/adapters/rclone_adapter.py` calls `subprocess.run` or `subprocess.Popen` ✅

---

## Phase 3: User Story 1 — rclone-Only Architecture Verification (Priority: P1) 🎯 MVP

**Goal**: Verify through automated tests that no cloud provider SDK or direct HTTP calls exist in file operation code paths.

**Independent Test**: Run `pytest tests/unit/test_rclone_only_enforcement.py -v` — must PASS with zero violations.

### Tests

- [x] T006 [P] [US1] Write AST-based rclone-only enforcement test in `tests/unit/test_rclone_only_enforcement.py` ✅ (same as T005)

---

## Phase 4: User Story 2 — Cloud Drive Operations + 3-Type Contract Tests (Priority: P1)

**Goal**: Ensure list/detail/move/delete work identically across PikPak, JianGuoYun, and BaiduYun; expand existing tests.

**Independent Test**: `pytest tests/unit/test_rclone_adapter.py tests/unit/test_schemas.py -v` with mocked subprocess.

### Implementation

- [x] T007 [P] [US2] Add BaiduYun type to `DriveType` enum in `src/core/schemas.py` (FR-002) ✅
- [x] T008 [P] [US2] Register `baiduyun` in `_DRIVE_SERVICE_MAP` in `src/services/base.py` ✅
- [x] T009 [P] [US2] Add BaiduYun to `SUPPORTED_DRIVES` in `src/api/cloud.py` ✅
- [x] T010 [P] [US2] Write parameterized contract tests for 3 drive types (pikpak, jianguoyun, baiduyun) in `tests/integration/test_cloud_drive_contracts.py` ✅
- [x] T011 [US2] Implement `CloudDriveFileInUseError` check in `CloudDriveService.delete()` and `.move()` against `SyncJobManager` active jobs ✅

---

## Phase 5: User Story 3 — Sync Job Management + FILE_IN_USE (Priority: P2)

**Goal**: Complete sync job lifecycle (submit → track → cancel) with FILE_IN_USE guard for active file protection.

**Independent Test**: `pytest tests/unit/test_sync_manager.py tests/unit/test_cloud_drive_file_in_use.py -v`

### Implementation

- [x] T012 [P] [US3] Add `FILE_IN_USE` to `CloudDriveError` hierarchy in `src/core/exceptions.py` ✅ (done in T002)
- [x] T013 [P] [US3] Implement file-in-use guard in `CloudDriveService.delete()` and `.move()` — check `SyncJobManager._jobs` for active (PENDING/RUNNING) jobs targeting the same path ✅ (done in T011)
- [x] T014 [P] [US3] Write unit tests for FILE_IN_USE logic in `tests/unit/test_cloud_drive_file_in_use.py` ✅

---

## Phase 6: User Story 4 — PikPak Cloud Download + 30-Min Timeout (Priority: P2)

**Goal**: Implement `cloud_download_add` with background watchdog that marks tasks TIMEOUT after 30 minutes and persists to `cloud_download_jobs` table.

**Independent Test**: `pytest tests/unit/test_cloud_download.py tests/integration/test_pikpak_offline.py -v`

### Implementation

- [x] T015 [P] [US4] Create `CloudDownloadJobManager` in `src/services/cloud_download_manager.py` with watchdog thread and 30-minute timeout ✅
- [x] T016 [P] [US4] Add `cloud_download_jobs` table operations to `src/db/database.py` ✅
- [x] T017 [P] [US4] Implement `CloudDownloadJob` dataclass with state machine (PENDING → DOWNLOADING → COMPLETED/FAILED/TIMEOUT) ✅
- [x] T018 [US4] Wire `cloud_download_add` to `PikPakCloudDrive` in `src/services/base.py` ✅
- [x] T019 [US4] Write CloudDownloadJob unit tests in `tests/unit/test_cloud_download.py` ✅

---

## Phase 7: User Story 5 — MCP Tool Contract Verification (Priority: P3)

**Goal**: Verify MCP tools produce identical response schemas to HTTP API endpoints.

**Independent Test**: `pytest tests/integration/test_mcp_tools.py -v`

### Implementation

- [x] T020 [P] [US5] Write MCP tool contract tests in `tests/integration/test_mcp_tools.py` verifying `pikpak_list_files`, `pikpak_offline_download` response schema ✅

---

## Phase 8: Integration & Polish

**Purpose**: End-to-end validation, edge case coverage, and quickstart validation.

- [x] T021 [P] Expand `tests/integration/test_api.py` to cover all 3 drive types and new error codes ✅
- [x] T022 [P] Add edge case tests in `tests/unit/test_rclone_adapter.py`: zero-byte progress, 100% progress, KiB/MiB/GiB/TiB units ✅ (already covered by existing tests)
- [x] T023 Run full test suite: `pytest tests/ -v` — all tests must pass ✅ (144 tests passing)
- [x] T024 Validate quickstart.md instructions work: `pytest tests/unit/ -v` with `RCLONE_PATH=echo` ✅ (83 unit tests pass)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: No external dependencies — T002/T003/T004/T005 can proceed immediately
- **Phase 3 (US1)**: Depends on T005 (architecture guard test exists) — blocks nothing else, starts immediately after T005
- **Phase 4 (US2)**: Depends on T007/T008/T009 (drive type wiring) — can start after T002
- **Phase 5 (US3)**: Depends on T012 (FILE_IN_USE exception) — can start after T002
- **Phase 6 (US4)**: Depends on T015/T016/T017 (cloud download manager) — can start after T002/T003/T004
- **Phase 7 (US5)**: Depends on MCP server code existing — can start after Phase 4
- **Phase 8 (Polish)**: Depends on all user stories complete

### Within-Phase Parallelism

- T002, T003, T004 can run in parallel (different files)
- T006, T007, T008, T009 can run in parallel
- T012, T013, T014 can run in parallel
- T015, T016, T017 can run in parallel
- T020 and T022 can run in parallel
- T021 and T023 can run in parallel

### Suggested Parallel Execution

```bash
# Phase 2 — all 4 tasks in parallel:
T002: CloudDriveFileInUseError in src/core/exceptions.py
T003: CloudDownloadJobSchema in src/core/schemas.py
T004: cloud_download_jobs table in src/db/init_db.py
T005: Architecture guard test in tests/unit/test_rclone_only_enforcement.py

# Phase 4 — US2 tasks parallel after T002:
T007: BaiduYun type in DriveType enum
T008: baiduyun in _DRIVE_SERVICE_MAP
T009: BaiduYun in SUPPORTED_DRIVES

# Phase 5 — US3 tasks parallel after T012:
T013: FILE_IN_USE guard in delete/move
T014: FILE_IN_USE unit tests
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 → Phase 2 (T005) → Phase 3 (US1)
2. **STOP and VALIDATE**: `pytest tests/unit/test_rclone_only_enforcement.py -v` passes
3. Deploy/demo if architecture is the only concern

### Full Feature Delivery

1. Phase 1 → Phase 2 (T002–T005) → all user stories (Phase 3–7) in parallel where possible
2. Phase 8 integration + polish
3. Full `pytest tests/ -v` passes

### Independent Testability per Story

- **US1**: Run `pytest tests/unit/test_rclone_only_enforcement.py -v` — code inspection test, no server needed
- **US2**: Run `pytest tests/integration/test_cloud_drive_contracts.py -v` — mocked rclone, no real cloud
- **US3**: Run `pytest tests/unit/test_sync_manager.py tests/unit/test_cloud_drive_file_in_use.py -v`
- **US4**: Run `pytest tests/unit/test_cloud_download.py -v` — mocked PikPakAPI
- **US5**: Run `pytest tests/integration/test_mcp_tools.py -v` — MCP server required
