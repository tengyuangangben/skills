# wps-airscript-agent

面向 WPS 多维表的通用 Skill，支持：

- 字段发现（fields）
- 记录录入（create，支持附件）
- 条件查询（contains / 数字范围 / 聚合）
- 动态提交人、动态提交渠道

## 版本信息

- 当前版本：`v1.1.0`
- Release：`https://github.com/tengyuangangben/skills/releases/tag/v1.1.0`

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
- `wps_webhook_map.example.json`：公开配置模板（脱敏）
- `docs/安装与调用说明.md`：完整安装与调用文档

## 安装步骤（最简）

1. 在 WPS 多维表端部署并发布三份脚本（录入/查询/字段配置查询）。
2. 从脚本详情页复制 token 与 webhook。
3. 复制模板配置并填写真实 webhook：
   - `Copy-Item wps_webhook_map.example.json wps_webhook_map.json`
4. 设置环境变量：
   - 必需：`WPS_AIRSCRIPT_TOKEN`
   - 可选：`WPS_WEBHOOK_MAP_PATH`、`WPS_SUBMITTER`、`WPS_SUBMIT_CHANNEL`
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
- 查询参数预览：`WPS_SKILL_MODE=query_argv`
- 查询执行：`WPS_SKILL_MODE=query`

详细参数与示例请查看 `docs/安装与调用说明.md`。

### 补传附件示例（不新增记录）

```powershell
$env:WPS_SKILL_MODE="update_attachment"
$env:WPS_SKILL_INTENT="花名册"
$env:WPS_UPDATE_KEY_FIELD="姓名"
$env:WPS_UPDATE_KEY_VALUE="李附件测试"
$env:WPS_UPDATE_ATTACHMENT_FIELD="相关资料附件"
$env:WPS_UPDATE_ATTACHMENT='{"file_path":"C:\\Users\\sunli\\Downloads\\demo.pdf"}'
python ".\scripts\wps_skill_router.py"
```

说明：

- 该模式会按 `WPS_UPDATE_KEY_FIELD/WPS_UPDATE_KEY_VALUE` 定位已存在记录并更新附件字段。
- 若没有命中记录，将按现有逻辑创建新记录。

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

## 安全说明

- 不要提交真实 token、真实 webhook、个人本地绝对路径。
- 公开仓库仅保留 `wps_webhook_map.example.json`。
