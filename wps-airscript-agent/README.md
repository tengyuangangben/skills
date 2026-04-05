# wps-airscript-agent

面向 WPS 多维表的通用 Skill，支持：

- 字段发现（fields）
- 记录录入（create，支持附件）
- 条件查询（contains / 数字范围 / 聚合）
- 动态提交人、动态提交渠道

## 版本信息

- 当前版本：`v2.0.0`
- Release：`https://github.com/tengyuangangben/skills/releases/tag/v2.0.0`
- 版本历史：`../../CHANGELOG.md`

## 从 v1.0.0 升级到 v1.1.0

1. 更新 Skill 目录下文件（重点是 `scripts/wps_skill_router.py` 与 `scripts/录入脚本.js`）。
2. 将新版 `录入脚本.js` 重新发布到 WPS 多维表脚本端。
3. 保持原有环境变量不变即可运行；如需排障日志可设置：
   - `WPS_KEEP_AIRSCRIPT_LOGS=true`

升级收益：

- 默认裁剪执行日志，减少 token 消耗。
- 查询优先单次返回，减少多次 webhook 调用。
- 附件上传兼容性更强（避免灰色问号）。
- 新增 `update_attachment`，支持已存在记录补传附件。

## 从 v1.1.0 升级到 v1.1.1

1. 更新 `scripts/wps_skill_router.py`、`scripts/录入脚本.js` 与 `docs/安装与调用说明.md`。
2. 将新版 `录入脚本.js` 重新发布到 WPS 多维表脚本端。
3. 若需新增业务字段，必须显式设置：
   - `WPS_ALLOW_NEW_FIELDS=true`
   - 可选 `WPS_NEW_FIELDS_WHITELIST=字段A,字段B`

升级收益：

- 默认严格字段写入，避免误新增字段污染表结构。
- 提交人/提交渠道优先采用运行时真实来源。
- OpenClaw 自动调用策略补充“新增字段需用户明确授权”规则。

## 从 v1.1.1 升级到 v1.1.2

1. 更新 `scripts/wps_skill_router.py` 与 `docs/安装与调用说明.md`。
2. 若你在 OpenClaw 中不设置 `WPS_WEBHOOK_MAP_PATH`，可直接使用 skill 根目录下的 `wps_webhook_map.json`（已支持自动发现）。
3. 多消息补附件场景建议设置：
   - `WPS_UPDATE_ATTACHMENT_MODE=append`

升级收益：

- `wps_webhook_map.json` 默认路径识别更稳，不再必须手动传路径。
- `update_attachment` 支持 append 合并，避免多消息附件后写覆盖前写。

## 从 v1.1.2 升级到 v2.0.0

1. 更新 `scripts/wps_skill_router.py`、`wps_webhook_map.example.json`、`docs/安装与调用说明.md`。
2. 将 `wps_webhook_map.json` 顶层补充 `config` 开关（可替代环境变量）：
   - `require_submit_channel`
   - `require_submitter`
   - `require_confirm_submit`
   - `forbid_attachment_ocr_by_default`
3. 建议将 `require_submit_channel` 与 `require_submitter` 设为 `true`，避免回落默认提交人/渠道。

升级收益：

- 删除流程改为先查询ID再删除，规避WPS端记录对象差异导致的ID类型异常。
- `update_attachment/update` 透传 `submitter/submit_channel`，来源归因更稳定。
- 关键安全开关支持配置文件集中管理，用户可控性更高。

## 给 Agent 的安装指引（重点）

该目录本身就是一个可安装 Skill 包。  
Agent（如 OpenClaw）需要的是这个目录里的 `SKILL.md` 与脚本文件，而不是仅复制单个文件。

### 安装方式 1：从 skills 仓库克隆

```bash
git clone https://github.com/tengyuangangben/skills.git
```

将 `skills/wps-airscript-agent` 目录拷贝到你的 Agent 技能目录。

### 安装方式 2：仅下载本 Skill（npx）

```bash
npx degit tengyuangangben/skills/wps-airscript-agent ./wps-airscript-agent
```

将下载后的 `./wps-airscript-agent` 放入 Agent 技能目录即可。

### OpenClaw 参考安装步骤

1. 获取 `wps-airscript-agent` 目录（用上面任一方式）。
2. 放置到 OpenClaw 技能目录，例如：`<OPENCLAW_HOME>/skills/wps-airscript-agent`。
3. 重启 OpenClaw 或执行技能重载。
4. 在 OpenClaw 中启用并调用该 Skill。

## 目录说明

- `SKILL.md`：Skill 规范与行为约定
- `scripts/wps_skill_router.py`：外部路由与调用入口
- `scripts/wps_skill_init.py`：交互式初始化工具
- `scripts/录入脚本.js`：WPS 端录入脚本
- `scripts/查询脚本.js`：WPS 端查询脚本
- `scripts/字段配置查询脚本.js`：WPS 端字段发现脚本
- `scripts/删除脚本.js`：WPS 端删除脚本
- `wps_webhook_map.example.json`：公开配置模板（脱敏）
- `docs/安装与调用说明.md`：完整安装与调用文档

## 安装步骤（最简）

1. 在 WPS 多维表端部署并发布四份脚本（录入/查询/字段配置查询/删除）。
2. 从脚本详情页复制 token 与 webhook。
3. 复制模板配置并填写真实 webhook：
   - `Copy-Item wps_webhook_map.example.json wps_webhook_map.json`
   - 可选在配置顶层填写 `token`（优先于环境变量）
4. 设置环境变量：
   - 可选：`WPS_AIRSCRIPT_TOKEN`（当 `wps_webhook_map.json` 未配置 `token` 时使用）
   - 可选：`WPS_WEBHOOK_MAP_PATH`、`WPS_SUBMITTER`、`WPS_SUBMIT_CHANNEL`
   - 若不设置 `WPS_WEBHOOK_MAP_PATH`，脚本会按顺序自动查找：
     1) `scripts/wps_webhook_map.json`
     2) Skill 根目录 `wps_webhook_map.json`
     3) 当前工作目录 `wps_webhook_map.json`
5. 运行健康检查与字段发现：
   - `WPS_SKILL_MODE=setup`
   - `WPS_SKILL_MODE=fields`

### 环境变量示例（PowerShell）

```powershell
$env:WPS_AIRSCRIPT_TOKEN="你的脚本令牌"
$env:WPS_WEBHOOK_MAP_PATH="D:\path\to\wps_webhook_map.json"
$env:WPS_SUBMITTER="agent_user"
$env:WPS_SUBMIT_CHANNEL="telegram"
```

## 常用调用

- 录入：`WPS_SKILL_MODE=create`
- 补传附件到已存在记录：`WPS_SKILL_MODE=update_attachment`
- 更新已有记录字段：`WPS_SKILL_MODE=update`
- 查询参数预览：`WPS_SKILL_MODE=query_argv`
- 查询执行：`WPS_SKILL_MODE=query`

详细参数与示例请查看 `docs/安装与调用说明.md`。

### 提交人/提交渠道来源优先级

为保证写入“实际渠道/实际用户”，当前优先级如下（从高到低）：

1. 显式入参（`submitter` / `submit_channel`）
2. OpenClaw/聊天运行时环境变量（如 `OPENCLAW_CHANNEL`、`OPENCLAW_CHAT_CHANNEL`、`REQUEST_CHANNEL`）
3. `WPS_SKILL_DATA` 中的元数据（如 `submitter`、`submit_channel`、`_提交人`、`_提交渠道`）
4. 兜底环境变量（`WPS_SUBMITTER` / `WPS_SUBMIT_CHANNEL`）
5. 最终兜底（提交人=`agent`，提交渠道默认 `wecom`）

OpenClaw 调用强制要求：

- 每次 `create/update/update_attachment/delete` 都必须显式传 `submitter` 与 `submit_channel`。
- 禁止省略 `submit_channel`，否则可能回落到默认渠道（`wecom`）。
- 建议启用强校验：
  - `WPS_REQUIRE_SUBMIT_CHANNEL=true`
  - 建议同时开启：`WPS_REQUIRE_SUBMITTER=true`
  - `WPS_REQUIRE_CONFIRM_SUBMIT=true`
  - `WPS_FORBID_ATTACHMENT_OCR_BY_DEFAULT=true`

上述开关也可放到 `wps_webhook_map.json` 顶层 `config`：

- `require_submit_channel`
- `require_submitter`
- `require_confirm_submit`
- `forbid_attachment_ocr_by_default`

可选覆盖最终兜底渠道：

- 环境变量：`WPS_FALLBACK_SUBMIT_CHANNEL`
- 路由级配置：`default_submit_channel`

### 删除记录示例（按条件/撤销）

```powershell
$env:WPS_SKILL_MODE="delete"
$env:WPS_SKILL_INTENT="花名册"
$env:WPS_DELETE_FIELD="姓名"
$env:WPS_DELETE_VALUE="李附件测试"
$env:WPS_DELETE_RULE="等于"
python ".\scripts\wps_skill_router.py"
```

空值删除示例：

```powershell
$env:WPS_SKILL_MODE="delete"
$env:WPS_SKILL_INTENT="花名册"
$env:WPS_DELETE_FIELD="客户姓名"
$env:WPS_DELETE_RULE="为空"
python ".\scripts\wps_skill_router.py"
```

### 更新记录示例（修改字段内容）

```powershell
$env:WPS_SKILL_MODE="update"
$env:WPS_SKILL_INTENT="花名册"
$env:WPS_UPDATE_KEY_FIELD="姓名"
$env:WPS_UPDATE_KEY_VALUE="李附件测试"
$env:WPS_UPDATE_FIELDS_JSON='{"联系电话":"13800001111","客户状态":"活跃"}'
$env:WPS_UPDATE_MUST_EXIST="true"
python ".\scripts\wps_skill_router.py"
```

撤销当次录入（按请求ID）：

```powershell
$env:WPS_SKILL_MODE="delete"
$env:WPS_SKILL_INTENT="花名册"
$env:WPS_DELETE_REQUEST_ID="employee_roster-ab12cd34"
python ".\scripts\wps_skill_router.py"
```

### 补传附件示例（不新增记录）

```powershell
$env:WPS_SKILL_MODE="update_attachment"
$env:WPS_SKILL_INTENT="花名册"
$env:WPS_UPDATE_KEY_FIELD="姓名"
$env:WPS_UPDATE_KEY_VALUE="李附件测试"
$env:WPS_UPDATE_ATTACHMENT_FIELD="相关资料附件"
$env:WPS_UPDATE_ATTACHMENT_MODE="append"
$env:WPS_UPDATE_ATTACHMENT='{"file_path":"C:\\Users\\sunli\\Downloads\\demo.pdf"}'
python ".\scripts\wps_skill_router.py"
```

说明：

- 该模式会按 `WPS_UPDATE_KEY_FIELD/WPS_UPDATE_KEY_VALUE` 定位已存在记录并更新附件字段。
- `WPS_UPDATE_ATTACHMENT_MODE=append` 时会先读取已有附件并追加写入，避免覆盖。
- 若没有命中记录，将按现有逻辑创建新记录。
- 默认 `create` 模式不会自动关联“上一轮新增的记录”，所以“分两次对话先新增后补附件”应使用 `update_attachment` 或开启覆盖模式并提供主键。

### 覆盖模式（可用于补写同一条记录）

```powershell
$env:WPS_SKILL_MODE="create"
$env:WPS_OVERWRITE_MODE="true"
$env:WPS_KEY_FIELD="姓名"
$env:WPS_KEY_VALUE="李附件测试"
$env:WPS_SKILL_DATA='{"相关资料附件":{"file_path":"C:\\Users\\sunli\\Downloads\\demo.pdf"}}'
python ".\scripts\wps_skill_router.py"
```

## 附件字段入参规范（OpenClaw 推荐）

为避免 WPS 里附件出现灰色问号，建议优先传“带后缀文件名 + 正确数据格式”：

```json
{
  "相关资料附件": {
    "file_data": "<base64字符串或data URI>",
    "file_name": "示例.pdf"
  }
}
```

也支持以下形式：

- 本地路径：`{"file_path":"D:\\a\\b\\c.pdf"}`
- 多文件：`{"file_paths":["D:\\a.png","D:\\b.pdf"]}`
- 远程URL：`{"file_url":"https://example.com/a.pdf","file_name":"a.pdf"}`
- 列表混合：`{"files":[{"file_url":"..."},{"file_path":"..."}]}`

注意：

- `file_name` 建议带扩展名（如 `.pdf` / `.png`）。
- 若传入纯 base64（不含 `data:mime;base64,` 前缀），路由会按 `file_name` 推断 MIME 并自动补全。

### OpenClaw 低 Token 附件策略模板

建议在 OpenClaw 的提示词或工具编排层加如下规则：

1. 禁止把附件原始内容（base64大文本）直接拼进用户对话上下文。
2. 优先传 `file_path` 或 `file_url`。
3. 仅在无法获取路径/链接时才传 `file_data`，且必须带 `file_name`。
4. 默认不做附件内容识别（强制）；仅当用户明确提出“识别附件内容/提取附件内容/OCR附件”时才触发识别流程。
5. 建议启用：`WPS_FORBID_ATTACHMENT_OCR_BY_DEFAULT=true`，未明确授权时拒绝OCR结果写入。

推荐输出给 Skill 的附件参数模板：

```json
{
  "相关资料附件": {
    "files": [
      {"file_path": "D:\\docs\\a.pdf"},
      {"file_url": "https://example.com/b.png", "file_name": "b.png"}
    ]
  }
}
```

## Token 消耗优化建议

为尽量降低 Agent token 消耗，建议：

- 默认不要返回执行日志（本版已默认裁剪 `data.logs`）。
- 查询优先使用单次返回模式（`selected_fields` / `all_fields`），避免按字段多次查询。
- `WPS_QUERY_RETURN_FIELDS` 仅保留必要字段，避免大字段回传。
- 调用 `query` 时优先使用 `WPS_QUERY_OUTPUT_FORMAT=text`，减少 JSON 冗余。
- 附件上传优先传 `file_path` 或 `file_url`，避免把超长 base64 文本放进对话上下文。

## 意图识别与自动调用（OpenClaw）

为降低“识别不到意图导致不调用 Skill”的概率，建议在 OpenClaw 的系统提示词中加入：

- 用户提到以下任一关键词时，优先调用 `wps-airscript-agent`：
  - 业务词：`报销`、`花名册`、`员工`、`通讯录`
  - 动作词：`录入`、`新增`、`登记`、`查询`、`统计`、`汇总`
  - 字段词：`金额`、`状态`、`附件`、`平均值`、`总和`
- 若用户意图是“写入数据”，先走 `fields` 再走 `create`。
- 若用户意图是“查数据/统计”，直接走 `query`，并尽量设置：
  - `WPS_QUERY_RETURN_MODE=selected_fields`
  - `WPS_QUERY_OUTPUT_FORMAT=text`
- 当路由不明确时，先调用 `setup` 并根据 `routes` 做二次匹配，不要直接放弃。

可直接使用模板文件：

- `docs/OpenClaw_自动调用策略模板.md`

推荐开启“强制交互式确认提交”：

- 只要用户进入录入场景，一律先进入草稿收集态，不立即写入
- 每轮收集后都询问用户是否已提供完整；仅当用户回复“确认提交/提交/完成”才一次性写入
- create 调用时显式传 `_confirm_submit=true`；未确认提交时不要调用 create
- 这样可避免多轮消息导致字段遗漏、附件覆盖、误提交

录入前预校验（已内置）：

- 单选字段会校验值是否在 `options` 内
- 多选字段会校验每个值是否在 `options` 内
- 新增模式下会校验必填字段是否缺失

## 安全说明

- 不要提交真实 token、真实 webhook、个人本地绝对路径。
- 公开仓库仅保留 `wps_webhook_map.example.json`。

## 字段写入约束（重要）

- 录入时仅允许按目标表**已有字段**写入。
- 仅以下系统字段允许自动创建：
  - `_请求ID`
  - `_提交人`
  - `_提交渠道`
- 其余不存在字段会直接返回失败，不会自动新增，避免污染表结构。
- 如用户明确要求“新增字段”时，可显式开启：
  - `WPS_ALLOW_NEW_FIELDS=true`
  - `WPS_ALLOW_NEW_FIELDS_REQUESTED=true`
  - `WPS_NEW_FIELDS_WHITELIST=字段A,字段B`
