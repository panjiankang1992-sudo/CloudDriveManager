# Implementation Plan: Cloud Drive Manager

**Branch**: `001-cloud-drive-manager` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-cloud-drive-manager/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

构建一个云盘管理器独立服务，通过 HTTP REST API 对外提供 PikPak、坚果云、百度云、阿里云、夸克云五个云盘的操作能力。底层通过封装 rclone 命令实现云盘操作，上层通过 FastAPI 提供统一的 HTTP 接口。核心能力包括：配置管理（config_dev.yaml / config_prod.yaml 按环境加载）、日志（10MB 轮转保留7天）、密码加密（Fernet 对称加密，启动时解密到内存）、统一异常机制（字符串错误码）。

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastAPI (HTTP框架), uvicorn (ASGI服务器), pyyaml (配置加载), cryptography (Fernet加密), structlog (结构化日志)
**Storage**: YAML 配置文件（config_dev.yaml / config_prod.yaml）；无数据库
**Testing**: pytest（单元测试），手动 API 测试
**Target Platform**: Windows 和 WSL（双平台支持）
**Project Type**: HTTP REST 独立服务（后台进程）
**Performance Goals**: API 响应时间 P95 < 10s；服务启动 < 5s
**Constraints**: 日志 10MB 轮转保留7天最多10个；网络异常自动重试最多3次
**Scale/Scope**: 单实例部署；同时支持 5 个云盘类型（pikpak/jianguoyun/baidu/aliyun/quark）；支持后续扩展新云盘类型

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

宪法为模板文件，尚未填写具体原则。因此本 feature 无需进行 Constitution Gate 检查。
所有设计决策基于行业最佳实践和项目需求制定。

**Gate Status**: ✅ PASSED（宪法为模板，无约束门）

## Project Structure

### Documentation (this feature)

```text
specs/001-cloud-drive-manager/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── api-contract.md  # HTTP API 规范
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── main.py              # 服务入口，FastAPI 实例化
├── config/
│   ├── __init__.py
│   └── config.py        # 配置管理器（单例，支持 config_dev.yaml / config_prod.yaml）
├── core/
│   ├── __init__.py
│   ├── logger.py        # 日志组件（RotatingFileHandler，10MB/7天/最多10个）
│   ├── encryption.py     # 加密服务（Fernet，启动时解密所有密码到内存）
│   └── exceptions.py    # 统一异常体系（字符串错误码）
├── adapters/
│   ├── __init__.py
│   └── rclone_adapter.py  # rclone 命令封装（subprocess 调用 rclone）
├── services/
│   ├── __init__.py
│   ├── base.py          # 云盘操作基类（CloudDriveService）
│   ├── pikpak.py        # PikPak 实现
│   ├── jianguoyun.py    # 坚果云实现
│   ├── baidu.py         # 百度云实现
│   ├── aliyun.py        # 阿里云实现
│   └── quark.py         # 夸克云实现
└── api/
    ├── __init__.py
    ├── router.py        # FastAPI 路由聚合
    ├── cloud.py         # 云盘通用 API 路由
    ├── health.py        # 健康检查路由
    └── schemas.py       # Pydantic 请求/响应模型

config/
├── config_dev.yaml      # 开发环境配置
└── config_prod.yaml     # 现网环境配置

tests/
├── unit/
│   ├── test_config.py
│   ├── test_logger.py
│   ├── test_encryption.py
│   └── test_rclone_adapter.py
└── integration/
    └── test_api.py      # API 集成测试
```

**Structure Decision**: 单项目结构（Option 1），按功能分层（config/core/adapters/services/api），而非前后端分离。所有代码在 `src/` 下，配置在 `config/` 下，测试在 `tests/` 下。API 层直接调用 Service 层，Service 层调用 RcloneAdapter，无需 Repository 层。

## Phase 0: Research

[See research.md](./research.md)

## Phase 1: Design & Contracts

[See data-model.md](./data-model.md)
[See contracts/api-contract.md](./contracts/api-contract.md)
[See quickstart.md](./quickstart.md)

## Complexity Tracking

> 无 Constitution 违规，无需填写复杂度追踪表。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 无 | - | - |