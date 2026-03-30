# WPS AirScript Agent（可发布版）

这是一个可复用的 WPS 多维表对接项目，支持：

- 字段发现（fields）
- 记录录入（create，含附件）
- 条件查询（query，含包含/范围/聚合）
- 动态提交人/提交渠道

## 一、建议上传到 GitHub 的文件

- `wps_skill_router.py`
- `wps_skill_init.py`
- `录入脚本.js`
- `查询脚本.js`
- `字段配置查询脚本.js`
- `.trae/skills/wps-airscript-agent/SKILL.md`
- `WPS_AirScript_Skill_安装与调用说明.md`
- `wps_webhook_map.example.json`
- `README.md`
- `.gitignore`

## 二、不建议直接上传的文件（含敏感或本地测试痕迹）

- `wps_webhook_map.json`（含真实 webhook）
- 任何包含真实 `WPS_AIRSCRIPT_TOKEN` 的文件
- `__pycache__/` 与 `*.pyc`
- 个人本地测试脚本或本地绝对路径文件

## 三、发布前脱敏清单

1. webhook 脱敏：
   - 使用 `wps_webhook_map.example.json` 作为公开模板
   - 本地真实配置放 `wps_webhook_map.json`（已被 `.gitignore` 忽略）
2. token 脱敏：
   - 一律通过环境变量 `WPS_AIRSCRIPT_TOKEN` 注入
   - 不把 token 写入代码和文档
3. 本地路径脱敏：
   - 文档示例避免暴露本机用户名、盘符、业务文件名

## 四、首次运行（开源仓库用户）

1. 复制模板并填写真实 webhook：
   - `Copy-Item wps_webhook_map.example.json wps_webhook_map.json`
2. 设置环境变量：
   - `WPS_AIRSCRIPT_TOKEN`
   - 可选 `WPS_WEBHOOK_MAP_PATH`
   - 可选 `WPS_SUBMITTER`
   - 可选 `WPS_SUBMIT_CHANNEL`
3. 先执行：
   - `WPS_SKILL_MODE=setup`
   - `WPS_SKILL_MODE=fields`

## 五、许可证与安全建议

- 发布前建议加 LICENSE（MIT/Apache-2.0）
- 若怀疑 webhook 或 token 泄露，请立即在 WPS 侧重置令牌并替换 webhook

