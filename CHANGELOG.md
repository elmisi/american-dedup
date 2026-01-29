# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-29

### Added
- Initial public release
- TUI interface built with Textual
- Folder selection with two-panel layout (scan folders + target folders)
- Integration with fdupes for duplicate detection
- Preview screen showing files to move vs files to keep
- Execute move operation with progress tracking
- Undo functionality to restore moved files
- Save/load configuration profiles
- Option to include/exclude internal duplicates within target folders
- Comprehensive logging to `/tmp/american-dedup.log`

### Features
- Tree navigation with keyboard arrows in preview screen
- Animated spinner during scan operations
- Detailed statistics (files moved, skipped, errors)
- Preserves folder structure when moving duplicates
