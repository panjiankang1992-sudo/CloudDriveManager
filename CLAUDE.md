# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Branch Strategy

**所有改动最终必须合入 `master` 分支。** 开发应在功能分支进行，完成后合并到 master，合入主分支才算任务执行完成。

## Project Overview

CloudDriveManager is a universal cloud drive file manager providing REST API and MCP tools for file operations (list/detail/move/delete/sync/cloud-download) across multiple cloud drives. Currently supports PikPak, JianGuoYun, and BaiduYun (via Alist WebDAV).

**Active Feature**: [specs/005-rclone-full-testing/plan.md](specs/005-rclone-full-testing/plan.md) — 全量功能测试覆盖 + CloudDownloadJob + FILE_IN_USE

## Commands

```bash
# Run the HTTP API server (port 29312)
python -m src.main

# Run with production config
python -m src.main --prod

# Initialize database tables
python -m src.main init-db

# Run the MCP server (port 29313)
python -m src.mcp

# Run tests
pytest

# Run a single test file
pytest tests/unit/test_rclone_adapter.py

# Run with verbose output
pytest -v

# Type check
pyright
```

## Architecture

```
src/
├── app.py              # FastAPI factory (port 29312)
├── main.py             # CLI entry point (argparse)
├── mcp/
│   ├── server.py       # FastMCP server (port 29313)
│   └── __main__.py     # MCP entry point
├── api/
│   └── cloud.py        # FastAPI router factory (create_cloud_router)
├── services/
│   ├── base.py         # CloudDriveService ABC + concrete drive implementations
│   ├── sync_manager.py # Async sync job manager (ThreadPoolExecutor, max 5)
│   └── pikpak.py       # PikPak-specific async bridge
├── adapters/
│   └── rclone_adapter.py  # rclone CLI wrapper
├── core/
│   ├── config.py       # YAML config singleton (Config.get())
│   ├── schemas.py      # Pydantic models (request/response)
│   ├── exceptions.py   # CloudDriveError hierarchy
│   └── logger.py       # JSON structured logging
└── db/
    ├── database.py     # MySQL connection singleton
    └── init_db.py       # Table creation
```

**Data flow**: HTTP/MCP request → API router → Service layer → RcloneAdapter → rclone CLI
**Offline download**: PikPakClient (httpx-based) → PikPak HTTP API

## Key Design Patterns

### Service factory pattern (`services/base.py`)
`get_drive_service(drive_type)` creates the appropriate `CloudDriveService` subclass. Add new drives by:
1. Create a concrete class inheriting from `_RcloneCloudDrive` or `CloudDriveService`
2. Register in `_DRIVE_SERVICE_MAP`

### Adapter pattern (`adapters/rclone_adapter.py`)
`RcloneAdapter` wraps the rclone CLI subprocess. It is thread-safe for concurrent use. Progress parsing uses a regex on `rclone copy --progress` output.

### Config-driven singleton (`core/config.py`)
`Config.get()` loads `config/config_{ENV}.yaml` (ENV from `CONFIG_ENV` env var, default `dev`). All settings are accessed as typed properties.

### Sync job architecture (`services/sync_manager.py`)
Uses an in-memory `_SyncJob` dataclass + `ThreadPoolExecutor` (max 5 workers). Jobs are also persisted to MySQL `sync_jobs` table. Cancellation uses `threading.Event`.

## Testing

Tests live in `tests/` with conftest.py setting `CONFIG_ENV=dev` and `RCLONE_PATH=echo` to avoid real I/O during unit tests. Integration tests (marked in `tests/integration/`) may hit real services.

## Tech Stack

- **Language**: Python 3.10
- **HTTP framework**: FastAPI + uvicorn
- **MCP**: FastMCP 0.40+
- **Schema validation**: Pydantic v2
- **Database**: MySQL via pymysql
- **Cloud operations**: rclone CLI (pikpak:, jianguoyun:, baiduyun: remotes via Alist WebDAV)
- **PikPak API**: httpx-based client for offline downloads
- **Type checking**: pyright (basic mode)

## Rclone Configuration

All cloud drive operations use rclone remotes. Users must manually configure rclone before use. See [RCLONE_CONFIG.md](RCLONE_CONFIG.md) for setup instructions.
