# Changelog

All notable changes to Timed Switch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions use the project's `major.minor.build` numbering scheme.

## [Unreleased]

### Added

- English and Hungarian user documentation.
- A crontab.guru reference for additional cron-expression guidance.

### Fixed

- ON/OFF cron expressions entered in configuration or the dashboard are normalized to five fields: missing fields are filled with `*`, wildcard-only extra fields are removed, and other extra fields retain the existing validation error behavior.

## [0.1.0040] - 2026-08-19

### Added

- Cron-based ON and OFF schedules with live editing.
- Manual override mode with configurable timeout.
- Configurable state synchronization and availability diagnostics.
- Persisted controller state and recovery after Home Assistant restarts.
- Built-in virtual target and optional Virtual Switch target creation.
- Timed Switch dashboard card with schedule, timing, state, and diagnostic controls.
- Persistent notifications for optional schedule and enforcement events.

### Changed

- Schedule fields are available directly from the dashboard card.
- Dashboard timing and status presentation was refined.

### Fixed

- Cron validation errors are reported when schedules are edited.
- Scheduled-state calculation, countdown display, card selection, and event cleanup.
