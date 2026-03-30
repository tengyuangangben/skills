# wps-airscript-agent

面向 WPS 多维表的通用 Skill，支持：

- 字段发现（fields）
- 记录录入（create，支持附件）
- 条件查询（contains / 数字范围 / 聚合）
- 动态提交人、动态提交渠道

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

## 常用调用

- 录入：`WPS_SKILL_MODE=create`
- 查询参数预览：`WPS_SKILL_MODE=query_argv`
- 查询执行：`WPS_SKILL_MODE=query`

详细参数与示例请查看 `docs/安装与调用说明.md`。

## 安全说明

- 不要提交真实 token、真实 webhook、个人本地绝对路径。
- 公开仓库仅保留 `wps_webhook_map.example.json`。
