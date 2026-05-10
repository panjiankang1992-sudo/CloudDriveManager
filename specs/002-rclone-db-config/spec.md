# Feature Specification: rclone 云盘配置数据库持久化 + 自动配置

## 1. Overview

**Feature Name**: rclone 云盘配置数据库持久化 + 自动配置
**Feature ID**: 002-rclone-db-config
**User Story**: US-DB-CONFIG

---

## 2. User Story

作为系统管理员，我希望将各云盘的 rclone 连接配置（remote name、类型、endpoint、账号、密码）存储在 MySQL 数据库中，并在服务启动时，如果本地 rclone 尚未配置某个云盘，能够从数据库读取配置并自动执行 `rclone config` 完成该云盘的本地配置，这样新环境无需手动执行 `rclone config` 即可使用所有云盘。

---

## 3. Goals

- 将 5 个云盘的 rclone 连接配置持久化到 MySQL
- 服务启动时自动检测并配置本地缺失的 rclone remote
- 密码使用 Fernet 加密后存储，无法明文读取
- 提供云盘配置的 CRUD REST API（仅管理员使用）

---

## 4. Technical Architecture

### 4.1 Database Schema

**Table**: `cloud_drive_configs`

| Column | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| drive_type | VARCHAR(32) | NOT NULL, UNIQUE | 云盘类型: pikpak/jianguoyun/baidu/aliyun/quark |
| remote_name | VARCHAR(128) | NOT NULL | rclone remote 名称 |
| drive_type_variant | VARCHAR(32) | NOT NULL | rclone remote type: pikpak/jianGuoYun/baidu/AliyunDrive/quark |
| host_endpoint | VARCHAR(512) | NULL | 自定义 API endpoint（可选，默认使用云盘官方） |
| username | VARCHAR(256) | NULL | 登录用户名/邮箱 |
| encrypted_password | VARCHAR(512) | NULL | Fernet 加密后的密码 |
| is_enabled | BOOLEAN | DEFAULT TRUE | 是否启用该配置 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**Index**: `idx_drive_type` on `drive_type`

### 4.2 Module Architecture

```
src/
  core/
    encryption.py          ← 复用: Fernet encrypt/decrypt
  config/
    config.py             ← 复用: YAML 配置
  db/
    models.py             ← NEW: SQLAlchemy ORM 模型
    repository.py          ← NEW: CloudDriveConfig CRUD 操作
    connection.py         ← NEW: MySQL 连接管理
  services/
    base.py               ← 修改: 添加 cloud_download_add 默认实现
    rclone_configurator.py ← NEW: rclone config 自动配置服务
  api/
    admin.py              ← NEW: 管理员 CRUD API
    cloud.py              ← 修改: 使用 DB 配置覆盖 YAML
```

### 4.3 rclone config 非交互式创建

每个云盘的 rclone config 命令：

**PikPak**:
```
rclone config create mypikpak pikpak \
  --filesystem-access-key-id=ACCESS_KEY \
  --filesystem-secret-key=SECRET \
  --oops
```

**坚果云**:
```
rclone config create myjianguoyun jianGuoYun \
  --jianGuoYun-api-url=https://api.jianguoyun.com/api/v1/ \
  --jianGuoYun-token=TOKEN \
  --oops
```

> 注意：不同云盘的 rclone config 参数不同，需要分别实现。

**非交互式方案**：使用 `expect` 工具或 `echo` 命令管道输入（非可靠）。推荐：先用 `rclone config create` 子命令（如果 rclone 版本支持），或通过 `--config` 选项临时写入配置段。

### 4.4 启动时自动配置流程

```
1. Config.load("dev")  # 加载 YAML
2. setup_logger()
3. enc.configure(salt)  # 初始化 Fernet
4. Database.load()  # 连接 MySQL（如果配置了）
5. RcloneConfigurator.autoconfig()  # 自动配置缺失的 remote
   └─ For each enabled DB config:
       ├─ rclone config show | grep remote_name
       ├─ If missing → rclone config create ...
       └─ Log result
6. FastAPI app + routers
```

---

## 5. Functional Requirements

### 5.1 数据库 CRUD API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /admin/cloud-configs | 列出所有云盘配置（密码不返回） |
| GET | /admin/cloud-configs/{drive_type} | 获取指定云盘配置 |
| POST | /admin/cloud-configs | 新增云盘配置 |
| PUT | /admin/cloud-configs/{drive_type} | 更新云盘配置 |
| DELETE | /admin/cloud-configs/{drive_type} | 删除云盘配置 |
| POST | /admin/cloud-configs/{drive_type}/apply | 手动触发对该云盘的 rclone config |

**POST /admin/cloud-configs 请求体**:
```json
{
  "drive_type": "pikpak",
  "remote_name": "mypikpak",
  "drive_type_variant": "pikpak",
  "host_endpoint": "https://api.mypikpak.com",
  "username": "user@example.com",
  "password": "plaintext_password"
}
```

**GET /admin/cloud-configs/{drive_type} 响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "drive_type": "pikpak",
    "remote_name": "mypikpak",
    "drive_type_variant": "pikpak",
    "host_endpoint": "https://api.mypikpak.com",
    "username": "user@example.com",
    "password_set": true,
    "is_enabled": true,
    "created_at": "2026-04-27T12:00:00Z",
    "updated_at": "2026-04-27T12:00:00Z"
  }
}
```

> 注意：`password` 字段仅在创建/更新时需要传入，读取时永不明文返回。

### 5.2 启动时自动配置

- 读取所有 `is_enabled=true` 的数据库配置
- 对每个配置检查本地 rclone 是否已存在该 remote
- 如果不存在，执行 `rclone config create` 创建
- 如果已存在，跳过并记录 INFO log
- 自动配置失败不影响服务启动，但记录 ERROR log

### 5.3 凭证安全

- 用户传入明文密码 → Fernet 加密 → 存入 `encrypted_password`
- 读取配置时，永远不返回明文密码（API 响应中无 password 字段）
- 运行时解密后立即用于 rclone config 命令，不持久化解密后的密码

---

## 6. Data Model

### 6.1 CloudDriveConfig (数据库模型)

```python
class CloudDriveConfig(BaseModel):
    id: int | None
    drive_type: str              # pikpak/jianguoyun/baidu/aliyun/quark
    remote_name: str
    drive_type_variant: str       # rclone remote type name
    host_endpoint: str | None
    username: str | None
    encrypted_password: str | None
    is_enabled: bool = True
    created_at: datetime | None
    updated_at: datetime | None

    # 临时字段（不存库）
    password_plaintext: str | None = None  # 仅创建/更新时传入
```

### 6.2 API Schemas

```python
class CloudDriveConfigCreate(BaseModel):
    drive_type: str
    remote_name: str
    drive_type_variant: str
    host_endpoint: str | None
    username: str | None
    password: str | None  # 明文，存入前加密

class CloudDriveConfigUpdate(BaseModel):
    remote_name: str | None
    drive_type_variant: str | None
    host_endpoint: str | None
    username: str | None
    password: str | None  # 明文，留空则不修改密码
    is_enabled: bool | None

class CloudDriveConfigResponse(BaseModel):
    drive_type: str
    remote_name: str
    drive_type_variant: str
    host_endpoint: str | None
    username: str | None
    password_set: bool           # 是否有密码（但不返回密码本身）
    is_enabled: bool
    created_at: datetime | None
    updated_at: datetime | None
```

---

## 7. API Contracts

### 7.1 GET /admin/cloud-configs

**Response 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "drive_type": "pikpak",
      "remote_name": "mypikpak",
      "drive_type_variant": "pikpak",
      "host_endpoint": null,
      "username": "user@example.com",
      "password_set": true,
      "is_enabled": true
    }
  ]
}
```

### 7.2 POST /admin/cloud-configs

**Request Body**: `CloudDriveConfigCreate`

**Response 201**: 配置已创建并已应用 rclone config
**Response 400**: 参数校验失败
**Response 409**: drive_type 已存在

### 7.3 PUT /admin/cloud-configs/{drive_type}

**Request Body**: `CloudDriveConfigUpdate`

**Response 200**: 配置已更新（如果 is_enabled=true 且 remote_name 改变，重新应用 rclone config）

### 7.4 DELETE /admin/cloud-configs/{drive_type}

**Response 200**: 配置已删除

### 7.5 POST /admin/cloud-configs/{drive_type}/apply

手动触发将该配置应用到本地 rclone（如果 remote 已存在则先删除再创建）

**Response 200**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "drive_type": "pikpak",
    "remote_name": "mypikpak",
    "action": "created"  // "created" | "updated" | "unchanged"
  }
}
```

---

## 8. Edge Cases

| 情况 | 处理方式 |
|------|---------|
| MySQL 连接失败 | 回退到纯 YAML 配置，服务正常启动，记录 ERROR log |
| 数据库有配置，但密码为空 | 跳过该云盘的自动配置，记录 WARNING log |
| rclone config create 失败 | 记录 ERROR log，继续处理下一个，不阻塞服务启动 |
| drive_type 已存在但 remote_name 不同 | 先删除旧 remote 再创建新的 |
| encrypted_password 解密失败 | 记录 ERROR log，标记该配置为不可用 |

---

## 9. Dependencies & Assumptions

- MySQL 数据库可用，custom-mysql-mcp 工具可用
- 每个云盘的 rclone remote type 名称已知（pikpak/jianGuoYun/baidu/AliyunDrive/quark）
- rclone 版本 >= 1.54（支持 config create 子命令）
- 数据库管理员已在 MySQL 中创建 `cloud_drive_manager` 数据库和 `cloud_drive_configs` 表

---

## 10. Out of Scope

- 不实现用户认证/权限管理（管理员 API 直接暴露）
- 不实现 rclone remote 的实时同步检查
- 不实现多 rclone 配置文件管理（使用默认 `~/.config/rclone/rclone.conf`）
