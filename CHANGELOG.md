# Changelog

All notable changes to this repository are documented in this file.

## [v2.0.0] - 2026-04-05

### Added
- Config-level safety switches in `wps_webhook_map.json` top-level `config`:
  - `require_submit_channel`
  - `require_submitter`
  - `require_confirm_submit`
  - `forbid_attachment_ocr_by_default`
- Example config now includes inline explanatory comment fields for each switch.

### Changed
- Delete-by-condition flow now resolves matched record IDs via query path first, then calls delete with normalized string IDs.
- `update_attachment` and `update` flows now support explicit `submitter/submit_channel` pass-through.
- Field config parsing is more tolerant of alternative field keys (`field_name/label/fieldType/data_type`).

### Fixed
- Prevented submitter/channel regressions in update flows that could fallback to defaults.
- Hardened record-id normalization for mixed object/string id shapes.
- Improved Windows-side response decoding stability for field-query payloads.

## [v1.1.2] - 2026-04-04

### Added
- Attachment append mode for multi-message uploads: `WPS_UPDATE_ATTACHMENT_MODE=append`.
- Setup output now includes resolved webhook map path and existence status.
- Delete capability: `WPS_SKILL_MODE=delete` with condition/request-id/record-id pathways.
- New delete AirScript file: `scripts/删除脚本.js`.
- Router initializer now supports `delete_webhook` and `request_id_field_name`.

### Changed
- Webhook map path resolution now auto-detects in this order when env is unset:
  - `scripts/wps_webhook_map.json`
  - skill root `wps_webhook_map.json`
  - current working directory `wps_webhook_map.json`
- Token resolution now prefers `wps_webhook_map.json` top-level `token`, then falls back to `WPS_AIRSCRIPT_TOKEN`.
- Submit channel priority now prefers OpenClaw runtime channel context over payload/default env fallback.

### Fixed
- OpenClaw runtime no longer requires explicit `WPS_WEBHOOK_MAP_PATH` in common skill-layout deployments.
- Split-message attachment uploads no longer lose earlier files when append mode is enabled.
- OpenClaw multi-channel attachment workflows now default to direct upload, avoiding unnecessary content-recognition token usage unless explicitly requested.

## [v1.1.1] - 2026-04-04

### Added
- OpenClaw auto-invocation strategy template with strict field-creation consent flow.
- Detailed installation guide refresh aligned with current behavior (`docs/安装与调用说明.md`).
- Explicit runtime submitter/channel resolution priority documentation.

### Changed
- Default field policy is strict: only existing table fields are writable.
- Only `_请求ID`, `_提交人`, `_提交渠道` are auto-creatable by default.
- New business field creation now requires explicit opt-in (`WPS_ALLOW_NEW_FIELDS=true`) and optional whitelist.

### Fixed
- Submitter and submit channel are resolved from runtime context before static fallback values.
- Attachment backfill/update flow stability improvements for split-message scenarios.

## [v1.1.0] - 2026-04-04

### Added
- Attachment backfill mode (`update_attachment`) for existing records.
- OpenClaw intent trigger and low-token usage guidance.

### Changed
- Reduced token usage by compacting AirScript response logs by default.
- Query path optimized for single-call return with compatibility fallback.

## [v1.0.0] - 2026-04-04

### Added
- Initial publish-ready release.
- Skill packaging, install docs, and basic release artifacts.
