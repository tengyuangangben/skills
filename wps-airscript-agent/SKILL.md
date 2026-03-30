---
name: wps-airscript-agent
description: 面向WPS多维表的通用录入与查询技能。支持按业务意图自动路由Webhook、动态获取字段并执行录入/查询。
---

# WPS AirScript Agent Skill

## Purpose
将 WPS 多维表的“字段发现、录入、查询”能力封装为可复用技能，支持多业务表统一调用。

## Invoke When
- 用户要求录入某业务表数据（如报销、花名册）
- 用户要求先读取字段列表再引导填报
- 用户要求按配置自动选择对应 webhook
- 用户要求按提交人/部门等范围条件执行查询

## Required Files
- 路由配置文件：`d:\custome_development\wps多维表对接程序\wps_webhook_map.json`
- 外部路由脚本：`d:\custome_development\wps多维表对接程序\wps_skill_router.py`
- 交互初始化脚本：`d:\custome_development\wps多维表对接程序\wps_skill_init.py`
- WPS 端录入脚本：`d:\custome_development\wps多维表对接程序\录入脚本.js`
- WPS 端查询脚本：`d:\custome_development\wps多维表对接程序\查询脚本.js`
- WPS 端字段配置查询脚本：`d:\custome_development\wps多维表对接程序\字段配置查询脚本.js`

## First-Run Setup
1. 在本地设置环境变量（全局仅需一次）：
   - `WPS_AIRSCRIPT_TOKEN`：WPS 脚本令牌
   - 可选：`WPS_WEBHOOK_MAP_PATH`：路由配置文件路径（默认读取项目内 `wps_webhook_map.json`）
   - 可选：`WPS_SUBMITTER`：默认提交人
   - 可选：`WPS_SUBMIT_CHANNEL`：默认提交渠道（如 `telegram|feishu|whatsapp`）
   - 令牌获取路径：进入任意脚本编辑器 → 点击“脚本令牌” → 创建/复制令牌 → 写入环境变量
2. 在 `wps_webhook_map.json` 中为每个业务路由填写：
   - `write_webhook`：录入脚本 webhook
   - `query_webhook`：查询脚本 webhook
   - `field_query_webhook`：字段配置查询脚本 webhook
   - `default_notification_mode`：默认通知模式（`text|image|file|dashboard_link`）
   - `default_range_mode`：默认范围模式（`all|user|group|both`）
   - `range_filter_fields`：范围筛选字段名映射（`user_field_name/group_field_name`）
   - 可选使用交互式脚本自动填写：`python d:\custome_development\wps多维表对接程序\wps_skill_init.py`
3. 在目标多维表中分别创建并保存三个脚本（录入/查询/字段配置查询），发布后复制各自 webhook。

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
4. 在脚本详情页获取：
   - 脚本令牌（Token）
   - 脚本 webhook（每个脚本一条）
5. 获取表名称：
   - 使用多维表顶部标题的可见名称，写入路由配置的 `sheet_name`。

## Operating Workflow
1. **识别业务意图**：根据用户输入匹配 `routes.aliases/name/key`。
2. **发现字段**：调用 `get_required_fields(intent)`，返回字段清单与类型。
3. **引导填报**：按字段清单收集用户值，仅收集业务字段。
4. **执行录入**：调用 `create_record(intent, user_data, submitter)`。
5. **执行查询**（可选）：
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
  - `fields[{name,type}]`

### 录入数据
- 函数：`create_record(intent, user_data, submitter="", submit_channel="")`
- 入参：
  - `intent`：业务意图
  - `user_data`：`{字段名: 值}`
  - `submitter`：提交人标识
  - `submit_channel`：提交渠道（可传 `telegram`/`feishu`/`whatsapp` 等）
- 行为：
  - 自动读取字段类型并映射 `field_format`
  - 自动生成 `request_id`
  - 自动调用目标 `write_webhook`

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
- 查询调用优先使用机器枚举参数：
  - `range_mode` 代替旧 `data_range_condition`
  - `notification_mode` 代替旧 `notification_type`
- 若 webhook 或 token 缺失，返回明确的缺失项清单，不进行盲调用。

## Troubleshooting
- 返回“未匹配到业务路由”：
  - 检查 `routes.aliases/name/key` 是否覆盖用户表达。
- 返回“未配置 webhook”：
  - 在 `wps_webhook_map.json` 填写对应业务路由 webhook。
- 返回“未返回字段配置”：
  - 检查字段配置查询脚本是否已发布并绑定到正确表名。
