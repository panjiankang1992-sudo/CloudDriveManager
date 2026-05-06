# Rclone 配置指南

CloudDriveManager 所有网盘操作均通过 rclone 实现。用户需提前在本地配置好 rclone remotes。

## 安装 rclone

```bash
# Linux/macOS
curl https://rclone.org/install.sh | sudo bash

# Windows
# 从 https://rclone.org/downloads/ 下载并安装

# 验证安装
rclone version
```

## 配置 rclone remotes

### 1. 运行配置向导

```bash
rclone config
```

按照提示创建各网盘的 remote。

### 2. PikPak 配置

```
name> pikpak
Storage> pikpak
Username> your_email@example.com
Password> your_password
```

PikPak remote 创建后，使用 `pikpak:` 前缀访问，例如：
- `rclone ls pikpak:/`
- `rclone copy pikpak:/file.txt ./local/`

### 3. 坚果云 (JianGuoYun) 配置

坚果云需要通过 WebDAV 连接：

```bash
rclone config
```

```
name> jianguoyun
Storage> webdav
URL> https://dav.jianguoyun.com/dav/
Vendor> other
User> your_username
Password> your_app_password
```

### 4. 百度网盘 (BaiduYun) 配置

百度网盘需要通过 Alist WebDAV 代理：

```bash
rclone config
```

```
name> baiduyun
Storage> webdav
URL> http://localhost:5244/dav/baidu/
Vendor> other
User> your_username
Password> your_password
```

### 5. 阿里云盘配置

```bash
rclone config
```

```
name> aliyun
Storage> webdav
URL> http://localhost:5244/dav/aliyun/
Vendor> other
User> your_username
Password> your_password
```

### 6. 夸克网盘配置

```bash
rclone config
```

```
name> quark
Storage> webdav
URL> http://localhost:5244/dav/quark/
Vendor> other
User> your_username
Password> your_password
```

## 验证配置

```bash
# 列出所有 remotes
rclone listremotes

# 测试 PikPak 连接
rclone lsd pikpak:

# 测试坚果云连接
rclone lsd jianguoyun:
```

## 配置文件位置

- Linux/macOS: `~/.config/rclone/rclone.conf`
- Windows: `%APPDATA%\rclone\rclone.conf`

## 使用 app password

对于支持两步验证的网盘，建议使用应用专用密码而不是登录密码。

## 故障排除

### PikPak 登录失败
- 确认用户名密码正确
- 尝试在浏览器登录 PikPak 确认账号状态
- 检查是否有异地登录风控

### WebDAV 连接超时
- 确认 Alist 服务正常运行
- 检查网络连接和防火墙设置
- 确认 WebDAV 路径正确

## config.yaml 配置

在 `config/config_dev.yaml` 或 `config/config_prod.yaml` 中配置 rclone 路径：

```yaml
cloud_drives:
  rclone_path: rclone  # 或完整路径如 /usr/local/bin/rclone
  timeout: 300          # 操作超时时间（秒）
```
