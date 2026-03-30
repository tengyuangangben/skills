# Skills Repository (Agent Skill Collection)

This repository is a **central collection of installable skills** for agents (such as OpenClaw).  
Each skill is maintained in its own folder with an independent `README.md`.

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
| `wps-airscript-agent` | Generic WPS multi-dimensional table integration (create/query/attachments/aggregation) | See `wps-airscript-agent/README.md` |

## Adding a New Skill

1. Create a new folder at repository root (for example: `new-skill/`).
2. Add an independent `README.md` inside that skill folder.
3. Keep secrets out of git; provide `*.example` configs.
4. Update the catalog table in this file.

## Security Guidelines

- Never commit real tokens/webhooks/private paths.
- Use environment variables for credentials.
- Commit only sanitized templates (`*.example`).
