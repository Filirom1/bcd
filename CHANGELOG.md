# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0]

### Added
- **Configuration**: Added `.env` configuration editor directly in the Web UI settings.
- **Configurable Directories**: Made application directories (data, config, logs, covers, backups) fully configurable via environment variables.
- **Cover Art**: Implemented background cover art downloads with slow rate limiting and real-time ETA progress display in the Web UI.
- **Cataloging & Call Numbers**: Added wildcard support to shelf-based call number rules.
- **Circulation & Holds**: Added a "soft loan warning limit" setting, integrated across the Web UI and the Godot kids client.
- **Kids Client**: Show shelving location details upon successful book return to guide student tidy-up.

### Fixed
- **Portable Mode**: Fixed startup failure caused by a circular import between configuration and portable path helpers.
- **Reports**: Applied publication year filters correctly to books missing publication year data.
- **API**: Configured verification endpoint to use the backup service directory helper.
- **Internationalization**: Added missing `status_not_loanable` keys in both French and English.
- **Kids Client**: Fixed button text color contrast on keyboard focus in the `chaperon-rouge` theme.

### Changed
- **UI Refactoring**: Unified borrower and bibliographic record view/edit modes, removing duplicated template code.
- **UI UX**: Increased `startId` debounce delay on item barcode label generation to prevent accidental submissions.

## [1.0.1]

### Added
- **Cataloging**: Added support for series, illustrators, and title fragments in automatic call number generation rules.

### Fixed
- **Updater**: Prevented "Text file busy" errors during Linux auto-update by unlinking the old binary before writing.
- **Cataloging**: Correctly set medium type to "periodical" for ISSN records parsed from SUDOC/BNF.

### Changed
- **E2E Tests**: Fixed and updated end-to-end tests for the v1.0.1 environment.
