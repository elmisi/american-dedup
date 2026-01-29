# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`american-dedup` is a TUI (Terminal User Interface) application built with Textual for finding and managing duplicate files using `fdupes`. It wraps `fdupes` with a user-friendly interface for selecting folders, previewing duplicates, and safely moving them while preserving undo capability.

## Development Commands

```bash
# Install (creates venv in .venv/ and symlink in ~/.local/bin/)
./install.sh

# Run directly during development
.venv/bin/python run.py [optional_start_path]

# Run after installation
american-dedup [optional_start_path]

# Uninstall
./uninstall.sh
```

**IMPORTANT**: After every code modification, reinstall the app with `./install.sh` to update the wrapper script.

**External dependency**: Requires `fdupes` system package to be installed.

## Architecture

### Module Structure

```
american_dedup/
├── __init__.py  # Package init with version
├── app.py       # Main Textual App class, keybindings, entry point
├── core.py      # fdupes execution, output parsing, file operations
├── config.py    # Persistent config and undo state (~/.config/american-dedup/)
└── screens.py   # All TUI screens (MainSelect, Scan, Preview, Execute, Undo, etc.)
```

### Screen Flow

```
MainSelectScreen → ScanScreen → PreviewScreen → ExecuteScreen
        ↑                                              │
        └──────────────────────────────────────────────┘
                        (or UndoScreen via 'u' key)
```

### Key Concepts

**Priority System**: Files are classified by their containing folder:
- Folders NOT in `source_folders` (target folders) = high priority (files are KEPT)
- Folders IN `source_folders` = low priority (duplicates are MOVED)

When a duplicate group spans both priorities, only low-priority copies are moved. When all copies are low-priority and `include_internal` is True, the first is kept.

**fdupes Output Parsing** (`core.py:parse_fdupes_line`): The `-1` flag outputs all duplicates in a group on one line, space-separated. Spaces in paths are escaped as `\ `. The parser handles this by replacing `\ ` with a placeholder before splitting.

**Undo System**: Every move operation saves source/dest paths to `~/.config/american-dedup/last_move.json`. Only the most recent operation can be undone.

### Async Pattern

Screens use Textual's `run_worker()` with `thread=True` to run blocking operations (fdupes, file moves, analysis) without freezing the UI. The `on_worker_state_changed()` method handles worker completion.

## Config Files

Stored in `~/.config/american-dedup/`:
- `saved_configs.json` - Named folder/source configurations for reuse
- `last_move.json` - Undo information for last move operation

## Logging

Debug logs are written to `/tmp/american-dedup.log`.
