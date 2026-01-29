# american-dedup

A terminal user interface (TUI) application for finding and managing duplicate files using [fdupes](https://github.com/adrianlopezroche/fdupes).

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

## Features

- **Two-panel folder selection**: Select folders to scan and mark target folders for deduplication
- **Smart duplicate handling**: Files in target folders are moved, files in other folders are kept
- **Preview before action**: See exactly which files will be moved and which will be kept
- **Undo support**: Restore moved files to their original locations
- **Save/load configurations**: Save folder selections for repeated use
- **Internal duplicates option**: Optionally handle duplicates within target folders only

## Requirements

- Python 3.10+
- [fdupes](https://github.com/adrianlopezroche/fdupes) (must be installed on your system)
- Linux (tested on Ubuntu/Debian)

### Installing fdupes

```bash
# Debian/Ubuntu
sudo apt install fdupes

# Fedora
sudo dnf install fdupes

# Arch Linux
sudo pacman -S fdupes
```

## Installation

### From source

```bash
git clone https://github.com/yourusername/american-dedup.git
cd american-dedup
./install.sh
```

This creates a virtual environment and installs the command `american-dedup` to `~/.local/bin/`.

### Using pip

```bash
pip install american-dedup
```

## Usage

```bash
american-dedup [starting_path]
```

### Workflow

1. **Add folders to scan**: Click "+ Add" to select folders containing files to check for duplicates
2. **Mark target folders**: Check the boxes next to folders from which duplicates should be moved
3. **Configure options**: Optionally enable "Include duplicates within target folders"
4. **Scan**: Click "Scan" to run fdupes and analyze duplicates
5. **Preview**: Review the files that will be moved vs kept
6. **Execute**: Click "Execute Move" to move duplicates to a timestamped folder

### Keyboard shortcuts

- `q` - Quit the application
- `u` - Open undo screen
- `Escape` - Go back to previous screen
- Arrow keys - Navigate tree in preview screen

### How it works

The application uses a priority system:
- Files in **non-target folders** have high priority (they are KEPT)
- Files in **target folders** have low priority (they are MOVED)

When a duplicate group contains files from both:
- All copies in target folders are moved
- All copies in non-target folders are kept

When duplicates exist only within target folders:
- If "Include internal duplicates" is OFF: nothing is moved
- If "Include internal duplicates" is ON: first copy is kept, others are moved

Moved files are placed in a `__dup_YYYYMMDD_HHMMSS` folder, preserving the original folder structure.

## Configuration

Configurations are saved to `~/.config/american-dedup/`:
- `saved_configs.json` - Named folder configurations
- `last_move.json` - Undo information for the last move operation

## Logging

Detailed logs are written to `/tmp/american-dedup.log` for debugging.

## Uninstallation

```bash
./uninstall.sh
```

Or if installed via pip:

```bash
pip uninstall american-dedup
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [fdupes](https://github.com/adrianlopezroche/fdupes) by Adrian Lopez for the duplicate detection engine
- [Textual](https://github.com/Textualize/textual) for the TUI framework
