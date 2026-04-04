# Skills 仓库（Agent Skill Collection）

这是一个用于 **Agent（如 OpenClaw）安装与使用** 的技能汇总仓库。  
每个 Skill 独立维护在自己的目录中，并提供独立 `README.md` 说明其用途、安装方法与调用方式。

## 版本信息

- 当前稳定版本：`v1.1.2`
- 最新发布页：`https://github.com/tengyuangangben/skills/releases/tag/v1.1.2`
- 版本历史：见 `CHANGELOG.md`

## 升级记录（仓库级）

| 版本 | 说明 |
|---|---|
| v1.1.2 | 修复webhook_map默认路径识别、补传附件追加模式（append）、多消息附件场景适配说明完善 |
| v1.1.1 | 严格字段策略、显式授权新增字段、提交人/渠道动态优先级、安装文档与自动调用策略完善 |
| v1.1.0 | 降低 token 消耗、优化附件兼容、支持补传附件、增强 OpenClaw 调用规则 |
| v1.0.0 | 首个稳定可发布版本 |

## 升级路径（推荐）

- 从 `v1.0.0` 升级：先到 `v1.1.0`，再升级到 `v1.1.2`
- 从 `v1.1.0` 或 `v1.1.1` 升级：直接升级到 `v1.1.2`
- 升级后建议：
  - 重新发布 WPS 端 `录入脚本.js`
  - 使用 `setup` 做一次健康检查
  - 阅读 `wps-airscript-agent/README.md` 中对应版本迁移说明

## 目录结构约定

- 仓库级说明：
  - `README.md`（中文索引）
  - `README.en.md`（英文索引）
  - `LICENSE`
  - `.gitignore`
- Skill 目录（每个 Skill 一个子目录）：
  - `<skill-name>/README.md`（该 Skill 的详细文档）
  - `<skill-name>/SKILL.md`（Skill 规范文件）
  - `<skill-name>/scripts/*`（脚本与路由实现）
  - `<skill-name>/docs/*`（补充文档）
  - `<skill-name>/*.example.*`（公开模板配置）

## Skill 项目清单

| Skill | 简介 | 安装/使用 |
|---|---|---|
| `wps-airscript-agent` | WPS 多维表通用录入与查询（含附件、条件查询、聚合） | 见 `wps-airscript-agent/README.md`（含 OpenClaw 安装与自动调用模板） |

## Agent 安装方式（仓库级）

### 方式 A：克隆整个 skills 仓库（推荐长期维护）

```bash
git clone https://github.com/tengyuangangben/skills.git
```

然后按目标 Agent 的技能目录规范，拷贝某个 Skill 子目录（例如 `wps-airscript-agent/`）到 Agent 的技能目录。

### 方式 B：仅拉取单个 Skill（npx 快速安装）

```bash
npx degit tengyuangangben/skills/wps-airscript-agent ./wps-airscript-agent
```

如果你的 Agent 支持“从本地目录安装 Skill”，可直接选择 `./wps-airscript-agent`。

### OpenClaw 安装参考

1. 获取 Skill 目录（方式 A 或 B）。
2. 将 Skill 目录放入 OpenClaw 的 skills 目录（例如：`<OPENCLAW_HOME>/skills/wps-airscript-agent`）。
3. 重启 OpenClaw 或在管理界面执行技能重载。
4. 在 OpenClaw 内调用该 Skill（具体参数见该 Skill 自身 `README.md`）。

## 新增 Skill 的维护规则

1. 在仓库根目录新增一个 Skill 子目录（如 `new-skill/`）。
2. 必须包含该 Skill 的独立 `README.md`。
3. 如有敏感信息，提供 `*.example` 模板并把真实配置加入 `.gitignore`。
4. 将该 Skill 增加到本页“Skill 项目清单”。

## 安全与脱敏

- 禁止提交真实 token、webhook、私密路径。
- 统一通过环境变量注入凭据。
- 敏感配置文件仅保留 `*.example` 版本。
