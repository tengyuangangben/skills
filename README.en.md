# WPS AirScript Agent (Publish-Ready)

This repository contains a reusable WPS AirScript skill package for:

- Field discovery (`fields`)
- Record creation (`create`, including attachments)
- Query with conditions (`query`, including contains/range/aggregation)
- Dynamic submitter and submit channel tagging

## What to Publish

Keep only skill-related files in this repo:

- `wps-airscript-agent/SKILL.md`
- `wps-airscript-agent/scripts/wps_skill_router.py`
- `wps-airscript-agent/scripts/wps_skill_init.py`
- `wps-airscript-agent/scripts/录入脚本.js`
- `wps-airscript-agent/scripts/查询脚本.js`
- `wps-airscript-agent/scripts/字段配置查询脚本.js`
- `wps-airscript-agent/wps_webhook_map.example.json`
- `wps-airscript-agent/docs/安装与调用说明.md`
- `README.md`, `README.en.md`, `LICENSE`, `.gitignore`

## Security & Redaction

Before publishing:

1. Do **not** commit real webhook config:
   - keep `wps_webhook_map.json` local only
   - publish only `wps_webhook_map.example.json`
2. Do **not** commit tokens:
   - use environment variable `WPS_AIRSCRIPT_TOKEN`
3. Avoid local absolute paths and personal data in examples.

## Quick Start

1. Create local config from template:
   - `Copy-Item wps-airscript-agent/wps_webhook_map.example.json wps_webhook_map.json`
2. Set env vars:
   - required: `WPS_AIRSCRIPT_TOKEN`
   - optional: `WPS_WEBHOOK_MAP_PATH`, `WPS_SUBMITTER`, `WPS_SUBMIT_CHANNEL`
3. Run:
   - setup check: `WPS_SKILL_MODE=setup`
   - field discovery: `WPS_SKILL_MODE=fields`
   - create/query with `wps_skill_router.py`

## License

Apache-2.0. See `LICENSE`.
