# Changelog

All notable changes to Timed Switch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions use the project's `major.minor.build` numbering scheme.

## [Unreleased]

### Changed

- Moved Manual Override to Controls and the two remaining-time sensors to Diagnostic, naming the latter Time Until Override and Time Until Sync consistently on the Device page and dashboard card.
- Renamed the Configuration schedule entities to Schedule ON and Schedule OFF.
- Renamed the Problem diagnostic entity and its entity ID to Status, including migration of existing registry entries.
- Standardized the three primary switch labels on the Device page and dashboard card as Device state, Expected state, and Scheduled state.
- Standardized the manual control label as Manual Override on the Device page and dashboard card.
- Added separate Device, Expected, and Timed State change timestamps to the Diagnostic section and dashboard card.
- Added a read-only Target entity sensor to the Configuration section so the controlled entity is visible from the Device page.

### Fixed

- Device change time and manual-mode handling now ignore target updates that change attributes without changing the logical ON/OFF state.
- Manual Timeout and Sync Interval changes made through their number entities now persist in the config entry and survive Home Assistant restarts; subsequent number or schedule edits preserve all previously saved options instead of writing from a stale config-entry snapshot.

## [0.4.0049] - 2026-09-03

### Fixed

- Moved the Manual Remaining and Sync Remaining one-second countdown updates into the dashboard browser while exposing only stable deadline timestamps to Home Assistant, preventing the displays from flooding Activity and History.

## [0.3.0048] - 2026-09-02

### Changed

- Classified each config entry as a device so the integration remains visible on the Home Assistant Integrations dashboard.

## [0.2.0044] - 2026-08-29

### Added

- External automations can override the scheduled state through the standard Timed State switch until the next actual cron occurrence; the override is persisted while minute-aligned cron evaluation continues in the background.
- English and Hungarian user documentation.
- A crontab.guru reference for additional cron-expression guidance.
- HACS metadata, MIT license, and GitHub Actions for HACS and Hassfest validation.
- A parameterized local validation script for repository checks, unit tests, and Dockerized Hassfest.

### Changed

- Prepared repository metadata for publication under the `kovizsolt` GitHub account.
- Declared Home Assistant 2026.8.2 as the minimum supported version and classified the integration as a helper.
- Added HACS custom-repository installation instructions.

### Fixed

- Minute-aligned cron evaluation now uses a self-rearming monotonic delay, preventing backward system-clock jumps or evaluation errors from stalling future cron checks.
- ON/OFF cron expressions entered in configuration or the dashboard are normalized to five fields: missing fields are filled with `*`, wildcard-only extra fields are removed, and other extra fields retain the existing validation error behavior.
- Hassfest validation now recognizes the HTTP dependency, config-entry-only setup, and complete config-flow descriptions.
- Dashboard contract tests follow the punctuation used by the current card labels.

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
