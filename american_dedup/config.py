"""Configuration management for saved profiles and undo state."""

import json
from pathlib import Path
from typing import Optional, TypedDict

CONFIG_DIR = Path.home() / ".config" / "american-dedup"
CONFIGS_FILE = CONFIG_DIR / "saved_configs.json"
UNDO_FILE = CONFIG_DIR / "last_move.json"


class ConfigData(TypedDict):
    """Saved configuration data."""
    folders: list[str]
    sources: list[str]
    include_internal: bool


class MoveInfo(TypedDict):
    """Information about a single file move."""
    src: str
    dst: str


class UndoInfo(TypedDict):
    """Undo information for restoring moved files."""
    dest_dir: str
    moves: list[MoveInfo]


def ensure_config_dir() -> None:
    """Create the configuration directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_saved_configs() -> dict[str, ConfigData]:
    """
    Load all saved configurations.

    Returns:
        Dictionary mapping config names to their data.
    """
    ensure_config_dir()
    if CONFIGS_FILE.exists():
        with open(CONFIGS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(
    name: str,
    folders: list[str],
    sources: list[str],
    include_internal: bool = False
) -> None:
    """
    Save a configuration profile.

    Args:
        name: Name for this configuration.
        folders: List of folders to scan.
        sources: List of target folders (subset of folders).
        include_internal: Whether to include internal duplicates.
    """
    ensure_config_dir()
    configs = load_saved_configs()
    configs[name] = {
        "folders": folders,
        "sources": sources,
        "include_internal": include_internal
    }
    with open(CONFIGS_FILE, 'w') as f:
        json.dump(configs, f, indent=2)


def delete_config(name: str) -> None:
    """
    Delete a saved configuration.

    Args:
        name: Name of the configuration to delete.
    """
    configs = load_saved_configs()
    if name in configs:
        del configs[name]
        with open(CONFIGS_FILE, 'w') as f:
            json.dump(configs, f, indent=2)


def save_undo_info(moves: list[tuple[str, str]], dest_dir: str) -> None:
    """
    Save undo information for the last move operation.

    Args:
        moves: List of (source, destination) tuples for each moved file.
        dest_dir: The destination directory where files were moved.
    """
    ensure_config_dir()
    data: UndoInfo = {
        "dest_dir": dest_dir,
        "moves": [{"src": src, "dst": dst} for src, dst in moves]
    }
    with open(UNDO_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_undo_info() -> Optional[UndoInfo]:
    """
    Load undo information for the last move operation.

    Returns:
        Undo info dictionary, or None if no undo info exists.
    """
    if UNDO_FILE.exists():
        with open(UNDO_FILE, 'r') as f:
            return json.load(f)
    return None


def clear_undo_info() -> None:
    """Clear the undo information file."""
    if UNDO_FILE.exists():
        UNDO_FILE.unlink()
