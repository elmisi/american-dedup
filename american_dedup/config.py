"""Configuration management for saved profiles."""

import json
from pathlib import Path
from typing import TypedDict

CONFIG_DIR = Path.home() / ".config" / "american-dedup"
CONFIGS_FILE = CONFIG_DIR / "saved_configs.json"


class ConfigData(TypedDict):
    """Saved configuration data."""
    folders: list[str]
    sources: list[str]
    include_internal: bool


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

