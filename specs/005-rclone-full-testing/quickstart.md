# Quickstart: Rclone Full Testing

**Feature**: 005-rclone-full-testing | **Date**: 2026-05-03

## 测试运行

### 前提条件

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python -m src.main init-db
```

### 运行全部测试

```bash
pytest tests/ -v
```

### 运行单元测试（无需真实云盘）

```bash
pytest tests/unit/ -v
```

单元测试通过 mock rclone subprocess 避免真实 I/O。测试使用 `conftest.py` 中设置的环境变量：
- `CONFIG_ENV=dev`
- `RCLONE_PATH=echo`（模拟 rclone 存在）

### 运行集成测试（需要真实 rclone 配置）

```bash
# 确保 rclone 在 PATH 中且 remotes 已配置
rclone listremotes

# 确保 MySQL 可连接
# config/config_dev.yaml 中的 database 配置正确

pytest tests/integration/ -v
```

### 运行单个测试文件

```bash
pytest tests/unit/test_rclone_adapter.py -v
pytest tests/integration/test_api.py -v
```

### Mock rclone 进行测试

在 `conftest.py` 中已配置：

```python
os.environ["RCLONE_PATH"] = "echo"  # dummy rclone for smoke tests
```

如需修改，使用 `monkeypatch`：

```python
def test_something(monkeypatch):
    monkeypatch.setenv("RCLONE_PATH", "/path/to/mock/rclone")
```

---

## API 服务运行

### 开发模式

```bash
python -m src.main
# 服务启动于 http://0.0.0.0:29312
# API 文档: http://localhost:29312/docs
```

### 生产模式

```bash
python -m src.main --prod
```

---

## MCP 服务运行

```bash
python -m src.mcp
# MCP 服务启动于 http://0.0.0.0:29313
```

---

## 数据库初始化

```bash
python -m src.main init-db
```

这将创建/更新以下表：
- `sync_jobs`
- `cloud_download_jobs`（新增）
- `operation_logs`

---

## 测试覆盖范围

| 模块 | 测试内容 |
|------|---------|
| `test_rclone_adapter.py` | rclone 命令参数构造、输出解析、进度正则 |
| `test_schemas.py` | 所有 Pydantic schema 序列化/反序列化 |
| `test_exceptions.py` | CloudDriveError 层级、错误码、to_dict() |
| `test_api.py` | 所有 API 端点注册、路由匹配 |
| 新增 | CloudDownloadJob 生命周期、FILE_IN_USE 逻辑 |
| 新增 | 3 种云盘类型契约一致性（PikPak、JianGuoYun、BaiduYun） |
| 新增 | rclone-only 架构约束验证 |
