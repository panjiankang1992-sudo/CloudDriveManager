# Research: 云盘通用文件操作

**Feature**: [spec.md](./spec.md)
**Updated**: 2026-05-01

## Research Questions

以下问题通过背景调研和代码分析回答：

1. **FastAPI 异步任务队列**：BackgroundTasks vs 自定义内存队列？
2. **rclone 进度追踪**：如何解析 `--progress` 输出？
3. **任务取消**：Python 如何安全中断正在运行的 subprocess？
4. **结构化日志**：Python logging 如何配置 JSON 输出？
5. **PikPak API**：离线下载接口和认证流程

---

## Q1: FastAPI 异步任务队列

### Decision: 内存 dict + threading（轻量方案）

### Rationale

个人工具场景（单一管理员、无多进程需求），无需引入 Celery/Redis。

**方案对比**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| FastAPI BackgroundTasks | 官方集成，生命周期绑定请求 | 无法查询状态，不支持取消 |
| `asyncio.create_task` | 原生异步，生命周期绑定 app | 进程退出时任务丢失，无持久化 |
| **内存 dict + Background thread** | 可查询、可取消、简单 | 进程重启任务丢失（可接受） |
| Celery + Redis | 任务持久化、分布式 | 过度工程，引入额外依赖 |

**最终选择**：内存 dict（`SyncJobManager._jobs: dict[job_id, SyncJob]`）+ `threading.Thread` 执行下载 + `threading.Event` 取消信号。

### Alternatives Considered

- Celery：引入 Redis 依赖，不适合个人工具
- asyncio + create_task：无法取消正在运行的任务
- FastAPI BackgroundTasks：无法轮询状态

---

## Q2: rclone 进度追踪

### Decision: 解析 `rclone copy --progress` stdout

### Rationale

rclone 支持 `--progress` 标志，输出格式稳定：

```
Transferred:    1.345 GiB / 10.382 GiB, 13%, 11.161 MiB/s, ETA 13m41s
```

**进度解析正则**（Python）：
```python
import re
PROGRESS_RE = re.compile(
    r"Transferred:\s+([\d.]+ [KMGT]iB) / ([\d.]+ [KMGT]iB),\s+(\d+)%"
)
```

### Alternatives Considered

- rclone `--log-format` + `--log-file`：日志格式不同，进度信息不完整
- rclone `rc core/stats`：需要 rclone rc 服务，不适合简单 CLI 调用
- **最终选择**：直接解析 `--progress` stdout，最简单可靠

### rclone moveto 不自动创建目录

rclone `moveto` 不会创建目标目录的父目录。需要在 moveto 前执行 `rclone mkdir`。

```bash
rclone mkdir pikpak:/backup/documents
rclone moveto pikpak:/docs/a.txt pikpak:/backup/documents/a.txt
```

---

## Q3: 任务取消（subprocess interruption）

### Decision: `subprocess.Popen` + `proc.terminate()` / `proc.kill()`

### Rationale

下载进程由 `threading.Thread` 启动的 `subprocess.Popen` 管理。取消时：

1. 调用 `proc.terminate()` 发送 SIGTERM（优雅终止）
2. 等待最多 5 秒
3. 若未退出，调用 `proc.kill()` 强制杀死
4. 删除临时文件

**取消信号**：`threading.Event`（`cancel_event.is_set()` 检测取消请求）

```python
import subprocess, threading, os, time

cancel_event = threading.Event()

def download_thread(cancel_event, job_id):
    proc = subprocess.Popen(
        ["rclone", "copy", "--progress", f"pikpak:/files/{job_id}", local_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in proc.stdout:
        if cancel_event.is_set():
            proc.terminate()
            time.sleep(5)
            if proc.poll() is None:
                proc.kill()
            # cleanup temp files
            return
        # parse progress from line
    proc.wait()
```

### Alternatives Considered

- `asyncio.create_task` + `task.cancel()`：仅能取消协程，无法杀死 subprocess
- `multiprocessing.Process` + `terminate()`：更安全隔离，但更复杂
- **最终选择**：threading + subprocess.Popen，最简单够用

---

## Q4: 结构化 JSON 日志

### Decision: Python `logging` + 自定义 `JSONFormatter`

### Rationale

使用 Python 标准库 `logging`，通过自定义 formatter 输出 JSON。

```python
import logging, json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "extra": getattr(record, "extra", {})
        }
        return json.dumps(log_obj, ensure_ascii=False)

# 配置
handler = logging.FileHandler("log/app.log")
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("sync_api")
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

SC-008 要求：日志 buffered flush ≤ 5s。使用 `logging.handlers.TimedRotatingFileHandler` 或 `flush()`。

### Alternatives Considered

- `loguru`：更现代，但引入额外依赖
- 手动写 JSON 文件：无法接入 Python logging 生态
- **最终选择**：标准 logging + custom formatter

---

## Q5: PikPak API 离线下载

### Status: NEEDS RESEARCH — 需调研 PikPak 官方 API

> 调研 Agent bg_84cd9f08 尚未完成，以下为初步方案

PikPak 离线下载需要 PikPak 官方 API（非 rclone）：

**API Base**: `https://api.mypikpak.com`

**认证流程**：
1. `POST /v1/auth/signin` — username + password → access_token
2. `POST /v1/download` — access_token + urls → task_id

**已知端点**（待调研确认）：
```
POST https://api.mypikpak.com/v1/auth/signin
POST https://api.mypikpak.com/v1/download
GET  https://api.mypikpak.com/v1/download?task_id=xxx
```

**凭证存储**：
- `CloudDriveConfig.username` = PikPak 登录邮箱
- `CloudDriveConfig.password_encrypted` = Fernet 加密密码（用于获取 access_token）

**PikPak API 限速**：Clarification 确认使用指数退避（1s→2s→4s…，上限 60s）

### Fallback（若 API 调研失败）

若 PikPak 官方 API 无法对接：
- 标记 `cloud_download_add` 为 `NotImplementedError`
- 云下载功能仅记录日志，不可用
- SC-004 不适用（无任务 ID 返回）

---

## Implementation Risk Summary

| 风险 | 等级 | 缓解 |
|------|------|------|
| PikPak API 认证/接口调研失败 | 中 | 已有 NotImplementedError fallback |
| rclone 进度解析格式变更 | 低 | 解析失败时隐藏进度，不阻塞 |
| 进程取消后临时文件残留 | 低 | 统一清理函数，cancel 时调用 |
| MySQL 操作日志延迟超 500ms | 低 | 同步写入，事务 commit 后再返回 |
| 并发任务超过 5 个 | 低 | API 层校验，返回 `OPERATION_QUEUE_FULL` |
