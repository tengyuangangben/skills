# Changelog

All notable changes to this repository are documented in this file.

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
