# Research: Rclone Full Testing

**Feature**: 005-rclone-full-testing | **Date**: 2026-05-03

## R1: 验证 rclone-only 架构约束

### Decision

使用 Python `ast` 模块扫描所有 `src/` 下的 Python 源文件，检测 `subprocess.run`、`subprocess.Popen`、`subprocess.call` 等调用的存在，并在非白名单模块中触发测试失败。

### Rationale

`ast` 模块提供可靠的静态代码分析，不受代码混淆或动态拼接影响。白名单仅允许 `src/adapters/rclone_adapter.py` 调用 subprocess。

### Alternatives Considered

- **grep 扫描**: 简单但容易误报（如注释中包含关键字）
- **import hooks**: 过于复杂，不适合测试场景
- **AST + 白名单**: 精确控制，测试失败信息清晰

---

## R2: 全面测试 RcloneAdapter 子进程交互

### Decision

使用 `unittest.mock.patch("subprocess.run")` 和 `unittest.mock.patch("subprocess.Popen")` 模拟子进程，按测试场景注入不同的 stdout/stderr 和 returncode。

### Rationale

pytest + mock 是 Python 标准测试实践，不需要真实 rclone 安装或云盘配置。可覆盖 Happy Path 和所有错误路径。

### Alternatives Considered

- **集成测试**: 需要真实 rclone binary 和有效 remotes，不适合 CI
- **pytest-httpserver**: 适用于 HTTP API 测试，不适用于 CLI
- **mock.patch + 黑盒测试**: 与上述决策相同

---

## R3: 异步任务 30 分钟超时看门狗

### Decision

使用后台线程定期查询 PikPak API 任务状态（`get_offline_task_status`），结合 `threading.Timer` 或 `asyncio` 调度，在超时触发时更新数据库状态。

### Rationale

`pikpakapi` 库已提供 `offline_list` API 用于查询任务状态。30分钟超时属于长时间任务，使用独立监控线程比在每次 API 调用时检查更清晰。

### Alternatives Considered

- **每次操作检查**: 增加 API 调用频率，不必要
- **Celery/Redis**: 过度工程，单机工具不需要分布式任务队列
- **独立监控线程**: 实现简单，与现有 SyncJobManager 模式一致

---

## R4: FILE_IN_USE 占用检查

### Decision

`CloudDriveService.delete()` 和 `CloudDriveService.move()` 在执行前检查 `SyncJobManager` 是否有活跃任务（状态为 PENDING 或 RUNNING）正在操作同一文件路径。若存在，返回 `CloudDriveFileInUseError`。

### Rationale

SyncJobManager 已有 `self._jobs` 内存字典，只需在其上检查路径占用即可。无需新增数据库字段。

### Alternatives Considered

- **数据库锁**: 过度复杂，同步任务生命周期短
- **文件系统锁**: rclone 操作本身不是原子的，不可靠
- **内存字典检查**: 简单高效，与 SyncJobManager 共用数据结构

---

## R5: 3 种云盘类型统一契约测试

### Decision

使用 `pytest.mark.parametrize` 对所有 3 种 drive_type（PikPak、JianGuoYun、BaiduYun）执行相同的测试序列，验证响应 schema 一致性和操作等效性。

### Rationale

参数化测试确保每种云盘类型得到平等覆盖，且测试代码不重复。响应 schema 统一性能保证 Service 层抽象有效。

### Alternatives Considered

- **每种类型单独测试文件**: 代码重复，维护成本高
- **fixture 驱动**: 需要复杂的 fixture 工厂，可行但不如 parametrize 直接
- **pytest parametrize**: pytest 内置，清晰简洁
