# Quickstart: Cloud Drive Manager

**Feature**: Cloud Drive Manager
**Date**: 2026-04-26

---

## 环境准备

### 前置依赖

1. **Python 3.10+**
   ```bash
   python --version  # 确认 >= 3.10
   ```

2. **rclone 已安装并配置**
   - 下载 rclone: https://rclone.org/downloads/
   - 配置各云盘 remote：
     ```bash
     rclone config
     # 配置示例（pikpak）:
     # name: mypikpak
     # type: pikpak
     # username: your@email.com
     # password: your_password
     ```
   - 验证 rclone 可用：
     ```bash
     rclone version
     ```

### 安装步骤

```bash
# 1. 克隆或进入项目目录
cd CloudDriveManager

# 2. 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/WSL

# 3. 安装依赖
pip install fastapi uvicorn pyyaml cryptography pytest

# 4. 配置 rclone 路径（编辑 config_dev.yaml）
# config_dev.yaml 中添加：
# pikpak:
#   rclone_path: D:/software/rclone/rclone.exe
#   remote_name: mypikpak
```

---

## 配置文件

在 `config/` 目录下创建配置文件：

### config_dev.yaml（开发环境）

```yaml
app:
  name: cloud_drive_manager
  version: 1.0.0
  mode: dev

server:
  host: 0.0.0.0
  port: 8000

log:
  level: DEBUG
  max_bytes: 10485760    # 10MB
  backup_count: 10
  retention_days: 7

encryption:
  salt: your_fernet_key_here  # 生成方式见下方

encryption:
  salt: irydSRYkbek-AcWtcP-a1p2_Y1CIYOXdmHZEPJRWNVg=  # 示例（请替换为新密钥）

pikpak:
  remote_name: mypikpak
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 3
  timeout: 300

jianguoyun:
  remote_name: myjianguoyun
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 3
  timeout: 300

baidu:
  remote_name: mybaidu
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 3
  timeout: 300

aliyun:
  remote_name: myaliyun
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 3
  timeout: 300

quark:
  remote_name: myquark
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 3
  timeout: 300
```

### config_prod.yaml（生产环境）

```yaml
app:
  name: cloud_drive_manager
  version: 1.0.0
  mode: prod

server:
  host: 0.0.0.0
  port: 8000

log:
  level: INFO
  max_bytes: 10485760
  backup_count: 10
  retention_days: 7

encryption:
  salt: <生产环境密钥>

pikpak:
  remote_name: mypikpak
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 5
  timeout: 600

jianguoyun:
  remote_name: myjianguoyun
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 5
  timeout: 600

baidu:
  remote_name: mybaidu
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 5
  timeout: 600

aliyun:
  remote_name: myaliyun
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 5
  timeout: 600

quark:
  remote_name: myquark
  rclone_path: D:/software/rclone/rclone.exe
  max_retries: 5
  timeout: 600
```

---

## 生成加密密钥

```bash
# 使用 Python 生成 Fernet 密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

将输出粘贴到配置文件的 `encryption.salt` 字段。

---

## 启动服务

```bash
# 开发模式（自动重载）
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**指定环境模式**：
```bash
# 启动时通过命令行参数或环境变量指定模式
# （取决于实现，可选）
uvicorn src.main:app --host 0.0.0.0 --port 8000 --app-mode prod
```

---

## API 访问

服务启动后，访问：

| 端点 | 方法 | 说明 |
|------|------|------|
| `http://localhost:8000/health` | GET | 健康检查 |
| `http://localhost:8000/docs` | GET | Swagger UI（FastAPI 自动提供） |
| `http://localhost:8000/openapi.json` | GET | OpenAPI JSON |

### 常用 API 调用示例

```bash
# 健康检查
curl http://localhost:8000/health

# 列出 PikPak 根目录
curl "http://localhost:8000/cloud/pikpak/list?path=/"

# 获取文件详情
curl "http://localhost:8000/cloud/pikpak/detail?path=/readme.txt"

# 下载文件
curl -X POST http://localhost:8000/cloud/pikpak/download \
  -H "Content-Type: application/json" \
  -d '{"cloud_path": "/readme.txt", "local_path": "D:/Downloads/readme.txt"}'

# 删除文件
curl -X POST http://localhost:8000/cloud/pikpak/delete \
  -H "Content-Type: application/json" \
  -d '{"path": "/downloads/old_file.txt"}'

# PikPak 离线下载
curl -X POST http://localhost:8000/cloud/pikpak/offline-download \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/file.zip"], "destination_folder": "/downloads"}'

# 同步文件（pikpak -> 坚果云）
curl -X POST http://localhost:8000/cloud/sync \
  -H "Content-Type: application/json" \
  -d '{"source_drive": "pikpak", "source_path": "/downloads", "dest_drive": "jianguoyun", "dest_path": "/backup/downloads"}'
```

---

## 运行测试

```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试（需要服务运行）
pytest tests/integration/ -v
```

---

## 常见问题

### 1. rclone 可执行文件找不到

```
RCLONE_NOT_FOUND: rclone 可执行文件不存在
```
**解决**：确保 `rclone_path` 配置正确，或将 rclone 加入 PATH。

### 2. 配置文件找不到

```
CONFIG_FILE_NOT_FOUND: config/config_dev.yaml 未找到
```
**解决**：确认 `config/config_dev.yaml` 或 `config/config_prod.yaml` 存在于项目根目录。

### 3. 加密盐值无效

```
ENCRYPTION_SALT_INVALID: 盐值无效或为空
```
**解决**：重新生成 Fernet 密钥并更新配置文件。

### 4. 密码解密失败

```
DECRYPTION_FAILED: 无法解密密码
```
**解决**：确认配置文件中的密码密文是由相同的 Fernet 密钥生成的。

### 5. 云盘 remote 未配置

```
CLOUD_DRIVE_NOT_CONFIGURED: pikpak 云盘未配置
```
**解决**：在配置文件中添加 `pikpak` 配置块，并确保 `remote_name` 与 rclone config 中的名称一致。