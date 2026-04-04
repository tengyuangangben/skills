# wps-airscript-agent

面向 WPS 多维表的通用 Skill，支持：

- 字段发现（fields）
- 记录录入（create，支持附件）
- 条件查询（contains / 数字范围 / 聚合）
- 动态提交人、动态提交渠道

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
- 查询参数预览：`WPS_SKILL_MODE=query_argv`
- 查询执行：`WPS_SKILL_MODE=query`

详细参数与示例请查看 `docs/安装与调用说明.md`。

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

## Token 消耗优化建议

为尽量降低 Agent token 消耗，建议：

- 默认不要返回执行日志（本版已默认裁剪 `data.logs`）。
- 查询优先使用单次返回模式（`selected_fields` / `all_fields`），避免按字段多次查询。
- `WPS_QUERY_RETURN_FIELDS` 仅保留必要字段，避免大字段回传。
- 调用 `query` 时优先使用 `WPS_QUERY_OUTPUT_FORMAT=text`，减少 JSON 冗余。
- 附件上传优先传 `file_path` 或 `file_url`，避免把超长 base64 文本放进对话上下文。

## 安全说明

- 不要提交真实 token、真实 webhook、个人本地绝对路径。
- 公开仓库仅保留 `wps_webhook_map.example.json`。
