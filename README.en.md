# Skills Repository (Agent Skill Collection)

This repository is a **central collection of installable skills** for agents (such as OpenClaw).  
Each skill is maintained in its own folder with an independent `README.md`.

## Version

- Current stable release: `v1.1.2`
- Latest release page: `https://github.com/tengyuangangben/skills/releases/tag/v1.1.2`
- Change history: `CHANGELOG.md`

## Repository Structure

- Repository-level files:
  - `README.md` (Chinese index)
  - `README.en.md` (English index)
  - `LICENSE`
  - `.gitignore`
- Per-skill folder:
  - `<skill-name>/README.md` (skill-specific docs)
  - `<skill-name>/SKILL.md`
  - `<skill-name>/scripts/*`
  - `<skill-name>/docs/*`
  - `<skill-name>/*.example.*` (public config templates)

## Skill Catalog

| Skill | Summary | Install/Usage |
|---|---|---|
| `wps-airscript-agent` | Generic WPS multi-dimensional table integration (create/query/attachments/aggregation) | See `wps-airscript-agent/README.md` (includes OpenClaw install) |

## Agent Installation (Repository-Level)

### Option A: Clone full skills repository

```bash
git clone https://github.com/tengyuangangben/skills.git
```

Then copy the target skill folder (for example `wps-airscript-agent/`) into your agent's skills directory.

### Option B: Install a single skill via npx

```bash
npx degit tengyuangangben/skills/wps-airscript-agent ./wps-airscript-agent
```

If your agent supports local-folder skill installation, point it to `./wps-airscript-agent`.

### OpenClaw Reference

1. Get `wps-airscript-agent` using Option A or B.
2. Place it under OpenClaw skills folder, for example: `<OPENCLAW_HOME>/skills/wps-airscript-agent`.
3. Restart OpenClaw or reload skills.
4. Enable and invoke the skill inside OpenClaw.

## Upgrade Path

- From `v1.0.0`: upgrade to `v1.1.0`, then to `v1.1.2`
- From `v1.1.0` or `v1.1.1`: upgrade directly to `v1.1.2`
- After upgrading:
  - republish WPS-side `录入脚本.js`
  - run `setup` once for health checks
  - review migration notes in `wps-airscript-agent/README.md`

## Adding a New Skill

1. Create a new folder at repository root (for example: `new-skill/`).
2. Add an independent `README.md` inside that skill folder.
3. Keep secrets out of git; provide `*.example` configs.
4. Update the catalog table in this file.

## Security Guidelines

- Never commit real tokens/webhooks/private paths.
- Use environment variables for credentials.
- Commit only sanitized templates (`*.example`).
