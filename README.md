# Skills 仓库（Agent Skill Collection）

这是一个用于 **Agent（如 OpenClaw）安装与使用** 的技能汇总仓库。  
每个 Skill 独立维护在自己的目录中，并提供独立 `README.md` 说明其用途、安装方法与调用方式。

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
| `wps-airscript-agent` | WPS 多维表通用录入与查询（含附件、条件查询、聚合） | 见 `wps-airscript-agent/README.md`（含 OpenClaw 安装） |

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
