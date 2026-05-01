# Feature Specification: Cloud Drive Manager

**Feature Branch**: `001-cloud-drive-manager`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "构建一个云盘管理器，包含公共能力（日志/加密/异常/配置）和功能模块（rclone封装、多云盘接口），支持PikPak、坚果云、百度云、阿里云、夸克云五个云盘类型"

## Clarifications

### Session 2026-04-26

- Q: 系统交付形态是纯Python库、Python库+API层、还是独立服务？ → A: 独立服务 — 系统作为后台服务进程运行，所有云盘操作通过API调用访问，支持HTTP REST接口供外部调用
- Q: 密码解密策略是什么？ → A: 加密存储，按需解密 — 配置文件存储加密后密文，服务启动时解密所有密码到内存，后续直接使用明文
- Q: 错误码体系采用哪种格式？ → A: 纯字符串错误码（如 `CONFIG_KEY_NOT_FOUND`、`PIKPAK_FILE_NOT_FOUND`），直观易读

## User Scenarios & Testing

### User Story 1 - 配置与日志基础设施 (Priority: P1)

作为运维/集成方，我希望将云盘管理器作为独立服务部署，通过HTTP API调用各云盘操作，无需关心底层实现细节。

**Why this priority**: 公共能力是所有功能模块的前置依赖，没有配置和异常机制就无法正确构建任何云盘功能。

**Independent Test**: 可以通过启动服务后调用API验证服务就绪，通过单元测试验证 Config.get() 能否正确读取配置、日志能否按指定参数轮转、异常能否携带错误码抛出和捕获、密码能否正确加密解密来独立完成测试。

**Acceptance Scenarios**:

1. **Given** 项目中存在 `config/config_dev.yaml` 和 `config/config_prod.yaml` 配置文件，**When** 启动时指定模式为 `dev`，**Then** 系统自动加载 `config_dev.yaml`，开发者通过 `Config.get("key")` 获取到开发环境的配置值
2. **Given** 配置中存在某键值对 `app.name: MyDrive`，**When** 调用 `Config.get("app.name")`，**Then** 返回 `MyDrive`；**When** 调用 `Config.get("nonexistent.key")`，**Then** 抛出配置缺失错误而非返回 None
3. **Given** 日志模块以 10MB 大小轮转、保留7天、最多10个文件的方式运行，**When** 日志文件超过 10MB，**Then** 自动创建新日志文件，旧日志文件按序保留；**When** 日志文件超过7天，**Then** 自动清理
4. **Given** 密码需要加密存储在配置文件中，**When** 服务启动，**Then** 所有加密密码自动解密到内存；**When** 对明文密码调用加密接口，**Then** 生成密文；盐值从配置文件中读取
5. **Given** 统一异常机制，**When** 发生业务错误时，**Then** 抛出携带错误码和描述的异常；**When** 调用方捕获异常，**Then** 可以从异常对象中获取错误码和错误信息

---

### User Story 2 - Rclone 云盘操作封装 (Priority: P2)

作为 API 使用者，我希望通过统一的 HTTP API 对多个云盘执行文件操作（查看列表、查看详情、下载、删除、同步），而不需要关心底层 rclone 命令的差异。

**Why this priority**: rclone 封装是多云盘接口的基础，只有完成了统一的底层操作能力，才能在上层为各种云盘提供一致的服务接口。

**Independent Test**: 可以通过调用服务的 API 接口（列出目录、获取文件详情、下载、删除、同步），验证返回结果的正确性来独立测试；内部实现通过 RcloneAdapter 调用 rclone 命令完成。

**Acceptance Scenarios**:

1. **Given** 一个已配置的 rclone remote（例如 pikpak），**When** 调用 list_directory("/")，**Then** 返回该 remote 根目录下的文件和文件夹列表，每项包含名称、大小、类型、修改时间等信息
2. **Given** 一个已知路径的文件，**When** 调用 get_file_detail("path/to/file")，**Then** 返回该文件的详细信息（大小、类型、修改时间等）
3. **Given** 一个云盘中的文件，**When** 调用 download_file("cloud/path", "local/path")，**Then** 文件成功下载到本地指定路径
4. **Given** 一个云盘路径，**When** 调用 delete_item("/path/to/delete")，**Then** 该路径的文件或文件夹被删除；**When** 尝试删除根目录 "/"，**Then** 抛出禁止操作的错误
5. **Given** 两个不同云盘之间的文件，**When** 调用 sync 操作，**Then** 源云盘的文件同步到目标云盘

---

### User Story 3 - 多云盘管理接口 (Priority: P3)

作为 API 使用者，我希望通过统一的 HTTP API 调用不同云盘的操作，每个云盘类型（PikPak、坚果云、百度云、阿里云、夸克云）都提供一致的基础操作（浏览、详情、下载、删除、同步），且能根据云盘特性提供扩展能力（如PikPak的云下载）。

**Why this priority**: 多云盘接口是最终面向使用者的能力层，依赖 P1（基础设施）和 P2（rclone封装）完成后才能构建。

**Independent Test**: 可以通过调用各云盘的 API 接口，分别验证返回结果符合预期来独立测试每个云盘类型。

**Acceptance Scenarios**:

1. **Given** PikPak 云盘已配置，**When** 通过 PikPak 接口执行浏览、详情、下载、移动、删除操作，**Then** 所有操作正确完成，且 PikPak 特有的云下载（离线下载）功能可用
2. **Given** 坚果云已配置，**When** 通过坚果云接口执行浏览、详情、下载、删除、同步操作，**Then** 所有操作正确完成
3. **Given** 百度云已配置，**When** 通过百度云接口执行浏览、详情、下载、删除、同步操作，**Then** 所有操作正确完成
4. **Given** 阿里云已配置，**When** 通过阿里云接口执行浏览、详情、下载、删除、同步操作，**Then** 所有操作正确完成
5. **Given** 夸克云已配置，**When** 通过夸克云接口执行浏览、详情、下载、删除、同步操作，**Then** 所有操作正确完成
6. **Given** 一个未配置的云盘类型，**When** 尝试实例化其操作接口，**Then** 抛出明确的配置缺失异常

---

### Edge Cases

- 当配置文件缺失某个必需的键时，Config.get() 应抛出明确的错误，而非返回 None 或空值
- 当 rclone 可执行文件不存在或版本不兼容时，rclone 适配器应在初始化阶段报错，而非延迟到运行时
- 当云盘连接中断或超时时，操作应按重试策略自动重试，重试耗尽后抛出网络异常
- 当日志目录不可写时，应降级到控制台日志而非崩溃
- 当配置中加密盐值为空或无效时，加密服务应报错而非静默失败
- 当服务启动时密码解密失败（如盐值错误、密文损坏），服务启动应失败并给出明确错误信息
- 不同云盘的 remote 名称配置错误时（如 remote 不存在），应在初始化时快速失败
- 删除操作应有安全检查（如禁止删除根目录）

## Requirements

### Functional Requirements

**公共能力模块**

- **FR-001**: 系统必须提供日志记录能力，日志文件按 10MB 大小轮转，保留最近 7 天的日志，最多保存 10 个日志文件
- **FR-002**: 系统必须提供密码加密/解密能力，使用配置文件中的盐值进行对称加密；配置文件存储加密后密文，服务启动时将所有密码解密至内存供后续使用，盐值存储在配置文件中
- **FR-003**: 系统必须提供统一的异常机制，包含：基础异常类、纯字符串错误码体系（如 `CONFIG_KEY_NOT_FOUND`、`RCLONE_NETWORK_ERROR`、`PIKPAK_FILE_NOT_FOUND`）、分类异常（如路径无效、网络错误、文件不存在、云盘错误等）；HTTP API 响应中错误码在 JSON body 中返回
- **FR-004**: 系统必须支持通过文件名区分开发环境和现网环境的配置文件（如 config_dev.yaml / config_prod.yaml），启动时通过指定模式加载对应配置
- **FR-005**: 系统必须提供 Config.get("key") 形式的配置读取接口，不提供默认值；当配置键不存在时，必须抛出异常而非返回空值
- **FR-006**: 系统必须支持嵌套配置键的点号分隔访问（如 "pikpak.remote_name"），以及环境变量覆盖

**Rclone 功能模块**

- **FR-007**: 系统必须封装 rclone 的目录列表（lsjson）能力，返回结构化的文件/文件夹信息列表
- **FR-008**: 系统必须封装 rclone 的文件详情查询能力，返回单个文件或文件夹的详细属性
- **FR-009**: 系统必须封装 rclone 的文件下载能力（copyto），支持从云盘下载文件到本地
- **FR-010**: 系统必须封装 rclone 的文件删除能力（purge），包含安全检查（禁止删除根目录）
- **FR-011**: 系统必须封装 rclone 的文件同步能力（sync/copy），支持云盘间或云盘与本地间同步
- **FR-012**: 系统必须支持通过配置指定不同的 rclone remote，以支持多种云盘类型（而非硬编码单一 remote）
- **FR-013**: 系统必须在 rclone 操作中提供重试机制和超时控制，网络异常时自动重试

**Cloud Drive 功能模块**

- **FR-014**: 系统必须为 PikPak 云盘提供 HTTP API 接口，包含：浏览目录、查看文件详情、下载文件、移动文件、删除文件、云下载（离线下载）
- **FR-015**: 系统必须为坚果云提供 HTTP API 接口，包含：浏览目录、查看文件详情、下载文件、删除文件、同步文件
- **FR-016**: 系统必须为百度云提供 HTTP API 接口，包含：浏览目录、查看文件详情、下载文件、删除文件、同步文件
- **FR-017**: 系统必须为阿里云盘提供 HTTP API 接口，包含：浏览目录、查看文件详情、下载文件、删除文件、同步文件
- **FR-018**: 系统必须为夸克云提供 HTTP API 接口，包含：浏览目录、查看文件详情、下载文件、删除文件、同步文件
- **FR-019**: 每种云盘 API 必须遵循统一的路由规范（如 `/cloud/{drive_type}/list`、`/cloud/{drive_type}/download`），确保调用方式一致
- **FR-020**: 各云盘可提供扩展 API（如 PikPak 的云下载 `/cloud/pikpak/offline-download`），这些扩展能力不影响基础接口的一致性
- **FR-021**: 系统必须提供服务健康检查接口（如 `/health`），供部署监控使用

### Key Entities

- **CloudDriveAPI**: HTTP API 服务层，负责接收外部请求、路由到对应云盘服务、返回标准化 JSON 响应
- **CloudDriveService**: 云盘操作业务逻辑层，调用 RcloneAdapter 执行实际操作
- **RcloneAdapter**: rclone 命令的封装器，负责将高级云盘操作翻译为 rclone 子命令执行，管理连接、重试和错误转换
- **Config**: 配置管理器（单例），负责加载环境相关配置文件并提供点号分隔键访问
- **CloudDriveError**: 统一异常基类（携带错误码），各模块异常继承自此基类
- **FileInfo**: 云盘文件/文件夹的标准化信息结构（名称、路径、大小、类型、修改时间等）

## Success Criteria

### Measurable Outcomes

- **SC-001**: 开发者可以在 5 分钟内完成一个新云盘类型的接入，仅需实现统一接口和添加配置
- **SC-002**: 所有云盘类型的目录列表、文件详情、下载、删除操作在正常网络条件下 95% 的请求在 10 秒内完成响应
- **SC-003**: Config.get("key") 在配置缺失时 100% 抛出异常，无静默返回空值的情况
- **SC-004**: 日志系统在文件达到 10MB 时自动轮转，7 天以上的日志文件被自动清理，日志文件总数不超过 10 个
- **SC-005**: 密码加密后解密还原，100% 与原文一致
- **SC-006**: 所有云盘共享相同的接口签名，调用者无需知道底层是哪个云盘即可完成基础操作
- **SC-007**: 网络异常时系统自动重试（最多 3 次），第 3 次重试失败后才抛出异常；正确配置的情况下 99% 的临时性网络错误可自动恢复
- **SC-008**: 服务在指定端口启动后 5 秒内可响应健康检查请求
- **SC-009**: 所有 API 响应采用统一 JSON 格式，包含状态码、消息和数据字段

## Assumptions

- rclone 已预先安装在运行环境中，且已配置好各云盘类型的 remote（如 `mypikpak`、`myjianguoyun` 等）；本系统不负责 rclone 的安装和 remote 配置
- 云盘类型（PikPak、坚果云、百度云、阿里云、夸克云）均通过 rclone 的对应 remote 进行操作；不使用各云盘的 HTTP SDK
- 系统以独立服务方式部署，支持 Windows 和 WSL 双平台；使用 HTTP REST API 对外提供云盘操作能力
- 配置文件使用 YAML 格式，开发环境配置文件名为 config_dev.yaml，现网环境配置文件名为 config_prod.yaml
- 盐值（加密密钥）存储在配置文件中；服务启动时将所有加密密码解密到内存中使用
- 每个 rclone remote 对应一个云盘类型，通过配置文件中的 remote_name 字段指定
- 同步功能（sync）指的是 rclone 的 sync/copy 操作，将源端文件同步到目标端
- PikPak 的云下载（离线下载）是通过 rclone backend addurl 命令实现的扩展能力，其他云盘可能不具备此功能
- API 路径统一使用 `/cloud/{drive_type}/` 前缀，如 `/cloud/pikpak/list`、`/cloud/jianguoyun/download`