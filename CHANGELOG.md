# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Added notice-first cataloging: librarians can search the local catalog before consulting configured external sources (BnF, Google Books, and SUDOC), then create physical copies from an existing notice.
- Added configurable external catalog source enablement and request timeouts in the Web UI settings.
- Added copy recaps during cataloging

### Fixed

- Improved periodical detection from bibliographic metadata and normalized identifier types.

## [1.4.0]

### Fixed

- Fixed shelf-location and Dewey badge colors in the Godot Kids client by using the array format returned by the settings API.
- Periodical detection now uses the bibliographic identifier type consistently across cataloging, reports, and collection statistics.
- Periodical item displays now preserve shelf locations while correctly handling issue numbers and call numbers.
- Never-borrowed report entries now include the bibliographic identifier type.

### Added

- Added synchronous automatic shelf suggestions during cataloging, using a lightweight pure-Python model trained from titles, subtitles, collections, authors, and unambiguous existing shelf assignments.

## [1.3.2]

### Fixed

- Added autocomplete suggestions for configured shelf locations in cataloging forms.
- Fixed automatic call-number recalculation from shelf rules across catalog and inventory editing forms.
- Fixed book barcode scanning in the Kids client by ignoring spaces in entered or scanned barcodes.
- The Kids client now restores the last server URL that connected successfully in the manual connection field after restarting.
- Added a confirmation dialog before closing the Kids client to prevent accidental exits.
- The Web UI catalog now shows all items by default.
- Added navigation from notices to cataloging for creating, editing, and deleting physical items.
- Fixed catalog searches for item barcodes entered with or without the configured prefix.

## [1.3.1]

### Fixed

- Fixed book links in the holds report by including the bibliographic record ID in the report response.
- Fixed borrower barcode printing to use the configured borrower prefix and ID on reference sheets and student cards.

## [1.3.0]

### Added

- Borrower `external_id` support: optional unique external identifiers (such as INE) can match existing borrowers during imports while preserving their reusable BCD IDs; CSV import and ONDE conversion support has also been improved.
- Organized converter packages with ONDE fixtures, tests, and borrower documentation updates.
- Inventory CLI commands for applying grouped inventory data, clearing call numbers, deleting unlisted items, and generating operation reports.
- CLI support for creating and replacing configured shelf locations.
- A `loanable` inventory search filter in the API and Web UI.
- `{TIT}` full normalized-title support for automatic call-number rules, including periodical cataloging updates.

### Changed

- Improved inventory column selection with a responsive two-column menu.
- Updated English and French translations and help documentation for inventory and catalog settings.

### Tests

- Added coverage for inventory CLI workflows, settings commands, loanable filtering, explicit call-number clearing, and full-title call-number generation.

## [1.2.0]

### Added

- Export / Import databse feature
- **Antivirus Analysis**: Integrated automated Windows Defender scanning into the release workflow for PyInstaller binaries.

### Changed

- Code cleanup

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
