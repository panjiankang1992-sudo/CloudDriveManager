# Research: Cloud Drive Manager

**Feature**: Cloud Drive Manager — HTTP REST 独立服务，支持5个云盘（rclone封装）
**Date**: 2026-04-26
**Status**: ✅ Complete

---

## Decision 1: HTTP 服务框架

### Decision: FastAPI

**Rationale**:
- 原生支持 async（future-proof）；与 uvicorn 结合支持高并发
- 自动生成 OpenAPI 文档（对 API 消费者极有价值）
- Pydantic 内置支持（请求/响应模型天然一体化）
- 成熟稳定（生产级别），与项目参考 AICoding 中使用的技术栈一致
- 轻量：相比 Django 不需要 ORM，适合无数据库的配置文件驱动服务

**Alternatives Considered**:
- **Flask**: 成熟但无原生 async；同步模式下每个请求阻塞线程；不符合现代 Python 服务趋势
- **aiohttp**: 低层，需要手动处理更多基础设施；缺少 OpenAPI 自动文档
- **Django + Django REST Framework**: 过度设计，需要 ORM/数据库支持，本项目无数据库
- **Starlette**: FastAPI 的底层，但直接使用 Starlette 需要更多手工工作

---

## Decision 2: 日志组件

### Decision: Python 标准库 `logging.handlers.RotatingFileHandler`

**Rationale**:
- Python 内置，无需额外依赖
- `RotatingFileHandler` 直接支持：maxBytes=10MB、backupCount=10
- 结合 `TimedRotatingFileHandler` 或自定义清理逻辑可实现 7 天保留
- 项目参考 AICoding 中 `logger.py` 即使用此方案，已有验证

**Alternatives Considered**:
- **structlog**: 更强的结构化日志能力，但增加依赖和学习成本；本项目日志为运维视角（轮转/保留），非结构化需求
- **loguru**: 更简洁的 API，但属于第三方依赖；标准库足够满足需求
- **watchdog + 外部日志管理**: 过度设计

**Retention Strategy**:
- 每次写日志时清理 7 天前文件（参考 AICoding logger.py 的 CleanupHandler 模式）
- 不使用 `TimedRotatingFileHandler`（其备份基于日期而非综合保留+数量限制）

---

## Decision 3: 加密方案

### Decision: Fernet（cryptography 包）

**Rationale**:
- AES-128-CBC + HMAC-SHA256，对称加密，工业级安全
- `cryptography.fernet` 提供 `encrypt()` / `decrypt()` 简洁 API
- 项目参考 AICoding 中 encryption_service.py 已使用 Fernet 方案
- 密文以 `gAAAAAB` 前缀开头，可自动识别（无需额外标记字段）

**Alternatives Considered**:
- **hashlib (SHA256)**: 单向散列，无法解密，不适合需要还原密码的使用场景
- **AES 直接实现**: 需要手动处理 padding/IV/CBC 模式，易出错
- **python-jose / PyJWT**: 用于 token 场景，非密码加密
- **Cryptodome (PyCryptodome)**: 功能等价，但 `cryptography` 生态更广

**Salt（密钥）Storage**:
- 存储在 config YAML 中（如 `encryption.salt: <base64_key>`）
- 服务启动时读取并实例化 Fernet 对象，解密所有密码到内存
- 符合澄清结果：启动时解密，内存明文使用

---

## Decision 4: 配置文件格式

### Decision: YAML（pyyaml）

**Rationale**:
- 项目参考 AICoding 中 `config.yaml` 使用 YAML 格式，一致性优先
- 支持嵌套结构（点号分隔键访问）
- 比 JSON 更适合配置文件（支持注释、裸字符串不需要引号）
- Python `pyyaml` 库内置支持 `yaml.safe_load()`

**Alternatives Considered**:
- **TOML**: Python 3.11+ 内置 `tomllib`，但项目要求 Python 3.10+ 兼容
- **JSON**: 可读但不支持注释，不适合配置文件
- **ini**: 嵌套结构支持差

**环境区分策略**:
- 文件名区分：`config_dev.yaml`（开发）和 `config_prod.yaml`（现网）
- 启动参数传入模式（如 `--mode=dev` 或 `--mode=prod`）
- 配置文件路径拼接：`config/config_{mode}.yaml`

---

## Decision 5: 服务入口与启动方式

### Decision: `main.py` + uvicorn 命令行启动

**Rationale**:
- `main.py` 创建 FastAPI 实例，注册路由，返回 app 对象
- 启动命令：`uvicorn src.main:app --host 0.0.0.0 --port 8000`
- 支持 `--reload` 用于开发模式
- 与项目参考 AICoding 的 launcher.py 模式一致

**Alternatives Considered**:
- **自定义 daemon**: 过度设计，uvicorn 足够
- **multiprocessing + 信号处理**: 同上
- **Docker 入口**: 容器化部署后续考虑，当前阶段不需要

---

## Decision 6: 子进程管理（rclone 调用）

### Decision: `subprocess.run()` 同步调用

**Rationale**:
- rclone 命令执行为同步 I/O，单个命令耗时从毫秒到分钟不等
- 使用 `asyncio.create_subprocess_exec()` 可实现 async，但增加复杂度
- 参考 AICoding 的 rclone_adapter.py 使用 `subprocess.run()`，经验证可行
- 对于长时间运行的下载，使用后台进程 + 进度回调（参考 AICoding 实现）

**Alternatives Considered**:
- **asyncio subprocess**: 需要将 rclone adapter 重写为 async，增加复杂度；当前阶段不需要
- **rclonerc / rclone API**: 需要 rclone serve 命令启动 HTTP 服务，额外资源消耗

---

## Decision 7: API 响应格式

### Decision: 统一 JSON 格式

**Response Schema**:
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

**Error Response Schema**:
```json
{
  "code": 1,
  "message": "错误描述",
  "error_code": "CONFIG_KEY_NOT_FOUND"
}
```

**Rationale**:
- 参考 AICoding HTTP API 响应格式，一致性优先
- HTTP 状态码统一使用 200（业务成功）/ 400（参数错误）/ 404（资源不存在）/ 500（服务器错误）
- 业务错误码在 JSON body 的 `error_code` 字段中返回（符合 FR-003 字符串错误码）

---

## Open Questions Resolved

| # | Question | Resolution |
|---|----------|------------|
| 1 | HTTP 框架选型 | FastAPI（成熟、async、Pydantic、OpenAPI 自动文档） |
| 2 | 日志库选型 | Python 标准库 logging + RotatingFileHandler |
| 3 | 加密算法选型 | Fernet（cryptography 包，AES-128-CBC + HMAC-SHA256） |
| 4 | 配置文件格式 | YAML（pyyaml），文件名区分环境 |
| 5 | 服务启动方式 | main.py + uvicorn 命令行 |
| 6 | rclone 调用方式 | subprocess.run() 同步调用 |
| 7 | API 响应格式 | 统一 JSON `{code, message, data}` |