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
| `wps-airscript-agent` | WPS 多维表通用录入与查询（含附件、条件查询、聚合） | 见 `wps-airscript-agent/README.md` |

## 新增 Skill 的维护规则

1. 在仓库根目录新增一个 Skill 子目录（如 `new-skill/`）。
2. 必须包含该 Skill 的独立 `README.md`。
3. 如有敏感信息，提供 `*.example` 模板并把真实配置加入 `.gitignore`。
4. 将该 Skill 增加到本页“Skill 项目清单”。

## 安全与脱敏

- 禁止提交真实 token、webhook、私密路径。
- 统一通过环境变量注入凭据。
- 敏感配置文件仅保留 `*.example` 版本。
