# Feature Specification: 云盘通用文件操作

**Feature Branch**: `003-cloud-drive-operations`
**Created**: 2026-05-01
**Status**: Draft
**Input**: User description: "每个云盘应该都具备以下功能，如果云盘本身不支持可以不实现对应方法..."

## User Scenarios & Testing

### User Story 1 - 查看云盘目录内容 (Priority: P1)

用户能够浏览云盘指定目录下的文件列表，快速了解目录结构。

**Why this priority**: 目录浏览是云盘最基础、最高频的使用场景，是所有其他操作的前置条件。

**Independent Test**: 可通过调用「列出目录」接口，验证返回文件列表结构完整且与云盘实际内容一致。

**Acceptance Scenarios**:

1. **Given** 用户已配置云盘凭证，**When** 用户请求根目录列表，**Then** 系统返回根目录下的所有文件和文件夹
2. **Given** 用户已配置云盘凭证，**When** 用户请求子目录 `/documents` 列表，**Then** 系统返回该目录下的所有文件和文件夹
3. **Given** 目录不存在，**When** 用户请求该目录列表，**Then** 系统返回空列表
4. **Given** 用户未配置该云盘凭证，**When** 用户请求目录列表，**Then** 系统返回错误提示

---

### User Story 2 - 查看文件/文件夹详情 (Priority: P1)

用户能够获取文件或文件夹的详细元数据（大小、修改时间、文件类型等），辅助文件管理决策。

**Why this priority**: 查看详情是管理文件的基础需求，用户需要依据文件大小、修改时间等信息进行后续操作。

**Independent Test**: 可通过调用「查看详情」接口，验证返回的元数据字段完整且数值合理。

**Acceptance Scenarios**:

1. **Given** 用户已配置云盘凭证，**When** 用户请求 `/documents/file.pdf` 的详情，**Then** 系统返回该文件的大小、修改时间、MIME 类型等元数据
2. **Given** 用户已配置云盘凭证，**When** 用户请求 `/documents/folder` 的详情，**Then** 系统返回该文件夹的元数据（大小为 0，目录标记为 true）
3. **Given** 路径为空，**When** 用户请求详情，**Then** 系统返回错误提示「目录不能为空」
4. **Given** 文件不存在，**When** 用户请求其详情，**Then** 系统返回文件不存在错误

---

### User Story 3 - 移动文件或文件夹 (Priority: P1)

用户能够将文件或文件夹移动到指定目录，支持重命名操作。

**Why this priority**: 文件整理是核心需求，用户需要频繁将文件移动到不同目录进行归档整理。

**Independent Test**: 可通过调用「移动」接口，将测试文件从 A 目录移动到 B 目录，然后调用「列表」接口验证文件已出现在新位置且原位置已不存在。

**Acceptance Scenarios**:

1. **Given** 源路径 `/docs/a.txt` 存在，目标目录 `/archive/` 存在，**When** 用户将 a.txt 移动到 /archive/，**Then** 文件出现在 /archive/ 下，原位置不再存在
2. **Given** 目标目录不存在，**When** 用户移动文件到该目录，**Then** 系统自动创建目标目录，完成移动操作
3. **Given** 源路径为空，**When** 用户请求移动操作，**Then** 系统返回错误提示「源地址不能为空」
4. **Given** 源路径不存在，**When** 用户请求移动操作，**Then** 系统返回源文件不存在错误

---

### User Story 4 - 删除文件或文件夹 (Priority: P2)

用户能够删除指定路径的文件或文件夹，释放云盘存储空间。

**Why this priority**: 删除是云盘管理的基本功能，属于高频操作，但误删后果严重，需要明确的输入校验。

**Independent Test**: 可通过调用「删除」接口删除指定文件，验证原文件不再出现在目录列表中。

**Acceptance Scenarios**:

1. **Given** 文件 `/docs/to_delete.txt` 存在，**When** 用户请求删除该文件，**Then** 系统删除文件并返回成功
2. **Given** 目录 `/docs/folder/` 存在，**When** 用户请求删除该目录，**Then** 系统删除整个目录及其所有内容并返回成功
3. **Given** 路径为根目录 `/`，**When** 用户请求删除操作，**Then** 系统返回错误提示「不能删除根目录」
4. **Given** 路径为空，**When** 用户请求删除操作，**Then** 系统返回错误提示「目录不能为空」
5. **Given** 文件不存在，**When** 用户请求删除操作，**Then** 系统返回文件不存在错误

---

### User Story 5 - 云下载（PikPak 离线下载） (Priority: P2)

用户能够提交离线下载任务，通过 PikPak 的云下载能力将互联网链接的文件直接下载到云盘，无需本地中转。

**Why this priority**: 云下载是 PikPak 的差异化能力，用户在外网环境下可以直接通过链接下载资源到云盘，其他云盘（不原生支持离线下载）可不实现此功能。

**Independent Test**: 可通过调用「云下载」接口提交链接，验证任务 ID 被正确返回，任务可在 PikPak 云盘中查看进度。

**Acceptance Scenarios**:

1. **Given** 用户已配置 PikPak 凭证，**When** 用户提交 3 个链接下载到 `/downloads` 目录，**Then** 系统返回任务 ID，3 个任务在 PikPak 中均可见
2. **Given** 用户提交下载链接，**When** 云盘目录参数为空，**Then** 系统默认将文件下载到 `/My Pack` 目录
3. **Given** 用户提交了无效链接，**When** 系统处理该链接，**Then** 系统返回错误或将该链接标记为失败
4. **Given** 用户为非 PikPak 云盘（如 Baidu、Aliyun），**When** 用户调用云下载接口，**Then** 系统返回「该云盘不支持云下载功能」

---

### User Story 6 - 同步文件到本地 (Priority: P2)

用户能够将云盘指定路径下的文件异步下载到本地，支持断点续传和并发下载。

**Why this priority**: 文件同步到本地是云盘使用的重要场景，用户需要将云盘文件备份或离线使用到本地，异步 + 并发是效率关键。

**Independent Test**: 可通过调用「同步」接口触发下载，验证返回任务 ID，并通过轮询或回调确认下载完成、文件出现在本地目标路径。

**Acceptance Scenarios**:

1. **Given** 云盘路径 `/documents/data.zip` 存在，本地路径 `/home/user/downloads/` 存在，**When** 用户发起同步任务，**Then** 系统异步下载文件到本地，完成后文件完整出现在目标路径
2. **Given** 云盘路径不存在，**When** 用户发起同步任务，**Then** 系统返回错误「云盘地址不存在」
3. **Given** 本地路径不存在，**When** 用户发起同步任务，**Then** 系统自动创建本地目录，完成下载
4. **Given** 下载过程中网络中断，**When** 系统重试（默认10次），**Then** 恢复后继续下载，完成后文件完整
5. **Given** 云盘路径 `/documents/folder/` 是目录，**When** 用户发起同步任务，**Then** 系统下载整个目录（保持目录结构）到本地
6. **Given** 同步任务进行中，**When** 用户查询任务状态，**Then** 系统返回当前进度（已下载大小、总大小、完成百分比）

---

### Edge Cases

- 云盘凭证无效或已过期时，所有操作应返回认证错误，用户可重新配置凭证
- 网络超时（默认 60 秒）时，操作应返回超时错误并标记可重试
- 移动/删除/同步进行中云盘断连，应返回明确错误并保留操作上下文（支持重试）
- 同步目录时包含超大文件（> 10GB），应支持分片下载和断点续传
- 目标路径磁盘空间不足时，同步应提前检测并返回错误
- 并发同步任务数超过限制（默认 5 个并发），系统应返回队列满错误

## Requirements

### Functional Requirements

- **FR-001**: 系统必须支持列出指定云盘的目录内容，路径为空时列出根目录 `/`
- **FR-002**: 系统必须支持查看文件/文件夹的详细元数据（名称、路径、大小、是否目录、修改时间、MIME 类型），路径为空时返回「目录不能为空」错误
- **FR-003**: 系统必须支持移动文件或文件夹到目标地址，目标目录不存在时自动创建；源地址不能为空
- **FR-004**: 系统必须支持删除指定路径的文件或文件夹，根目录 `/` 和空路径不能删除
- **FR-005**: 系统必须支持云下载功能（仅 PikPak），将 URL 列表离线下载到云盘指定目录（默认为 `/My Pack`），其他云盘返回「不支持」
- **FR-006**: 系统必须支持异步同步云盘文件到本地，本地路径不存在时自动创建；云盘路径不存在时返回错误；默认 5 个并发线程、重试 10 次
- **FR-007**: 同步任务应支持查询进度，返回已完成字节数、总字节数、完成百分比
- **FR-008**: 所有操作返回统一格式，包含操作结果或错误码/错误信息
- **FR-009**: 云盘操作应支持超时配置（可通过配置设置，默认 300 秒）

### Key Entities

- **FileInfo**: 云盘文件实体 — 属性：name（文件名）、path（完整路径）、size（字节大小）、is_dir（是否目录）、modified（ISO 8601 修改时间）、mime_type（MIME 类型，可为空）
- **SyncJob**: 同步任务实体 — 属性：job_id（任务ID）、source_path（云盘源路径）、local_path（本地目标路径）、status（pending/running/completed/failed）、progress_bytes（已完成字节数）、total_bytes（总字节数）、created_at（创建时间）
- **CloudDriveConfig**: 云盘配置实体 — 属性：drive_type（云盘类型）、remote_name（rclone remote 名称）、username（认证用户名）、password（加密存储密码）、is_enabled（是否启用）
- **OfflineDownloadTask**: 离线下载任务实体（仅 PikPak）— 属性：task_id、urls（链接列表）、destination_folder（目标云盘目录）、status（pending/running/completed/failed）

## Success Criteria

### Measurable Outcomes

- **SC-001**: 用户可在 5 秒内获取任意云盘根目录的文件列表（100 个以内文件）
- **SC-002**: 移动操作完成后，目标目录立即可见移动后的文件；原位置立即不再存在该文件
- **SC-003**: 删除操作完成后，被删除文件不再出现在任何目录列表中
- **SC-004**: 云下载提交后，5 秒内返回任务 ID，任务在 PikPak 云盘界面可见
- **SC-005**: 同步任务提交后，5 秒内返回任务 ID；下载完成时间取决于网络带宽和云盘接口限速，不做强制时间要求
- **SC-006**: 系统在 5 个并发同步任务下运行稳定，10 次重试内完成率不低于 95%
- **SC-007**: 所有云盘操作的错误信息对用户友好，不出现技术术语或堆栈信息

## Assumptions

- 用户已通过管理接口配置好各云盘凭证（用户名、密码、remote name）
- rclone 已安装在系统 PATH 中且版本 ≥ 1.60
- 本地同步目标路径有足够磁盘空间（同步前系统检测并提前预警）
- 云下载功能仅 PikPak 支持，其他云盘调用时返回明确提示
- 异步同步任务通过任务 ID 轮询查询状态（不依赖 WebSocket 或推送）
- 所有云盘均支持列表、详情、移动、删除基础操作（差异仅在云下载和同步能力上）
