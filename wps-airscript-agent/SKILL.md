---
name: wps-airscript-agent
description: 面向WPS多维表的通用录入与查询技能。支持按业务意图自动路由Webhook、动态获取字段并执行录入/查询。
version: v2.0.0
---

# WPS AirScript Agent Skill

## Purpose
将 WPS 多维表的“字段发现、录入、查询”能力封装为可复用技能，支持多业务表统一调用。

## Invoke When
- 用户要求录入某业务表数据（如报销、花名册）
- 用户要求先读取字段列表再引导填报
- 用户要求按配置自动选择对应 webhook
- 用户要求按提交人/部门等范围条件执行查询
- 用户提到“报销/花名册/员工/通讯录”且伴随“新增/录入/查询/统计/汇总/附件/金额”

## Intent Trigger Hints
- 录入触发词：`新增`、`录入`、`登记`、`写入`
- 查询触发词：`查询`、`筛选`、`查看`、`检索`
- 统计触发词：`合计`、`总和`、`平均`、`最大`、`最小`
- 更新触发词：`修改`、`更新`、`更正`、`变更`、`改成`
- 删除触发词：`删除`、`移除`、`作废`、`撤销`、`取消这条`、`回滚`
- 附件触发词：`上传附件`、`pdf`、`图片`、`文件`
- 业务触发词：
  - `报销|报销登记|报销表|日记账` → `reimbursement`
  - `花名册|人员|员工|通讯录` → `employee_roster`

## Required Files
- 路由配置文件（Skill 内）：`wps_webhook_map.json`
- 路由脚本入口（必须调用 Skill 内脚本）：`scripts/wps_skill_router.py`
- 交互初始化脚本：`scripts/wps_skill_init.py`
- WPS 端录入脚本：`scripts/录入脚本.js`
- WPS 端查询脚本：`scripts/查询脚本.js`
- WPS 端字段配置查询脚本：`scripts/字段配置查询脚本.js`
- 规则：仅使用当前 Skill 目录内相对路径，禁止引用项目根目录绝对路径

## First-Run Setup
1. 在本地设置环境变量（全局仅需一次）：
   - 可选：`WPS_AIRSCRIPT_TOKEN`：WPS 脚本令牌（当 `wps_webhook_map.json` 未配置 `token` 时使用）
   - 可选：`WPS_WEBHOOK_MAP_PATH`：路由配置文件路径（建议显式设为 `./wps_webhook_map.json`）
   - 可选：`WPS_SUBMITTER`：默认提交人
   - 可选：`WPS_SUBMIT_CHANNEL`：默认提交渠道（如 `telegram|feishu|whatsapp`）
   - 令牌获取路径：进入任意脚本编辑器 → 点击“脚本令牌” → 创建/复制令牌 → 写入环境变量
   - 若未设置 `WPS_WEBHOOK_MAP_PATH`，脚本会按顺序自动查找：
     1) `scripts/wps_webhook_map.json`
     2) `wps_webhook_map.json`（Skill 根目录）
     3) 当前工作目录 `wps_webhook_map.json`
   - 若 OpenClaw 运行目录不稳定，建议总是显式设置：`WPS_WEBHOOK_MAP_PATH=./wps_webhook_map.json`
2. 在 `wps_webhook_map.json` 中为每个业务路由填写：
   - 可选顶层：`token`（优先于环境变量 `WPS_AIRSCRIPT_TOKEN`）
   - `write_webhook`：录入脚本 webhook
   - `delete_webhook`：删除脚本 webhook
   - `query_webhook`：查询脚本 webhook
   - `field_query_webhook`：字段配置查询脚本 webhook
   - 可选：`request_id_field_name`（默认 `_请求ID`）
   - `default_notification_mode`：默认通知模式（`text|image|file|dashboard_link`）
   - `default_range_mode`：默认范围模式（`all|user|group|both`）
   - `range_filter_fields`：范围筛选字段名映射（`user_field_name/group_field_name`）
   - 可选使用交互式脚本自动填写：`python ./scripts/wps_skill_init.py`
3. 在目标多维表中分别创建并保存四个脚本（录入/查询/字段配置查询/删除），发布后复制各自 webhook。

## WPS-Side Deployment Guide
1. 打开目标多维表 → 自动化/脚本（AirScript）→ 新建脚本。
2. 在“添加服务”中开启 API 服务：
   - 必开：`云文档API`
   - 建议开：`网络API`
   - 不必开：`邮件API`
   - 最小可运行集合：`云文档API`
3. 分别粘贴并保存以下脚本内容：
   - `录入脚本.js`
   - `查询脚本.js`
   - `字段配置查询脚本.js`
   - `删除脚本.js`
4. 在脚本详情页获取：
   - 脚本令牌（Token）
   - 脚本 webhook（每个脚本一条）
5. 获取表名称：
   - 使用多维表顶部标题的可见名称，写入路由配置的 `sheet_name`。

## Operating Workflow
1. **识别业务意图**：根据用户输入匹配 `routes.aliases/name/key`。
2. **发现字段**：调用 `get_required_fields(intent)`，返回字段清单、类型、说明与可选项。
3. **引导填报**：按字段清单收集用户值，仅收集业务字段。
4. **执行录入**：调用 `create_record(intent, user_data, submitter)`。
5. **执行更新**（可选）：
   - 按关键字段更新：调用 `update_record_fields(...)` 并提供 `key_field/key_value/update_data`
6. **执行删除**（可选）：
   - 按条件删除：调用 `delete_records(...)` 并提供 `delete_field_name/delete_field_value`
   - 撤销当次录入：调用 `delete_records(...)` 并提供 `request_id`
7. **执行查询**（可选）：
   - 使用 `build_query_argv(...)` 构造查询参数
   - 或直接调用 `query_records(...)` 通过 `query_webhook` 获取结果

## Call Contracts
### 获取字段
- 函数：`get_required_fields(intent)`
- 入参：
  - `intent`：业务意图关键词（如“报销”“花名册”）
- 出参包含：
  - `route`
  - `sheet_name`
  - `recommended_range_mode`
  - `range_filter_fields`
  - `fields[{name,type,format,required,is_primary,options,description}]`

### 录入数据
- 函数：`create_record(intent, user_data, submitter="", submit_channel="")`
- 关键约束（OpenClaw 调用必须遵守）：
  - `submitter` 与 `submit_channel` 视为必传参数，必须显式传入本次会话来源值。
  - 禁止省略 `submit_channel`，否则可能回落默认渠道（如 `wecom`）。
  - submitter 可优先从 `OPENCLAW_SUBMITTER/OPENCLAW_USER/OPENCLAW_USERNAME` 获取；缺失时可从 `OPENCLAW_CONTEXT` 的 `user/sender/requester` 提取。
  - 默认强制二次确认提交：`WPS_REQUIRE_CONFIRM_SUBMIT=true`（用户未明确“确认提交”不得写入）。
  - 默认禁止附件OCR内容写入：`WPS_FORBID_ATTACHMENT_OCR_BY_DEFAULT=true`（仅明确授权时放开）。
  - 建议开启强校验：`WPS_REQUIRE_SUBMIT_CHANNEL=true` 且 `WPS_REQUIRE_SUBMITTER=true`。
  - 上述开关支持放入 `wps_webhook_map.json` 顶层 `config`（`require_submit_channel/require_submitter/require_confirm_submit/forbid_attachment_ocr_by_default`）。
- 入参：
  - `intent`：业务意图
  - `user_data`：`{字段名: 值}`
  - `submitter`：提交人标识（OpenClaw 必传）
  - `submit_channel`：提交渠道（OpenClaw 必传，可传 `telegram`/`feishu`/`whatsapp` 等）
- 行为：
  - 自动读取字段类型并映射 `field_format`
  - 自动生成 `request_id`
  - 自动调用目标 `write_webhook`

### 补传附件到已存在记录
- 函数：`update_attachment_record(intent, key_field, key_value, attachment_field, attachment_value)`
- 用途：
  - 第一次忘记传附件时，在后续会话中补传到同一条记录
- 环境变量模式：
  - `WPS_SKILL_MODE=update_attachment`
  - `WPS_UPDATE_KEY_FIELD`
  - `WPS_UPDATE_KEY_VALUE`
  - `WPS_UPDATE_ATTACHMENT_FIELD`
  - `WPS_UPDATE_ATTACHMENT`（JSON）
  - `WPS_UPDATE_ATTACHMENT_MODE=append|replace`（默认 `replace`，多消息补附件建议 `append`）

### 更新已有记录字段（非附件）
- 函数：`update_record_fields(intent, key_field, key_value, update_data, must_exist=True)`
- 用途：
  - 按关键字段定位单条或多条记录并更新普通字段值
- 环境变量模式：
  - `WPS_SKILL_MODE=update`
  - `WPS_UPDATE_KEY_FIELD`
  - `WPS_UPDATE_KEY_VALUE`
  - `WPS_UPDATE_FIELDS_JSON`（JSON）
  - `WPS_UPDATE_MUST_EXIST=true|false`（默认 `true`）

### 删除记录
- 函数：`delete_records(intent, delete_field_name="", delete_field_value="", delete_field_rule="等于", query_conditions=[], request_id="", record_ids=[], max_delete_count=200)`
- 用途：
  - 按字段条件删除记录
  - 按 `request_id` 撤销当次录入
  - 按 `record_ids` 精确删除
- 环境变量模式：
  - `WPS_SKILL_MODE=delete`
  - `WPS_DELETE_FIELD` / `WPS_DELETE_VALUE` / `WPS_DELETE_RULE`
  - 当 `WPS_DELETE_RULE=为空/不为空` 时，`WPS_DELETE_VALUE` 可留空
  - `WPS_DELETE_CONDITIONS_JSON`（可选）
  - `WPS_DELETE_REQUEST_ID`（可选）
  - `WPS_DELETE_RECORD_IDS_JSON`（可选）
  - `WPS_DELETE_MAX_COUNT`（默认 `200`）

### 构造查询参数
- 函数：`build_query_argv(intent, monitor_field_name, monitor_content, requester_user_value="", requester_group_value="", notification_field_name="", range_mode="", check_field_rule="等于", return_mode="notification", return_fields=[], query_conditions=[], aggregate={})`
- 关键输出：
  - `range_mode`：`all|user|group|both`
  - `notification_mode`：`text|image|file|dashboard_link`
  - `range_filter_fields`：范围字段映射
  - `return_mode`：`notification|selected_fields|all_fields`
  - `query_conditions`：支持包含关系和数字范围关系
  - `aggregate`：支持 `sum|avg|min|max|count`

### 执行查询
- 函数：`query_records_enhanced(intent, monitor_field_name, monitor_content, requester_user_value="", requester_group_value="", notification_field_name="", range_mode="", check_field_rule="等于", return_mode="notification", return_fields=[], query_conditions=[], aggregate={}, include_attachment_fields=False)`
- 依赖：
  - 路由内已配置 `query_webhook`

## Agent Behavior Rules
- 首次调用必须先检查：
  - `WPS_AIRSCRIPT_TOKEN` 是否存在
  - 路由是否存在并已配置 webhook
- 录入前必须先执行字段发现，避免字段名漂移导致失败。
- 录入前预校验：
  - 单选/多选字段值必须命中 `fields.options`
  - 新增模式下必填字段不可缺失
- 查询调用优先使用机器枚举参数：
  - `range_mode` 代替旧 `data_range_condition`
  - `notification_mode` 代替旧 `notification_type`
- 若 webhook 或 token 缺失，返回明确的缺失项清单，不进行盲调用。
- 若命中触发词，禁止只做自然语言回答，必须优先调用本 Skill 完成操作。
- 录入场景采用“强制交互式提交”：
  - 用户只要进入录入场景，一律先进入草稿收集态，不立即写入。
  - 每轮收集后必须询问“是否已完整，若完整请回复确认提交”。
  - 仅当用户明确回复“确认提交/提交/完成”时，才一次性调用 create 写入全部内容，并传 `_confirm_submit=true`。
- 录入时先按 `fields` 做字段匹配与补问：
  - 用户输入字段未命中字段清单时先澄清，不直接写入。
  - 若字段清单存在附件字段，提交前需确认附件是否已收齐。
- 删除场景必须二次确认：
  - 条件删除需复述删除条件给用户确认后再调用 `delete_records`。
  - 撤销当次录入优先使用 `request_id`，减少误删范围。
- 收集态下附件按“追加”语义聚合，不得因逐消息处理覆盖前序附件。
- 附件处理默认直传：
  - 用户发附件时默认直接上传，不做附件内容识别（强制）。
  - 用户未明确提出识别需求时，禁止主动做 OCR/解析/摘要。
  - 仅当用户明确要求“识别附件内容/提取附件内容/OCR附件”时，才进入附件识别流程，并传 `_allow_attachment_ocr=true`。
- 低 token 模式建议：
  - 附件优先使用 `file_path` 或 `file_url`，避免把大段 `file_data` 放入对话。
  - 查询优先 `return_mode=selected_fields` 且 `WPS_QUERY_OUTPUT_FORMAT=text`。
  - 非排障场景保持 `WPS_KEEP_AIRSCRIPT_LOGS=false`。
- 提交人/提交渠道写入优先级：
  - 显式参数 > OpenClaw运行时环境变量 > `WPS_SKILL_DATA` 元数据 > `WPS_SUBMITTER/WPS_SUBMIT_CHANNEL` > 默认值
- 提交人/提交渠道传参规则（强制）：
  - OpenClaw 每次调用 `create/update/update_attachment/delete` 都必须显式传入来源用户与来源渠道。
  - 若渠道缺失，禁止直接提交；应先向用户确认渠道或从会话上下文重取后再调用。
  - 建议在运行环境启用：`WPS_REQUIRE_SUBMIT_CHANNEL=true`，缺失渠道时直接报错而不是回落默认值。
- 字段约束：
  - 仅按表内已有字段写入
  - 仅 `_请求ID`、`_提交人`、`_提交渠道` 允许自动创建
  - 仅当用户明确要求新增字段时，才允许开启 `WPS_ALLOW_NEW_FIELDS=true` 且 `WPS_ALLOW_NEW_FIELDS_REQUESTED=true`（必须配 `WPS_NEW_FIELDS_WHITELIST`）

## Troubleshooting
- 返回“未匹配到业务路由”：
  - 检查 `routes.aliases/name/key` 是否覆盖用户表达。
- 返回“未配置 webhook”：
  - 在 `wps_webhook_map.json` 填写对应业务路由 webhook。
- 返回“未返回字段配置”：
  - 检查字段配置查询脚本是否已发布并绑定到正确表名。
- `field_query_webhook` 的 `raw_fields` 中文乱码但 `query_webhook` 正常：
  - 更新到最新 `scripts/wps_skill_router.py`，已内置响应字节级解码兼容（Windows场景）。
- OpenClaw 经常不自动调用：
  - 使用 `docs/OpenClaw_自动调用策略模板.md` 作为系统提示词补丁，强化触发词和决策树。
